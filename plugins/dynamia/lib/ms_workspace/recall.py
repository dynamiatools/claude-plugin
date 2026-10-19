"""Local full-text search over what was said and decided: Claude Code sessions run in the workspace, memory notes, the action log.

    ms-workspace recall <words...> [--kind session|memory|log] [-n 8] [--days 90] [--any] [--raw]
    ms-workspace recall index [--rebuild]      (a search refreshes the index first; this is only needed to pre-build it)
    ms-workspace recall status

SQLite FTS5 index at <workspace>/recall.db. Secrets are masked before anything is indexed. Nothing leaves the machine.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

from .core import Workspace, die, int_arg
from .gate import ASSIGNMENT, SECRET_PATTERNS

REMINDER = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)
MAX_TEXT = 2000


def db_path(ws: Workspace) -> Path:
    return ws.state_dir / "recall.db"


def connect(ws: Workspace, rebuild: bool = False) -> sqlite3.Connection:
    ws.state_dir.mkdir(parents=True, exist_ok=True)
    if rebuild:
        db_path(ws).unlink(missing_ok=True)
    con = sqlite3.connect(db_path(ws))
    try:
        con.execute("create virtual table if not exists fts using fts5(kind unindexed, ref unindexed, ts unindexed, title, body)")
    except sqlite3.OperationalError:
        die("this Python's SQLite was built without FTS5, so recall cannot index; install a Python whose sqlite3 supports FTS5")
    con.execute("create table if not exists sources(path text primary key, size integer, offset integer)")
    return con


def mask(text: str) -> str:
    for _, rx in SECRET_PATTERNS:
        text = rx.sub("***", text)
    return ASSIGNMENT.sub(lambda m: m.group(0).replace(m.group(3), "***"), text)


def message_text(d: dict) -> tuple[str, str]:
    """(role, text) of a transcript line, without tool output, tool calls or system reminders."""
    msg = d.get("message") if isinstance(d.get("message"), dict) else {}
    role = msg.get("role")
    if role not in ("user", "assistant") or d.get("isMeta"):
        return "", ""
    content = msg.get("content")
    if isinstance(content, list):
        content = " ".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    text = REMINDER.sub("", content if isinstance(content, str) else "").strip()
    return role, mask(re.sub(r"\s+", " ", text))[:MAX_TEXT]


def in_workspace(path: Path, ws: Workspace) -> bool:
    with open(path, errors="replace") as fh:
        for _, raw in zip(range(200), fh):
            try:
                cwd = json.loads(raw).get("cwd")
            except ValueError:
                continue
            if cwd:
                return ws.contains(cwd)
    return False


def index_sessions(ws: Workspace, con: sqlite3.Connection, days: float) -> int:
    projects = Path(os.environ.get("HOME", "~")).expanduser() / ".claude" / "projects"
    cutoff, added = time.time() - days * 86400, 0
    for f in sorted(projects.glob("*/*.jsonl")):
        try:
            st = f.stat()
        except OSError:
            continue
        if st.st_mtime < cutoff:
            continue
        row = con.execute("select size, offset from sources where path = ?", (str(f),)).fetchone()
        if row and row[0] == st.st_size:
            continue
        offset = row[1] if row and row[1] <= st.st_size else 0
        if not row and not in_workspace(f, ws):
            con.execute("insert or replace into sources values (?, ?, ?)", (str(f), st.st_size, st.st_size))   # remember that it is out of scope
            continue
        with open(f, "rb") as fh:
            fh.seek(offset)
            data = fh.read()
        data = data[: data.rfind(b"\n") + 1] if not data.endswith(b"\n") else data
        for raw in data.decode("utf-8", errors="replace").splitlines():
            try:
                d = json.loads(raw)
            except ValueError:
                continue
            role, text = message_text(d)
            if len(text) < 12:
                continue
            con.execute("insert into fts(kind, ref, ts, title, body) values ('session', ?, ?, ?, ?)",
                        (f.stem, (d.get("timestamp") or "")[:19], role, text))
            added += 1
        con.execute("insert or replace into sources values (?, ?, ?)", (str(f), st.st_size, offset + len(data)))
    return added


def index_small(ws: Workspace, con: sqlite3.Connection) -> None:
    """Memory notes and the action log are small: rebuild them on every refresh."""
    con.execute("delete from fts where kind in ('memory', 'log')")
    from .memory import notes
    for n in notes(ws):
        con.execute("insert into fts(kind, ref, ts, title, body) values ('memory', ?, ?, ?, ?)",
                    (n["name"], n["created"][:19], f"[{n['type']}] {n['title']}", mask(n["body"])[:MAX_TEXT]))
    if ws.log_dir.is_dir():
        for f in sorted(ws.log_dir.glob("*.jsonl")):
            for line in f.read_text(encoding="utf-8").splitlines():
                try:
                    e = json.loads(line)
                except ValueError:
                    continue
                if e.get("detail"):
                    con.execute("insert into fts(kind, ref, ts, title, body) values ('log', ?, ?, ?, ?)",
                                (f"{e['action']}", e["ts"][:19], f"{e['action']} {e['status']}", mask(" ".join(x for x in (e["repo"], e["batch"], e["detail"]) if x))))


def refresh(ws: Workspace, days: float, rebuild: bool = False) -> tuple[sqlite3.Connection, int, bool]:
    first = not db_path(ws).exists() or rebuild
    con = connect(ws, rebuild)
    if first:
        print("recall: building the index for the first time (sessions are read once; later searches are quick)...", file=sys.stderr)
    added = index_sessions(ws, con, days)
    index_small(ws, con)
    con.commit()
    return con, added, first


def fts_query(words: list[str], any_: bool, raw: bool) -> str:
    if raw:
        return " ".join(words)
    terms = ['"' + w.replace('"', "") + '"' + ("*" if i == len(words) - 1 and len(w) >= 3 else "") for i, w in enumerate(words) if w.strip('"')]
    return (" OR " if any_ else " ").join(terms)


def cmd_recall(ws: Workspace, args: list[str]) -> int:
    days = float(ws.get("recall", "days", default=90))
    if args[:1] == ["index"]:
        con, added, _ = refresh(ws, days, "--rebuild" in args)
        total = con.execute("select count(*) from fts").fetchone()[0]
        print(f"indexed {added} new message(s); {total} entries in {db_path(ws)}")
        return 0
    if args[:1] == ["status"]:
        if not db_path(ws).exists():
            print("no index yet (run: ms-workspace recall index)")
            return 0
        con = connect(ws)
        counts = dict(con.execute("select kind, count(*) from fts group by kind").fetchall())
        print(f"{db_path(ws)}: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())) + f" ({db_path(ws).stat().st_size // 1024} KB)")
        return 0
    kind, limit, any_, raw, words, it = "", 8, False, False, [], iter(args)
    for a in it:
        if a == "--kind":
            kind = next(it, "")
            if kind not in ("session", "memory", "log"):
                die("--kind is session, memory or log")
        elif a == "-n":
            limit = int_arg(it, "-n", 8)
        elif a == "--days":
            try:
                days = float(next(it))
            except (StopIteration, ValueError):
                die("--days needs a number")
        elif a == "--any":
            any_ = True
        elif a == "--raw":
            raw = True
        elif a.startswith("-"):
            die(f"recall: unknown option {a}")
        else:
            words.append(a)
    if not words:
        die("usage: recall <words...> [--kind session|memory|log] [-n N] [--days D] [--any] [--raw]  |  recall index|status")
    con, _, _ = refresh(ws, days)
    try:
        rows = con.execute("select kind, ref, ts, title, snippet(fts, 4, '[', ']', ' ... ', 14), bm25(fts) from fts where fts match ? "
                           + ("and kind = ? " if kind else "") + "order by bm25(fts) limit ?",
                           (fts_query(words, any_, raw), *([kind] if kind else []), limit)).fetchall()
    except sqlite3.OperationalError as e:
        die(f"could not run that search ({e}); try plain words, or --raw for FTS5 syntax")
    if not rows:
        print("(no matches)")
        return 0
    for k, ref, ts, title, snip, _ in rows:
        label = f"session {ref[:8]} {title}" if k == "session" else f"memory {title}" if k == "memory" else f"log {title}"
        print(f"{ts[:16]}  {label}\n    {snip.strip()}")
    sessions = sorted({r[1] for r in rows if r[0] == "session"})
    if sessions:
        print("Resume a conversation: claude --resume " + sessions[0] + ("  (and others: " + ", ".join(s[:8] for s in sessions[1:4]) + ")" if len(sessions) > 1 else ""))
    return 0
