"""Shared plumbing: workspace discovery and config, the action log, git and batch helpers."""
from __future__ import annotations

import fcntl
import json
import os
import re
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path


class MsError(Exception):
    """A user-facing failure: printed as 'ERROR: <message>' with exit code 1."""


def die(message: str):
    raise MsError(message)


# ---------------------------------------------------------------- subprocess / git
def run(cmd, cwd=None, input=None, env=None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, input=input, env=env, text=True, capture_output=True)


def git(cwd, *args) -> subprocess.CompletedProcess:
    return run(["git", "-C", str(cwd), *args])


def git_ok(cwd, *args) -> bool:
    return git(cwd, *args).returncode == 0


def git_out(cwd, *args) -> str:
    r = git(cwd, *args)
    if r.returncode != 0:
        die(f"git {' '.join(args)} failed in {cwd}: {r.stderr.strip()}")
    return r.stdout.strip()


# ------------------------------------------------------------------- workspace
def find_workspace_root(start: str | None = None) -> Path | None:
    here = Path(os.environ.get("MS_WORKSPACE") or start or os.getcwd()).resolve()
    for p in (here, *here.parents):
        if (p / "workspace.toml").is_file():
            return p
    return None


class Workspace:
    def __init__(self, root: Path):
        self.root = root
        self.cfg_path = root / "workspace.toml"
        import tomllib  # lazy: only `guard` has to work on Pythons older than 3.11
        try:
            self.cfg = tomllib.loads(self.cfg_path.read_text())
        except (OSError, tomllib.TOMLDecodeError) as e:
            die(f"could not parse {self.cfg_path}: {e}")
        self.state_dir = root / ".ms-workspace"
        self.log_dir = self.state_dir / "logs"
        self.batch_dir = root / ".batches"

    @classmethod
    def load(cls, required: bool = True, start: str | None = None) -> "Workspace | None":
        root = find_workspace_root(start)
        if root is None:
            if required:
                die("no workspace.toml found (run the dynamia:workspace-init skill first)")
            return None
        return cls(root)

    # -- config access
    def get(self, *keys, default=None):
        node = self.cfg
        for k in keys:
            if not isinstance(node, dict) or k not in node:
                return default
            node = node[k]
        return default if node is None else node

    def repo_names(self) -> list[str]:
        return sorted(self.get("repos", default={}))

    def repo_cfg(self, repo: str) -> dict:
        return self.get("repos", repo, default={})

    def repo_env(self, repo: str) -> dict[str, str]:
        """Variables from `env = ["NAME=value", ...]` of a repo, validated; applied to its test, e2e and setup commands."""
        out = {}
        for item in self.repo_cfg(repo).get("env") or []:
            name, sep, value = str(item).partition("=")
            if not sep or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
                die(f"repos.{repo}.env: '{item}' is not NAME=value")
            out[name] = value
        return out

    def run_env(self, repo: str) -> dict[str, str] | None:
        """Process environment for a repo's commands (None = inherit unchanged)."""
        extra = self.repo_env(repo)
        return {**os.environ, **extra} if extra else None

    def base(self, repo: str) -> str:
        return self.repo_cfg(repo).get("base") or "main"

    def deps(self, repo: str) -> list[str]:
        return list(self.repo_cfg(repo).get("deps") or [])

    def task_mode(self, repo: str) -> str:
        return self.repo_cfg(repo).get("tasks") or self.get("tasks", default="local")

    # -- action log: one JSON line per action, one file per day
    def log(self, action: str, status: str, repo: str = "", batch: str = "", detail: str = "", **extra):
        self.log_dir.mkdir(parents=True, exist_ok=True)
        path = self.log_dir / f"{time.strftime('%Y-%m-%d')}.jsonl"
        if not path.exists():
            self._rotate()
        rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "action": action, "status": status,
               "repo": repo, "batch": batch, "detail": detail}
        rec["ts"] = rec["ts"][:-2] + ":" + rec["ts"][-2:]
        rec.update({k: v for k, v in extra.items() if v is not None})
        rec.update(self._usage_fields())
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, separators=(",", ":"), ensure_ascii=False) + "\n")

    @staticmethod
    def _usage_fields() -> dict:
        """Plan usage (percent of the 5h and 7d windows) at event time, when a fresh snapshot exists."""
        try:
            from .usage import snapshot_path
            snap = json.loads(snapshot_path().read_text())
            now = time.time()
            if now - snap["captured_at"] > 1800:
                return {}
            out = {}
            for key, name in (("u5", "five_hour"), ("u7", "seven_day")):
                w = snap.get(name)
                if w and w.get("used_percentage") is not None and w["resets_at"] > now:
                    out[key] = w["used_percentage"]
            return out
        except Exception:
            return {}

    def _rotate(self):
        cutoff = time.time() - float(self.get("log_retention_days", default=14)) * 86400
        for folder, pattern in ((self.log_dir, "*.jsonl"), (self.state_dir / "memo", "*")):
            if folder.is_dir():
                for p in folder.glob(pattern):
                    try:
                        if p.is_file() and p.stat().st_mtime < cutoff:
                            p.unlink()
                    except OSError:
                        pass

    # -- the heavy-work lock: one test/e2e/setup run at a time per workspace
    @contextmanager
    def heavy_lock(self, timeout: float = 1800):
        self.state_dir.mkdir(parents=True, exist_ok=True)
        fh = open(self.state_dir / "heavy.lock", "w")
        deadline = time.time() + timeout
        try:
            while True:
                try:
                    fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.time() > deadline:
                        die("timed out waiting for another test run to finish")
                    time.sleep(0.5)
            yield
        finally:
            fh.close()


