"""Automatic handoff notes: the state a fresh session needs to resume a batch, written without asking the model.

    ms-workspace handoff [--batch B] [--print]      write (or just print) the handoff of a batch
    ms-workspace handoff --hook                     Stop / PreCompact / SessionEnd hook: writes only when it is worth it

One auto handoff is kept per batch (the newest replaces the previous one). Clearing the batch deletes it.
"""
from __future__ import annotations

import json
import sys
import time

from .core import Workspace, batch_of_cwd, batch_repos, die, git, git_out, need_batch
from .memory import add_note, notes, mem_dir

AUTO_TITLE = "auto handoff"


def latest_auto(ws: Workspace, batch: str) -> dict | None:
    for n in notes(ws):   # newest first
        if n["type"] == "handoff" and n["batch"] == batch and n["title"].startswith(AUTO_TITLE):
            return n
    return None


def collect(ws: Workspace, batch: str) -> list[str]:
    from .batches import unintegrated
    lines, pending = [], []
    for r in batch_repos(ws, batch):
        wt = ws.batch_dir / batch / r
        base = ws.base(r)
        dirty = [l[3:] for l in git(wt, "status", "--porcelain").stdout.splitlines() if l]
        ahead = git(wt, "rev-list", "--count", f"origin/{base}..HEAD").stdout.strip() or git(wt, "rev-list", "--count", f"{base}..HEAD").stdout.strip() or "0"
        subjects = git(wt, "log", "--format=%s", "-3", f"origin/{base}..HEAD").stdout.splitlines()
        loose = unintegrated(ws, batch, r)
        agents_dirty = []
        for a in sorted((ws.batch_dir / batch / ".agents").glob(f"*/{r}")):
            n = len([l for l in git(a, "status", "--porcelain").stdout.splitlines() if l])
            if n:
                agents_dirty.append(f"{a.parent.name} ({n} uncommitted)")
        part = f"{r}: {ahead} commit(s) ahead of {base}"
        if subjects:
            part += " [" + "; ".join(s[:50] for s in subjects) + "]"
        if dirty:
            part += f"; {len(dirty)} uncommitted file(s): " + ", ".join(dirty[:5]) + ("..." if len(dirty) > 5 else "")
            pending.append("commit or discard the uncommitted changes")
        if loose:
            part += "; agent branches not integrated: " + ", ".join(loose)
            pending.append(f"run `ms-workspace integrate {batch}`")
        if agents_dirty:
            part += "; agent worktrees with uncommitted work: " + ", ".join(agents_dirty)
        if int(ahead) and not dirty and not loose:
            pending.append(f"`ms-workspace test t1 {batch}`, then `plan {batch}`")
        lines.append(part)
    tasks = ws.batch_dir / batch / "TASKS.md"
    if tasks.is_file():
        open_tasks = [l[6:].strip() for l in tasks.read_text().splitlines() if l.startswith("- [ ]") and l[6:].strip()]
        if open_tasks:
            lines.append("open tasks: " + "; ".join(t[:60] for t in open_tasks[:5]))
    lines.append("next: " + ("; ".join(dict.fromkeys(pending)) if pending else "nothing pending in the worktrees"))
    from .insights import load_events
    noise = ("handoff", "memory.add", "memory.forget", "images", "doctor", "claude-md", "guard")   # events this very note causes
    recent = [e for e in load_events(ws, 3) if e.get("batch") == batch and e["action"] not in noise][-4:]
    if recent:
        lines.append("recent: " + "; ".join(f"{e['action']} {e['status']}" + (f" ({e['detail'][:40]})" if e.get("detail") else "") for e in recent))
    return lines


def usage_level(ws: Workspace) -> int:
    from .usage import evaluate, snapshot_path
    try:
        snap = json.loads(snapshot_path().read_text())
        return evaluate(snap, time.time(), ws.get("usage", "warn_pct", default=70), ws.get("usage", "stop_pct", default=90), 0)["level"]
    except (OSError, ValueError, KeyError):
        return 0


def write(ws: Workspace, batch: str, force: bool = False) -> str | None:
    lines = collect(ws, batch)
    body = "\n".join(lines)
    previous = latest_auto(ws, batch)
    if previous and previous["body"].split("\n", 1)[-1] == body and not force:
        return None
    for n in notes(ws):
        if n["type"] == "handoff" and n["batch"] == batch and n["title"].startswith(AUTO_TITLE):
            (mem_dir(ws) / f"{n['name']}.md").unlink(missing_ok=True)
    stamp = time.strftime("%H:%M")
    return add_note(ws, "handoff", f"Auto handoff written at {stamp}\n{body}", batch, f"{AUTO_TITLE} {stamp}")


def active_batch(ws: Workspace, cwd_batch: str) -> str:
    if cwd_batch:
        return cwd_batch
    names = [p.name for p in ws.batch_dir.iterdir() if p.is_dir()] if ws.batch_dir.is_dir() else []
    return names[0] if len(names) == 1 else ""


def hook() -> int:
    """Never fails the session and prints nothing."""
    try:
        payload = json.loads(sys.stdin.read() or "{}")
        import os
        cwd = payload.get("cwd")
        if cwd and os.path.isdir(cwd):
            os.chdir(cwd)
        ws = Workspace.load(required=False)
        if ws is None:
            return 0
        batch = active_batch(ws, batch_of_cwd(ws))
        if not batch or not (ws.batch_dir / batch).is_dir():
            return 0
        event = payload.get("hook_event_name")
        if event == "Stop":
            previous = latest_auto(ws, batch)
            recent = previous and time.time() - time.mktime(time.strptime(previous["created"][:19], "%Y-%m-%dT%H:%M:%S")) < 600
            if usage_level(ws) < 1 or recent:
                return 0
        elif event not in ("PreCompact", "SessionEnd"):
            return 0
        if write(ws, batch):
            ws.log("handoff", "ok", "", batch, f"auto ({event})")
    except Exception:
        pass
    return 0


def cmd_handoff(ws: Workspace | None, args: list[str]) -> int:
    if "--hook" in args:
        return hook()
    if ws is None:
        die("no workspace.toml found (run the ms-workspace-init skill first)")
    batch, only_print, it = "", "--print" in args, iter(a for a in args if a != "--print")
    for a in it:
        if a == "--batch":
            batch = next(it, "")
        else:
            die(f"handoff: unknown option {a}")
    batch = need_batch(ws, batch or active_batch(ws, batch_of_cwd(ws)))
    if only_print:
        print("\n".join(collect(ws, batch)))
        return 0
    name = write(ws, batch, force=True)
    print(f"saved {name}\n" + "\n".join(collect(ws, batch)))
    return 0
