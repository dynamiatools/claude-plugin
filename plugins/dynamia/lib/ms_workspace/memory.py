"""Small local memory: one markdown note per durable fact (decision, lesson, gotcha, handoff)."""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

from .core import Workspace, die

TYPES = ("decision", "lesson", "gotcha", "handoff")
USAGE = "usage: memory [add [--type T] [--batch B] [--title T] [--] <text>|list|search <text>|show <name>|forget <name>]"


def mem_dir(ws: Workspace) -> Path:
    return ws.state_dir / "memory"


def _parse(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    meta, body = {}, text
    if text.startswith("---\n") and "\n---\n" in text[4:]:
        head, _, body = text[4:].partition("\n---\n")
        for l in head.splitlines():
            k, _, v = l.partition(":")
            meta[k.strip()] = v.strip()
    meta["name"] = path.stem
    meta["body"] = body.strip()
    meta.setdefault("type", "lesson")
    meta.setdefault("batch", "")
    meta.setdefault("title", meta["body"][:60])
    meta["created"] = meta.get("created", "")
    return meta


def notes(ws: Workspace) -> list[dict]:
    d = mem_dir(ws)
    if not d.is_dir():
        return []
    return sorted((_parse(p) for p in d.glob("*.md")), key=lambda n: n["name"], reverse=True)  # newest first


def add_note(ws: Workspace, kind: str, text: str, batch: str = "", title: str = "") -> str:
    if kind not in TYPES:
        die(f"memory: type must be one of {', '.join(TYPES)}")
    text = text.strip()
    if not text:
        die("memory: empty note")
    title = (title or re.sub(r"\s+", " ", text)[:60]).strip()
    d = mem_dir(ws)
    d.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40] or "note"
    base = f"{time.strftime('%Y%m%d-%H%M%S')}-{slug}"
    name, i = base, 2
    while (d / f"{name}.md").exists():
        name, i = f"{base}-{i}", i + 1
    created = time.strftime("%Y-%m-%dT%H:%M:%S")
    (d / f"{name}.md").write_text(
        f"---\ntype: {kind}\nbatch: {batch}\ntitle: {title}\ncreated: {created}\n---\n{text}\n", encoding="utf-8")
    ws.log("memory.add", "ok", "", batch, f"{kind}: {title}")
    return name


def find(ws: Workspace, ref: str) -> dict:
    hits = [n for n in notes(ws) if n["name"] == ref] or [n for n in notes(ws) if ref and ref in n["name"]]
    if not hits:
        die(f"memory: no note matches '{ref}'")
    if len(hits) > 1:
        die(f"memory: '{ref}' is ambiguous ({', '.join(n['name'] for n in hits[:5])})")
    return hits[0]


def drop_batch_handoffs(ws: Workspace, batch: str) -> int:
    n = 0
    for note in notes(ws):
        if note["type"] == "handoff" and note["batch"] == batch:
            (mem_dir(ws) / f"{note['name']}.md").unlink()
            n += 1
    return n


def context_lines(ws: Workspace) -> list[str]:
    """At most four short lines for the SessionStart briefing."""
    all_notes = notes(ws)
    if not all_notes:
        return []
    counts = {}
    for n in all_notes:
        counts[n["type"]] = counts.get(n["type"], 0) + 1
    out = [f"Memory: {len(all_notes)} notes ({', '.join(f'{v} {k}' for k, v in sorted(counts.items()))}); `ms-workspace memory list|search|show`."]
    active = {p.name for p in ws.batch_dir.iterdir() if p.is_dir()} if ws.batch_dir.is_dir() else set()
    seen = set()
    for n in all_notes:
        if n["type"] == "handoff" and n["batch"] in active and n["batch"] not in seen:
            seen.add(n["batch"])
            out.append(f"  HANDOFF {n['batch']}: {re.sub(chr(10) + '+', ' / ', n['body'])[:200]}")
    others = [n["title"] for n in all_notes if n["type"] != "handoff"][:3]
    if others:
        out.append("  Recent: " + "; ".join(others))
    return out[:4]


def cmd_memory(ws: Workspace, args: list[str]) -> int:
    sub, rest = (args[0], args[1:]) if args else ("list", [])
    if sub in ("-h", "--help", "help") or (rest and rest[0] in ("-h", "--help")):
        print(USAGE)
        return 0
    if sub == "add":
        kind, batch, title, words = "lesson", "", "", []
        it = iter(rest)
        for a in it:
            if a == "--":
                words.extend(it)  # everything after -- is note text, even if it starts with --
            elif a == "--type":
                kind = next(it, "")
            elif a == "--batch":
                batch = next(it, "")
            elif a == "--title":
                title = next(it, "")
            elif a.startswith("--"):
                die(f"memory add: unknown option {a}\n{USAGE}")
            else:
                words.append(a)
        text = " ".join(words) if words else sys.stdin.read()
        print(f"saved {add_note(ws, kind, text, batch, title)}")
        return 0
    if sub == "list":
        kind, batch, limit = "", "", 20
        it = iter(rest)
        for a in it:
            if a == "--type":
                kind = next(it, "")
            elif a == "--batch":
                batch = next(it, "")
            elif a == "-n":
                limit = int(next(it, "20"))
            else:
                die(f"memory list: unknown option {a}")
        rows = [n for n in notes(ws) if (not kind or n["type"] == kind) and (not batch or n["batch"] == batch)]
        if not rows:
            print("(no notes)")
        for n in rows[:limit]:
            print(f"{n['type']:<9} {n['batch'] or '-':<8} {n['title']}  ({n['name']})")
        return 0
    if sub == "search":
        terms = [t.lower() for t in rest]
        if not terms:
            die("usage: memory search <text...>")
        found = False
        for n in notes(ws):
            hay = f"{n['title']}\n{n['body']}".lower()
            if all(t in hay for t in terms):
                found = True
                line = next((l for l in n["body"].splitlines() if terms[0] in l.lower()), n["body"][:100])
                print(f"{n['name']}: [{n['type']}] {n['title']}\n    {line.strip()[:160]}")
        if not found:
            print("(no matches)")
        return 0
    if sub == "show":
        n = find(ws, rest[0] if rest else "")
        print(f"[{n['type']}] {n['title']}  batch={n['batch'] or '-'}  {n['created']}\n\n{n['body']}")
        return 0
    if sub == "forget":
        n = find(ws, rest[0] if rest else "")
        (mem_dir(ws) / f"{n['name']}.md").unlink()
        ws.log("memory.forget", "ok", "", n["batch"], n["name"])
        print(f"forgot {n['name']}")
        return 0
    die(USAGE)
