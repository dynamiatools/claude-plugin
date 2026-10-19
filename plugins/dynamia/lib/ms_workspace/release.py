"""Release view: what is waiting to be promoted from the integration branch to qa/main, and notes for it.

    ms-workspace release status [repo] [--fetch]
    ms-workspace release notes [repo] [--to qa] [--max 60]     markdown grouped by commit type

Release branches come from `release = ["qa", "main"]` in workspace.toml. Read-only apart from the optional fetch.
"""
from __future__ import annotations

import re

from .core import Workspace, die, git, git_ok, git_out

TYPES = [("feat", "Features"), ("fix", "Fixes"), ("perf", "Performance"), ("refactor", "Refactoring"), ("docs", "Documentation"),
         ("test", "Tests"), ("build", "Build"), ("ci", "CI"), ("chore", "Chores"), ("style", "Style"), ("revert", "Reverts")]
PREFIX = re.compile(r"^(\w+)(?:\(([^)]*)\))?(!)?:\s*(.*)$")


def ref(directory, name: str) -> str | None:
    for cand in (f"origin/{name}", name):
        if git_ok(directory, "rev-parse", "--verify", "--quiet", cand):
            return cand
    return None


def classify(subject: str) -> tuple[str, str, bool]:
    m = PREFIX.match(subject)
    if m and m.group(1).lower() in dict(TYPES):
        return m.group(1).lower(), m.group(4), bool(m.group(3))
    return "other", subject, False


def commits(directory, frm: str, to: str) -> list[dict]:
    fmt = "%h\x1f%an\x1f%cr\x1f%s\x1f%b\x1e"
    out = git_out(directory, "log", "--no-merges", f"--format={fmt}", f"{frm}..{to}")
    rows = []
    for rec in out.split("\x1e"):
        parts = rec.strip("\n").split("\x1f")
        if len(parts) >= 4 and parts[0].strip():
            kind, text, bang = classify(parts[3])
            rows.append({"hash": parts[0].strip(), "author": parts[1], "age": parts[2], "subject": parts[3], "kind": kind, "text": text,
                         "breaking": bang or "BREAKING CHANGE" in (parts[4] if len(parts) > 4 else "")})
    return rows


def targets(ws: Workspace, name: str | None) -> list[str]:
    repos = [name] if name else [r for r in ws.repo_names() if ws.repo_cfg(r).get("release")]
    for r in repos:
        if r not in ws.repo_names():
            die(f"unknown repo '{r}'")
    return repos


def cmd_status(ws: Workspace, args: list[str]) -> int:
    fetch = "--fetch" in args
    names = [a for a in args if not a.startswith("-")]
    repos = targets(ws, names[0] if names else None)
    if not repos:
        print("no repo has `release = [...]` in workspace.toml")
        return 0
    for r in repos:
        d, base = ws.repo_dir(r), ws.base(r)
        if fetch:
            git(d, "fetch", "origin", "--quiet")
        base_ref = ref(d, base)
        releases = ws.repo_cfg(r).get("release") or []
        if not releases:
            print(f"{r}: no release branches configured")
            continue
        for rel in releases:
            rel_ref = ref(d, rel)
            if not base_ref or not rel_ref:
                print(f"{r}: {base} -> {rel}: branch not found locally (try --fetch)")
                continue
            pending = commits(d, rel_ref, base_ref)
            drift = commits(d, base_ref, rel_ref)
            if not pending:
                print(f"{r}: {base} -> {rel}: up to date")
            else:
                kinds: dict[str, int] = {}
                for c in pending:
                    kinds[c["kind"]] = kinds.get(c["kind"], 0) + 1
                mix = ", ".join(f"{n} {k}" for k, n in sorted(kinds.items(), key=lambda kv: (-kv[1], kv[0])))
                stat = git(d, "diff", "--shortstat", f"{rel_ref}...{base_ref}").stdout.strip()
                print(f"{r}: {base} -> {rel}: {len(pending)} commit(s) waiting ({mix}), {len({c['author'] for c in pending})} author(s), oldest {pending[-1]['age']}"
                      + (f" | {stat}" if stat else ""))
                for c in pending[:5]:
                    print(f"    {c['hash']} {c['subject'][:90]}")
                if len(pending) > 5:
                    print(f"    ... and {len(pending) - 5} more")
                if any(c["breaking"] for c in pending):
                    print("    BREAKING: " + "; ".join(c["subject"][:60] for c in pending if c["breaking"])[:200])
            if drift:
                print(f"    WARNING {rel} has {len(drift)} commit(s) that {base} does not (hotfix drift): " + ", ".join(f"{c['hash']} {c['subject'][:40]}" for c in drift[:3]))
    return 0


def cmd_notes(ws: Workspace, args: list[str]) -> int:
    to, limit, names, it = None, 60, [], iter(args)
    for a in it:
        if a == "--to":
            to = next(it, None)
        elif a == "--max":
            try:
                limit = int(next(it))
            except (StopIteration, ValueError):
                die("--max needs a number")
        elif a.startswith("-"):
            die(f"release notes: unknown option {a}")
        else:
            names.append(a)
    repos = targets(ws, names[0] if names else None)
    for r in repos:
        d, base = ws.repo_dir(r), ws.base(r)
        rel = to or (ws.repo_cfg(r).get("release") or [None])[0]
        if not rel:
            print(f"{r}: no release branch configured")
            continue
        base_ref, rel_ref = ref(d, base), ref(d, rel)
        if not base_ref or not rel_ref:
            die(f"{r}: cannot find {base} or {rel}")
        pending = commits(d, rel_ref, base_ref)
        print(f"## {r}: {base} -> {rel} ({len(pending)} change(s))")
        if not pending:
            print("Nothing to promote.")
            continue
        groups = [(title, [c for c in pending if c["kind"] == kind]) for kind, title in TYPES + [("other", "Other")]]
        groups = [(t, g) for t, g in groups if g]
        per_group = max(3, limit // len(groups))   # every kind of change gets a share of the lines, not just the first kinds
        for title, group in groups:
            print(f"\n### {title} ({len(group)})")
            for c in group[:per_group]:
                print(f"- {c['text']}{' **BREAKING**' if c['breaking'] else ''} ({c['hash']})")
            if len(group) > per_group:
                print(f"- ... and {len(group) - per_group} more")
    return 0


def cmd_release(ws: Workspace, args: list[str]) -> int:
    sub, rest = (args[0], args[1:]) if args else ("status", [])
    if sub == "status":
        return cmd_status(ws, rest)
    if sub == "notes":
        return cmd_notes(ws, rest)
    die("usage: release status [repo] [--fetch] | release notes [repo] [--to BRANCH] [--max N]")
