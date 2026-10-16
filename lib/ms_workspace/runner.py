"""Test levels: t0 (what changed here), t1 (changed repos of a batch + critical modules), t2 (end to end)."""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from .core import (Workspace, ahead_of_base, batch_of_cwd, batch_repos, changed_files, die, git, git_out, modules_of,
                   need_batch, toplevel, topo)


def _tail(path: str, n: int = 40) -> str:
    return "\n".join(Path(path).read_text(errors="replace").splitlines()[-n:])


def _run_locked(ws: Workspace, cmd: str, cwd: Path, timeout: float) -> tuple[int, str]:
    """Run `bash -c cmd` under the workspace heavy lock; returns (exit code, output file path)."""
    fd, out = tempfile.mkstemp(prefix="ms-ws-")
    with os.fdopen(fd, "w") as fh, ws.heavy_lock(timeout):
        rc = subprocess.run(["bash", "-c", cmd], cwd=cwd, stdout=fh, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL).returncode
    return rc, out


def _memo_key(ws: Workspace, repo: str, directory: Path, batch: str, cmd: str) -> str:
    """Hash of the code under test (tree, uncommitted changes, untracked files, in-batch dependencies) and the command."""
    h = hashlib.sha1()
    h.update(git_out(directory, "rev-parse", "HEAD^{tree}").encode())
    h.update(git(directory, "diff", "HEAD").stdout.encode())
    for f in git(directory, "ls-files", "-o", "--exclude-standard").stdout.splitlines():
        try:
            h.update(f.encode() + hashlib.sha1((directory / f).read_bytes()).digest())
        except OSError:
            pass
    for d in ws.deps(repo):
        dep = ws.batch_dir / batch / d if batch else None
        if dep and dep.is_dir():
            h.update(git_out(dep, "rev-parse", "HEAD^{tree}").encode())
    h.update(cmd.encode())
    return h.hexdigest()[:20]


def run_tests(ws: Workspace, repo: str, directory: Path, level: str, batch: str | None = None) -> int:
    batch = batch_of_cwd(ws) if batch is None else batch
    base = ws.base(repo)
    mods = modules_of(directory, changed_files(directory, base))
    if level != "t0":
        mods = sorted(set(mods) | set(ws.repo_cfg(repo).get("critical") or []))
    test_cfg = ws.repo_cfg(repo).get("test") or {}
    cmd = ""
    if mods and test_cfg.get("affected"):
        cmd = test_cfg["affected"].replace("{modules}", ",".join(mods))
    cmd = cmd or test_cfg.get("unit") or ""
    if not cmd:
        die(f"no test command configured for '{repo}' in workspace.toml")

    key = ""
    memo_dir = ws.state_dir / "memo"
    memo_dir.mkdir(parents=True, exist_ok=True)
    if not os.environ.get("MS_NO_MEMO"):
        key = _memo_key(ws, repo, directory, batch, cmd)
        if (memo_dir / f"{repo}-{key}").exists():
            print(f"PASS {level} {repo} (cached: same code and command already passed): {cmd}")
            ws.log(f"test.{level}", "ok", repo, batch, f"cached: {cmd}")
            return 0
    start = time.time()
    rc, out = _run_locked(ws, cmd, directory, 1800)
    secs = int(time.time() - start)
    try:
        if rc == 0:
            if key:
                (memo_dir / f"{repo}-{key}").touch()
            print(f"PASS {level} {repo} ({secs}s): {cmd}")
            ws.log(f"test.{level}", "ok", repo, batch, cmd)
        else:
            print(f"FAIL {level} {repo} ({secs}s): {cmd}", file=sys.stderr)
            print(_tail(out), file=sys.stderr)
            ws.log(f"test.{level}", "fail", repo, batch, cmd)
    finally:
        os.unlink(out)
    return rc


def run_e2e(ws: Workspace, batch: str) -> int:
    cmd = ws.get("e2e", "command")
    if not cmd:
        print("no [e2e] command configured", file=sys.stderr)
        return 2
    erepo = ws.get("e2e", "repo", default="")
    directory = ws.root / erepo if erepo else ws.root
    if batch and erepo and (ws.batch_dir / batch / erepo).is_dir():
        directory = ws.batch_dir / batch / erepo
    start = time.time()
    rc, out = _run_locked(ws, cmd, directory, 3600)
    secs = int(time.time() - start)
    try:
        if rc == 0:
            print(f"PASS t2 e2e ({secs}s): {cmd}")
            ws.log("test.t2", "ok", erepo, batch, cmd)
        else:
            print(f"FAIL t2 e2e ({secs}s): {cmd}", file=sys.stderr)
            print(_tail(out), file=sys.stderr)
            ws.log("test.t2", "fail", erepo, batch, cmd)
    finally:
        os.unlink(out)
    return rc


def test_t1(ws: Workspace, batch: str) -> int:
    for r in topo(ws, batch_repos(ws, batch)):
        wt = ws.batch_dir / batch / r
        if ahead_of_base(wt, ws.base(r)) == 0:
            print(f"skip {r} (no changes vs base)")
            continue
        rc = run_tests(ws, r, wt, "t1", batch)
        if rc != 0:
            return rc
    return 0


def cmd_test(ws: Workspace, args: list[str]) -> int:
    if "--no-cache" in args:
        os.environ["MS_NO_MEMO"] = "1"
        args = [a for a in args if a != "--no-cache"]
    level = args[0] if args else ""
    arg = args[1] if len(args) > 1 else ""
    if level == "t0":
        top = toplevel()
        return run_tests(ws, top.name, top, "t0")
    if level == "t1":
        return test_t1(ws, need_batch(ws, arg or batch_of_cwd(ws)))
    if level == "t2":
        return run_e2e(ws, need_batch(ws, arg or batch_of_cwd(ws)))
    die("usage: test t0|t1|t2 [batch]")
