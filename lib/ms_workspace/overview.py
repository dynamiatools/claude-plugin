"""Read-only views: log, status, context, doctor."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from .core import int_arg, Workspace, batch_repos, die, git, git_ok
from .usage import cmd_usage, snapshot_path


def cmd_log(ws: Workspace, args: list[str]) -> int:
    n, day, action = 20, "", ""
    it = iter(args)
    for a in it:
        if a == "-n":
            n = int_arg(it, "-n", 20)
        elif a == "--day":
            day = next(it)
        elif a == "--action":
            action = next(it)
        else:
            die(f"log: unknown option {a}")
    if not ws.log_dir.is_dir():
        print("(no log yet)")
        return 0
    if day:
        files = [ws.log_dir / f"{day}.jsonl"]
        if not files[0].is_file():
            print(f"(no log for {day})")
            return 0
    else:
        files = sorted(ws.log_dir.glob("*.jsonl"))
        if not files:
            print("(no log yet)")
            return 0
    rows = []
    for f in files:
        for l in f.read_text(encoding="utf-8").splitlines():
            try:
                e = json.loads(l)
            except ValueError:
                continue
            if action and e.get("action") != action:
                continue
            rows.append(" | ".join(x for x in (e["ts"][:19], e["status"], e["action"], e["repo"], e["batch"], e["detail"]) if x))
    print("\n".join(rows[-n:]))
    return 0


def cmd_status(ws: Workspace, args: list[str]) -> int:
    fetch = "--fetch" in args
    for r in ws.repo_names():
        d = ws.root / r
        if not (d / ".git").exists():
            print(f"{r}: (not cloned)")
            continue
        base = ws.base(r)
        if fetch:
            git(d, "fetch", "origin", base, "--quiet")
        branch = git(d, "branch", "--show-current").stdout.strip()
        rl = git(d, "rev-list", "--left-right", "--count", f"origin/{base}...HEAD")
        behind, ahead = rl.stdout.split() if rl.returncode == 0 and len(rl.stdout.split()) == 2 else ("?", "?")
        dirty = len([l for l in git(d, "status", "--porcelain").stdout.splitlines() if l])
        batches = sorted(p.name for p in ws.batch_dir.glob("*") if (p / r).is_dir()) if ws.batch_dir.is_dir() else []
        print(f"{r}: {branch} | vs {base}: +{ahead}/-{behind} | dirty {dirty}" + (f" | batches: {','.join(batches)}" if batches else ""))
    return 0


def cmd_context(ws: Workspace | None) -> int:
    if ws is None:
        return 0
    print(f"Workspace '{ws.get('name', default='unnamed')}' at {ws.root} ({len(ws.repo_names())} repos). "
          "Tool: ms-workspace (log, status, affected, test t0).")
    batches = sorted(p for p in ws.batch_dir.iterdir() if p.is_dir()) if ws.batch_dir.is_dir() else []
    if batches:
        print("Active batches:")
        for b in batches:
            tasks = b / "TASKS.md"
            open_tasks = sum(1 for l in tasks.read_text().splitlines() if l.startswith("- [ ]")) if tasks.is_file() else 0
            print(f"  - {b.name}: repos {','.join(batch_repos(ws, b.name))}, open tasks: {open_tasks}")
    else:
        print("Active batches: none")
    import io
    from contextlib import redirect_stdout, redirect_stderr
    buf = io.StringIO()
    with redirect_stdout(buf), redirect_stderr(io.StringIO()):
        try:
            cmd_usage(ws, ["--line"])
        except Exception:
            pass
    if buf.getvalue().strip():
        print("Plan " + buf.getvalue().strip())
    from .memory import context_lines
    for l in context_lines(ws):
        print(l)
    print("Recent actions:")
    buf = io.StringIO()
    with redirect_stdout(buf):
        cmd_log(ws, ["-n", "5"])
    print("\n".join("  " + l for l in buf.getvalue().rstrip("\n").splitlines()))
    return 0


def cmd_doctor(ws: Workspace | None) -> int:
    bad = [False]

    def ok(m): print(f"  ok       {m}")
    def miss(m): print(f"  MISSING  {m}"); bad.__setitem__(0, True)
    def warn(m): print(f"  warn     {m}")
    def want(tool, note=""): ok(tool) if shutil.which(tool) else miss(tool + (f" ({note})" if note else ""))

    if ws is None:
        print("(no workspace.toml here: checking general tools only)")
    print("Tools:")
    for t in ("git", "jq", "python3", "gh"):
        want(t)
    ok("python >= 3.11") if sys.version_info >= (3, 11) else miss("python >= 3.11 (tomllib)")
    ok("claude") if shutil.which("claude") else warn("claude not in PATH")
    ok("tmux") if shutil.which("tmux") else warn("tmux (needed by ms-tmux-session)")
    ok("rtk") if shutil.which("rtk") else warn("rtk (optional: token-optimized shell output)")
    try:
        import sqlite3
        sqlite3.connect(":memory:").execute("create virtual table t using fts5(a)")
        ok("sqlite FTS5 (needed by recall)")
    except Exception:
        warn("this Python's sqlite3 has no FTS5: `ms-workspace recall` will not work")

    if ws is not None:
        stacks = sorted({s for r in ws.repo_names() for s in (ws.repo_cfg(r).get("stacks") or [])})
        print(f"Stack tools (from workspace.toml: {' '.join(stacks) or 'none'}):")
        if "maven" in stacks:
            want("mvn"); want("java")
            if shutil.which("java"):
                v = subprocess.run(["java", "-version"], capture_output=True, text=True)
                ok((v.stderr or v.stdout).splitlines()[0] if (v.stderr or v.stdout) else "java")
        if "gradle" in stacks:
            want("java")
        if "pnpm" in stacks:
            want("node"); want("pnpm")
        if "npm" in stacks:
            want("node")
        if "yarn" in stacks:
            want("node"); want("yarn")
        if "go" in stacks:
            want("go")
        if "rust" in stacks:
            want("cargo")
        compose = list(ws.root.glob("docker-compose*.yml")) + list(ws.root.glob("*/docker-compose*.yml"))
        if ws.get("e2e", "command") or compose:
            want("docker")

        print("Workspace:")
        for r in ws.repo_names():
            if not (ws.root / r / ".git").exists():
                miss(f"repo '{r}' not cloned at {ws.root / r}")
                continue
            base = ws.base(r)
            if not (git_ok(ws.root / r, "rev-parse", "--verify", "--quiet", f"origin/{base}")
                    or git_ok(ws.root / r, "rev-parse", "--verify", "--quiet", base)):
                miss(f"repo '{r}': base branch '{base}' not found")
            for d in ws.deps(r):
                if d not in ws.repo_names():
                    miss(f"repo '{r}' depends on unknown repo '{d}'")
        if not bad[0]:
            ok("all repos present, bases and deps valid")

    print("Hooks:")
    from .setup import installed_commands, our_commands, settings_path, SOURCE
    try:
        sp = settings_path()
        have = installed_commands(json.loads(sp.read_text())) if sp.exists() else set()
        wanted = our_commands(json.loads(SOURCE.read_text()))
        missing = sorted(wanted - have)
        if missing:
            warn("not installed in settings.json: " + ", ".join(missing) + " (run /ms-setup)")
        else:
            ok("ms-workspace hooks are installed in settings.json")
    except (OSError, ValueError):
        warn("could not read settings.json to check hooks (run /ms-setup)")

    print("Plan usage:")
    snap = snapshot_path()
    if snap.is_file():
        try:
            age = int((time.time() - json.loads(snap.read_text())["captured_at"]) // 60)
            ok(f"usage snapshot {age} min old (ms-statusline is working)")
        except (ValueError, KeyError, OSError):
            warn("usage snapshot is unreadable")
    else:
        warn("no usage snapshot: add ms-statusline as statusLine in settings.json (Pro/Max plans only)")

    print("Resources:")
    try:
        mem = next(l for l in Path("/proc/meminfo").read_text().splitlines() if l.startswith("MemAvailable"))
        ram = int(mem.split()[1]) // (1024 * 1024)
        ok(f"{ram}G RAM available") if ram >= 4 else warn(f"only {ram}G RAM available")
    except (OSError, StopIteration, ValueError):
        pass
    disk = shutil.disk_usage(ws.root if ws else Path.home()).free // 2**30
    ok(f"{disk}G disk free") if disk >= 10 else warn(f"only {disk}G disk free")
    if ws is not None:
        ws.log("doctor", "fail" if bad[0] else "ok")
    return 1 if bad[0] else 0