# -------------------------------------------------------------------- batches
def batch_of_cwd(ws: Workspace) -> str:
    """Name of the batch the current directory is inside, or ''."""
    try:
        rel = Path(os.getcwd()).resolve().relative_to(ws.batch_dir.resolve())
    except ValueError:
        return ""
    return rel.parts[0] if rel.parts else ""


def batch_repos(ws: Workspace, batch: str) -> list[str]:
    d = ws.batch_dir / batch
    return sorted(p.name for p in d.iterdir() if p.is_dir() and p.name != ".agents") if d.is_dir() else []


def need_batch(ws: Workspace, name: str) -> str:
    if not name or not (ws.batch_dir / name).is_dir():
        die(f"unknown batch '{name}' (see: ms-workspace clean)")
    return name


def base_ref(directory, base: str) -> str:
    return f"origin/{base}" if git_ok(directory, "rev-parse", "--verify", "--quiet", f"origin/{base}") else base


def ahead_of_base(directory, base: str) -> int:
    return int(git_out(directory, "rev-list", "--count", f"{base_ref(directory, base)}..HEAD"))


def topo(ws: Workspace, repos: list[str]) -> list[str]:
    """Dependencies first. On a dependency cycle the remaining repos are appended as they are."""
    remaining, out = list(repos), []
    while remaining:
        ready = [r for r in remaining if not any(d in remaining for d in ws.deps(r))]
        if not ready:
            out.extend(remaining)
            break
        out.extend(ready)
        remaining = [r for r in remaining if r not in ready]
    return out


def toplevel(directory=None) -> Path:
    r = run(["git", "rev-parse", "--show-toplevel"], cwd=directory)
    if r.returncode != 0:
        die("run inside a repo or batch worktree")
    return Path(r.stdout.strip())


def changed_files(directory, base: str) -> list[str]:
    """Files changed vs the merge-base with the base branch, including uncommitted and untracked ones."""
    mb = ""
    for ref in (f"origin/{base}", base):
        r = git(directory, "merge-base", "HEAD", ref)
        if r.returncode == 0:
            mb = r.stdout.strip()
            break
    mb = mb or "HEAD"
    tracked = git(directory, "diff", "--name-only", mb).stdout.splitlines()
    untracked = git(directory, "ls-files", "-o", "--exclude-standard").stdout.splitlines()
    return sorted({f for f in tracked + untracked if f})


def modules_of(directory, files: list[str]) -> list[str]:
    """Nearest Maven module (directory holding a pom.xml) for every changed file; [] for non-Maven repos."""
    root = Path(directory)
    if not (root / "pom.xml").is_file():
        return []
    mods = set()
    for f in files:
        d = os.path.dirname(f) or "."
        while d != "." and not (root / d / "pom.xml").is_file():
            d = os.path.dirname(d) or "."
        mods.add(d)
    return sorted(mods)


def int_arg(it, flag: str, default: int) -> int:
    """Next value of an iterator as an int, with a clear error instead of a traceback."""
    raw = next(it, None)
    try:
        return int(raw)
    except (TypeError, ValueError):
        die(f"{flag} needs a number" + (f" (got '{raw}')" if raw is not None else ""))
