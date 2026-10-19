"""Development environment variables kept in workspace.toml, for the commands the workspace runs (tests, e2e, env --setup).

    [dev.env]                 every repo
    NAME = "value"
    [repos.erp.dev.env]       one repo; wins over [dev.env]
    NAME = "value"

Only the lines of these tables are edited, so comments and everything else in the file stay as they are.
The values are plain text: this is for local development, never for secrets that matter.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .core import Workspace, die

NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
SECRET = re.compile(r"PASS|SECRET|TOKEN|KEY|CREDENTIAL|PRIVATE|AUTH", re.I)
HEADER = re.compile(r"^\s*\[")


def table_header(repo: str | None) -> str:
    return f"repos.{repo}.dev.env" if repo else "dev.env"


def _bounds(lines: list[str], header: str) -> tuple[int, int] | None:
    """(index of the header line, index after the table's last line) or None."""
    pat = re.compile(r"^\s*\[\s*" + re.escape(header).replace(r"\.", r"\s*\.\s*") + r"\s*\]\s*(#.*)?$")
    for i, line in enumerate(lines):
        if pat.match(line):
            end = next((j for j in range(i + 1, len(lines)) if HEADER.match(lines[j])), len(lines))
            return i, end
    return None


def _key_line(lines: list[str], lo: int, hi: int, name: str) -> int | None:
    pat = re.compile(r"^\s*\"?" + re.escape(name) + r"\"?\s*=")
    return next((i for i in range(lo, hi) if pat.match(lines[i])), None)


def edit(text: str, repo: str | None, name: str, value: str | None) -> str:
    """Set NAME in the table (value None removes it); returns the new file text."""
    lines = text.split("\n")
    header = table_header(repo)
    span = _bounds(lines, header)
    new = None if value is None else f"{name} = {json.dumps(value, ensure_ascii=False)}"
    if span is None:
        if new is None:
            return text
        body = text if text.endswith("\n") or not text else text + "\n"
        return body + ("\n" if body.strip() else "") + f"[{header}]\n{new}\n"
    lo, hi = span
    at = _key_line(lines, lo + 1, hi, name)
    if at is not None:
        if new is None:
            del lines[at]
            if not any(x.strip() and not x.strip().startswith("#") for x in lines[lo + 1:hi - 1]):
                del lines[lo:hi - 1]  # the table is empty now: drop its header too
                while lo < len(lines) and lo > 0 and not lines[lo - 1].strip() and (lo == len(lines) or not lines[lo].strip()):
                    del lines[lo - 1]
                    lo -= 1
        else:
            lines[at] = new
    elif new is not None:
        last = hi
        while last > lo + 1 and not lines[last - 1].strip():
            last -= 1
        lines.insert(last, new)
    return "\n".join(lines)


def write(ws: Workspace, repo: str | None, name: str, value: str | None) -> None:
    import tomllib
    path = ws.cfg_path
    before = path.read_text()
    after = edit(before, repo, name, value)
    if after == before:
        return
    try:
        data = tomllib.loads(after)
    except tomllib.TOMLDecodeError as e:
        die(f"could not edit {path} safely ({e}); add the variable by hand under [{table_header(repo)}]")
    node = data
    for key in (["repos", repo] if repo else []) + ["dev", "env"]:
        node = node.get(key, {}) if isinstance(node, dict) else {}
    ok = node.get(name) == value if value is not None else name not in node
    if not ok:
        die(f"could not edit {path} safely (the result does not hold the change); do it by hand under [{table_header(repo)}]")
    path.write_text(after)


def collect(ws: Workspace) -> list[tuple[str, str, str]]:
    """(scope, name, value) for every dev variable, workspace-wide first."""
    rows = [("all", k, str(v)) for k, v in (ws.get("dev", "env", default={}) or {}).items()]
    for r in ws.repo_names():
        rows += [(r, k, str(v)) for k, v in ((ws.repo_cfg(r).get("dev") or {}).get("env") or {}).items()]
    return rows


def shown(name: str, value: str, reveal: bool) -> str:
    return value if reveal or not SECRET.search(name) else "***"


def cmd_dev_env(ws: Workspace, args: list[str]) -> int:
    sub, rest = (args[0], args[1:]) if args else ("list", [])
    repo = None
    if "--repo" in rest:
        i = rest.index("--repo")
        if i + 1 >= len(rest):
            die("--repo needs a repo name")
        repo = rest[i + 1]
        rest = rest[:i] + rest[i + 2:]
        if repo not in ws.repo_names():
            die(f"unknown repo '{repo}' (known: {', '.join(ws.repo_names()) or 'none'})")
    if sub == "list" and "--json" in rest:
        # for the panel: names of repos and the variables, values of secret-looking names already hidden
        rows = [{"scope": sc, "name": n, "value": shown(n, v, False), "secret": bool(SECRET.search(n))} for sc, n, v in collect(ws)]
        print(json.dumps({"repos": ws.repo_names(), "vars": rows}))
        return 0
    if sub == "list":
        rows = collect(ws)
        reveal = "--show" in rest
        for scope, name, value in rows:
            print(f"{scope:<14} {name}={shown(name, value, reveal)}")
        if not rows:
            print("(no dev variables; add one with: ms-workspace dev-env add NAME=value [--repo R])")
        elif not reveal and any(SECRET.search(n) for _, n, _ in rows):
            print("(values of names that look secret are hidden; --show reveals them)")
        return 0
    if sub == "add":
        if not rest or "=" not in rest[0]:
            die("usage: dev-env add NAME=value [--repo R]")
        name, _, value = rest[0].partition("=")
        if not NAME.fullmatch(name):
            die(f"'{name}' is not a valid variable name (letters, digits and _, not starting with a digit)")
        if "\n" in value or "\r" in value:
            die("a value cannot hold a line break")
        write(ws, repo, name, value)
        ws.log("dev-env", "ok", repo or "", "", f"set {name}")
        note = " (looks secret: plain text in workspace.toml, development only)" if SECRET.search(name) else ""
        print(f"set      {name} for {repo or 'all repos'} in {ws.cfg_path}{note}")
        return 0
    if sub in ("rm", "remove"):
        if not rest or not NAME.fullmatch(rest[0]):
            die("usage: dev-env rm NAME [--repo R]")
        present = any(s == (repo or "all") and n == rest[0] for s, n, _ in collect(ws))
        if not present:
            print(f"absent   {rest[0]} for {repo or 'all repos'}")
            return 0
        write(ws, repo, rest[0], None)
        ws.log("dev-env", "ok", repo or "", "", f"removed {rest[0]}")
        print(f"removed  {rest[0]} for {repo or 'all repos'}")
        return 0
    die("usage: dev-env [list [--show|--json] | add NAME=value [--repo R] | rm NAME [--repo R]]")
