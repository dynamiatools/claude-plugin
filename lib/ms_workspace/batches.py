"""Batch lifecycle: batch new, agent new, env, affected, integrate, ship, clean."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from .core import (MsError, Workspace, ahead_of_base, base_ref, batch_of_cwd, batch_repos, changed_files, die, git,
                   git_ok, git_out, modules_of, need_batch, run, toplevel, topo)


def eprint(*a):
    print(*a, file=sys.stderr)


# ------------------------------------------------------------ environment files
def copy_env(ws: Workspace, repo: str, dst: Path) -> None:
    """Copy gitignored files a fresh worktree lacks: .worktreeinclude, env_files and settings.local.json."""
    src = ws.root / repo
    names = set()
    if (src / ".worktreeinclude").is_file():
        r = git(src, "ls-files", "--others", "--ignored", "--exclude-from=.worktreeinclude")
        names.update(r.stdout.splitlines())
    names.update(ws.repo_cfg(repo).get("env_files") or [])
    names.add(".claude/settings.local.json")
    copied = 0
    for f in sorted(names):
        if not f or f.startswith("/") or ".." in f:
            continue
        if not (src / f).is_file() or (dst / f).exists():
            continue
        if not git_ok(src, "check-ignore", "-q", "--", f):  # never copy tracked files
            continue
        (dst / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src / f, dst / f)
        copied += 1
    if copied:
        print(f"    copied {copied} ignored file(s) into {dst.name}")


def trust_dir(directory: Path) -> None:
    """Mark a directory as trusted so Claude skips the 'trust this folder' dialog."""
    cfg = Path(os.environ.get("HOME", "~")).expanduser() / ".claude.json"
    if not cfg.is_file():
        return
    try:
        data = json.loads(cfg.read_text())
        data.setdefault("projects", {}).setdefault(str(directory), {})["hasTrustDialogAccepted"] = True
        cfg.write_text(json.dumps(data, indent=2))
    except (OSError, ValueError):
        pass


def worktree_dirs(ws: Workspace, batch: str) -> list[Path]:
    out = []
    for repo in batch_repos(ws, batch):
        out.append(ws.batch_dir / batch / repo)
        out.extend(sorted((ws.batch_dir / batch / ".agents").glob(f"*/{repo}")))
    return out


def cmd_env(ws: Workspace, args: list[str]) -> int:
    setup = trust = False
    batch = ""
    for a in args:
        if a == "--setup":
            setup = True
        elif a == "--trust":
            trust = True
        else:
            batch = a
    batch = need_batch(ws, batch or batch_of_cwd(ws))
    for d in worktree_dirs(ws, batch):
        repo = d.name
        print(f"  {d}")
        copy_env(ws, repo, d)
        if trust:
            trust_dir(d)
        cmd = ws.repo_cfg(repo).get("setup")
        if setup and cmd:
            print(f"    setup: {cmd}")
            with ws.heavy_lock(1800):
                r = subprocess.run(["bash", "-c", cmd], cwd=d, capture_output=True, text=True, stdin=subprocess.DEVNULL)
            if r.returncode == 0:
                ws.log("env.setup", "ok", repo, batch, cmd)
            else:
                ws.log("env.setup", "fail", repo, batch, cmd)
                eprint(f"    setup FAILED: {cmd}")
    ws.log("env", "ok", "", batch, f"setup={int(setup)} trust={int(trust)}")
    return 0


# ----------------------------------------------------------------------- batch
def cmd_batch(ws: Workspace, args: list[str]) -> int:
    if not args or args[0] != "new" or len(args) < 2:
        die("usage: batch new <name> [repo...]")
    name, repos = args[1], args[2:] or ws.repo_names()
    directory = ws.batch_dir / name
    if directory.exists():
        die(f"batch '{name}' already exists at {directory}")
    directory.mkdir(parents=True)
    for r in repos:
        src, base = ws.root / r, ws.base(r)
        if not (src / ".git").exists():
            ws.log("batch.new", "error", r, name, f"repo not found at {src}")
            die(f"repo '{r}' not found at {src}")
        if not git_ok(src, "fetch", "origin", base, "--quiet"):
            eprint(f"warn: could not fetch {r}/{base} (using local ref)")
        start = f"origin/{base}" if git_ok(src, "rev-parse", "--verify", "--quiet", f"origin/{base}") else base
        if not git_ok(src, "worktree", "add", "--no-track", "-b", f"int/{name}", str(directory / r), start):
            ws.log("batch.new", "error", r, name, "worktree add failed")
            die(f"could not create worktree for {r} (branch int/{name} may exist)")
        ws.log("batch.new", "ok", r, name, f"int/{name} from {start}")
        print(f"  {r} -> {directory / r} (int/{name} from {start})")
        copy_env(ws, r, directory / r)
    lines = [f"# Batch: {name}", "", f"Repos: {' '.join(repos)}", "", "## Tasks"]
    for r in repos:
        if ws.task_mode(r) == "github":
            lines.append(f"- {r}: tracked in GitHub issues; list only issue numbers here")
        else:
            lines.append(f"- [ ] {r}: ")
    (directory / "TASKS.md").write_text("\n".join(lines) + "\n")
    print(f"Batch ready: {directory}")
    return 0


def cmd_agent(ws: Workspace, args: list[str]) -> int:
    if len(args) < 3 or args[0] != "new":
        die("usage: agent new <batch> <task> [repo...]")
    batch = need_batch(ws, args[1])
    task = args[2]
    repos = args[3:] or batch_repos(ws, batch)
    for r in repos:
        main_wt = ws.batch_dir / batch / r
        wt = ws.batch_dir / batch / ".agents" / task / r
        if not main_wt.is_dir():
            die(f"repo '{r}' is not part of batch '{batch}'")
        if not git_ok(main_wt, "worktree", "add", "--no-track", "-b", f"agent/{batch}/{task}", str(wt), f"int/{batch}"):
            die(f"could not create agent worktree for {r} (branch agent/{batch}/{task} may exist)")
        ws.log("agent.new", "ok", r, batch, f"agent/{batch}/{task}")
        print(f"  {r} -> {wt} (agent/{batch}/{task})")
        copy_env(ws, r, wt)
    return 0


# -------------------------------------------------------------------- affected
def cmd_affected(ws: Workspace, args: list[str]) -> int:
    top = toplevel()
    repo, base = top.name, ws.base(top.name)
    files = changed_files(top, base)
    dependents: set[str] = set()
    grew = True
    while grew:  # transitive closure of "depends on <repo>"
        grew = False
        for r in ws.repo_names():
            if r != repo and r not in dependents and any(d == repo or d in dependents for d in ws.deps(r)):
                dependents.add(r)
                grew = True
    out = {"repo": repo, "files": len(files), "modules": modules_of(top, files), "dependents": sorted(dependents)}
    print(json.dumps(out, separators=(",", ":")))
    return 0


# ------------------------------------------------------------------- integrate
def cmd_integrate(ws: Workspace, args: list[str]) -> int:
    if not args:
        die("usage: integrate <batch> [--dry-run]")
    batch = need_batch(ws, args[0])
    dry = "--dry-run" in args[1:]
    conflict = False
    for r in topo(ws, batch_repos(ws, batch)):
        wt = ws.batch_dir / batch / r
        if not dry and git_out(wt, "status", "--porcelain"):
            die(f"{r}: int/{batch} worktree has uncommitted changes")
        branches = git_out(wt, "for-each-ref", "--format=%(refname:short)", f"refs/heads/agent/{batch}/").splitlines()
        for br in branches:
            if git_ok(wt, "merge-base", "--is-ancestor", br, "HEAD"):
                print(f"  {r}: {br} already merged")
                continue
            mt = git(wt, "merge-tree", "--write-tree", "--name-only", "HEAD", br)
            if mt.returncode == 0:
                if dry:
                    print(f"  {r}: {br} merges cleanly")
                else:
                    m = git(wt, "merge", "--no-ff", "--no-edit", "-m", f"Integrate {br}", br)
                    if m.returncode != 0:
                        die(f"{r}: merging {br} failed: {m.stderr.strip()}")
                    ws.log("integrate", "ok", r, batch, br)
                    print(f"  {r}: merged {br}")
            else:
                lines = mt.stdout.splitlines()[1:]
                files = " ".join(l for l in (lines[: lines.index("")] if "" in lines else lines) if l)
                eprint(f"  {r}: CONFLICT merging {br} -> {files}")
                ws.log("integrate", "conflict", r, batch, f"{br}: {files}")
                conflict = True
    if conflict:
        eprint(f"Resolve the conflicts (rebase the agent branch on int/{batch}), then run again.")
        return 1
    if not dry:
        print(f"Integrated. Next: ms-workspace test t1 {batch}")
    return 0


# ------------------------------------------------------------------------ ship
def cmd_ship(ws: Workspace, args: list[str]) -> int:
    from .runner import run_e2e, test_t1

    if not args:
        die("usage: ship <batch> [--yes] [--skip-e2e]")
    batch = need_batch(ws, args[0])
    yes = skip_e2e = False
    for a in args[1:]:
        if a == "--yes":
            yes = True
        elif a == "--skip-e2e":
            skip_e2e = True
        else:
            die(f"ship: unknown option {a}")

    repos = []
    for r in topo(ws, batch_repos(ws, batch)):
        wt, base = ws.batch_dir / batch / r, ws.base(r)
        if git_out(wt, "status", "--porcelain"):
            die(f"{r}: uncommitted changes in int/{batch}")
        if base in (ws.repo_cfg(r).get("release") or []):
            die(f"{r}: base '{base}' is a release branch; ship never targets those")
        if not git_ok(ws.root / r, "fetch", "origin", base, "--quiet"):
            eprint(f"warn: could not fetch {r}/{base}")
        if ahead_of_base(wt, base) == 0:
            print(f"skip {r} (nothing to ship)")
            continue
        repos.append(r)
    if not repos:
        print(f"Nothing to ship in batch '{batch}'.")
        return 0

    print(f"Plan for batch '{batch}':")
    for r in repos:
        mode = ws.repo_cfg(r).get("push") or "direct"
        print(f"  {r}: int/{batch} -> {ws.base(r)} ({mode}, {ahead_of_base(ws.batch_dir / batch / r, ws.base(r))} commits)")
    if not yes:
        print("(plan only; pass --yes to run: sync, t1, e2e, push)")
        return 0

    # 1) sync with the base branch (merge, since int/* is local only)
    for r in repos:
        wt, base = ws.batch_dir / batch / r, ws.base(r)
        if not git_ok(wt, "merge-base", "--is-ancestor", f"origin/{base}", "HEAD"):
            print(f"  {r}: base moved, merging origin/{base}")
            if not git_ok(wt, "merge", "--no-edit", f"origin/{base}"):
                git(wt, "merge", "--abort")
                ws.log("ship", "conflict", r, batch, f"merging origin/{base}")
                die(f"{r}: conflict merging origin/{base} into int/{batch}; resolve it in {wt} and run ship again")
    # 2) tests
    if test_t1(ws, batch) != 0:
        ws.log("ship", "fail", "", batch, "t1 failed")
        die("t1 failed; nothing was pushed")
    if not skip_e2e:
        if not ws.get("e2e", "command"):
            die("no [e2e] command configured; pass --skip-e2e to ship without e2e")
        if run_e2e(ws, batch) != 0:
            ws.log("ship", "fail", "", batch, "t2 failed")
            die("e2e failed; nothing was pushed")
    # 3) push
    for r in repos:
        wt, base = ws.batch_dir / batch / r, ws.base(r)
        mode = ws.repo_cfg(r).get("push") or "direct"
        if mode == "pr":
            p = subprocess.run(["git", "-C", str(wt), "push", "origin", f"int/{batch}"])
            if p.returncode == 0:
                p = subprocess.run(["gh", "pr", "create", "--base", base, "--head", f"int/{batch}", "--fill"], cwd=wt)
            if p.returncode != 0:
                die(f"{r}: could not open the PR")
        else:
            p = subprocess.run(["git", "-C", str(wt), "push", "origin", f"int/{batch}:{base}"])
            if p.returncode != 0:
                die(f"{r}: push to {base} rejected (base moved again? run ship again)")
        ws.log("ship", "ok", r, batch, f"int/{batch} -> {base} ({mode})")
        print(f"  pushed {r}")
    print(f"Shipped. Cleanup: ms-workspace clean {batch}")
    return 0


# ------------------------------------------------------------------------ clean
def _merged(ws: Workspace, batch: str, repo: str) -> bool:
    wt = ws.batch_dir / batch / repo
    return git_ok(wt, "merge-base", "--is-ancestor", "HEAD", base_ref(wt, ws.base(repo)))


def cmd_clean(ws: Workspace, args: list[str]) -> int:
    force = "--force" in args
    names = [a for a in args if a != "--force"]
    if not names:
        if not ws.batch_dir.is_dir():
            print("(no batches)")
            return 0
        for b in sorted(p.name for p in ws.batch_dir.iterdir() if p.is_dir()):
            ok = all(_merged(ws, b, r) for r in batch_repos(ws, b))
            print(f"{b}: {'merged (safe to clean)' if ok else 'pending'}")
        return 0
    batch = need_batch(ws, names[-1])
    repos = batch_repos(ws, batch)
    if not force:
        for r in repos:
            if not _merged(ws, batch, r):
                die(f"{r}: int/{batch} is not merged into {ws.base(r)} yet (use --force to discard)")
    flags = ["--force"] if force else []
    for r in repos:
        main_wt = ws.batch_dir / batch / r
        for wt in sorted((ws.batch_dir / batch / ".agents").glob(f"*/{r}")):
            res = git(main_wt, "worktree", "remove", *flags, str(wt))
            if res.returncode != 0:
                die(f"{r}: could not remove {wt}: {res.stderr.strip()}")
        res = git(main_wt, "worktree", "remove", *flags, str(main_wt))
        if res.returncode != 0:
            die(f"{r}: could not remove {main_wt}: {res.stderr.strip()}")
        refs = git_out(ws.root / r, "for-each-ref", "--format=%(refname:short)", f"refs/heads/agent/{batch}/", f"refs/heads/int/{batch}")
        for b in refs.splitlines():
            git(ws.root / r, "branch", "-D", b)
        ws.log("clean", "ok", r, batch, "")
        print(f"  cleaned {r}")
    (ws.batch_dir / batch / "TASKS.md").unlink(missing_ok=True)
    # Only empty directories (such as .agents/<task>) are left; remove bottom-up.
    for p in sorted((ws.batch_dir / batch).rglob("*"), key=lambda x: len(x.parts), reverse=True):
        if p.is_dir() and not any(p.iterdir()):
            p.rmdir()
    try:
        (ws.batch_dir / batch).rmdir()
    except OSError:
        pass
    return 0
