"""Context budget: what is loaded into every session before you type anything (estimate: characters / 4)."""
from __future__ import annotations

import io
import json
import os
import re
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from .core import Workspace, die

LISTING_CAP = 1536  # characters of description + when_to_use that Claude Code keeps per skill


def est(text: str) -> int:
    return (len(text) + 3) // 4


def home_dir() -> Path:
    return Path(os.environ.get("HOME", "~")).expanduser()


def claude_home() -> Path:
    return Path(os.environ.get("CLAUDE_HOME") or home_dir() / ".claude")


def frontmatter(path: Path) -> dict:
    text = path.read_text(errors="replace")
    if not text.startswith("---\n"):
        return {}
    head = text[4:].split("\n---\n", 1)[0]
    out, key = {}, None
    for line in head.splitlines():
        if line[:1] in (" ", "\t") and key:
            out[key] += " " + line.strip()
        elif ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            out[key] = value.strip()
    return out


def _file_item(label: str, path: Path, group: str, note: str = "") -> dict | None:
    try:
        real = path.resolve()
        return {"group": group, "name": label, "tokens": est(real.read_text(errors="replace")), "path": str(path), "note": note}
    except OSError:
        return None


def _imports(path: Path) -> list[Path]:
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return []
    return [path.resolve().parent / m for m in re.findall(r"^@(\S+)\s*$", text, re.M) if (path.resolve().parent / m).is_file()]


def collect(cwd: Path, ws: Workspace | None) -> tuple[list[dict], list[dict], list[str]]:
    """Returns (always-loaded items, on-demand items, MCP server names)."""
    always, demand = [], []
    done: set[Path] = set()   # a directory can be reached twice (~/.claude and a parent of cwd): count each file once

    def fresh(path: Path) -> bool:
        real = path.resolve()
        if real in done:
            return False
        done.add(real)
        return True

    ch = claude_home()
    # Instruction files: global, then every CLAUDE.md from the filesystem root down to cwd.
    seen = set()
    chain = [("CLAUDE.md (global)", ch / "CLAUDE.md")]
    for d in reversed([cwd, *cwd.parents]):
        for rel in ("CLAUDE.md", ".claude/CLAUDE.md", "CLAUDE.local.md"):
            if (d / rel).is_file():
                chain.append((f"{rel} ({d.name or '/'})", d / rel))
    for label, p in chain:
        if p.is_file() and p.resolve() not in seen:
            seen.add(p.resolve())
            item = _file_item(label, p, "instructions")
            if item:
                always.append(item)
            for imp in _imports(p):
                if imp.resolve() not in seen:
                    seen.add(imp.resolve())
                    always.append(_file_item(f"@{imp.name} (imported by {p.name})", imp, "instructions"))
    # Path-scoped rules load on demand; unscoped ones always.
    for rules in {d / ".claude" / "rules" for d in (cwd, *cwd.parents)}:
        for p in sorted(rules.glob("*.md")) if rules.is_dir() else []:
            if not fresh(p):
                continue
            scoped = "paths" in frontmatter(p)
            item = _file_item(f"rule {p.name}", p, "rules", "only when matching files are open" if scoped else "")
            (demand if scoped else always).append(item)
    # Skills and agents: only name + description are listed in the context.
    skill_dirs = [ch / "skills"] + [d / ".claude" / "skills" for d in (cwd, *cwd.parents)]
    for sd in skill_dirs:
        for p in sorted(sd.glob("*/SKILL.md")) if sd.is_dir() else []:
            if not fresh(p):
                continue
            fm = frontmatter(p)
            text = f"{fm.get('name', p.parent.name)}: {fm.get('description', '')} {fm.get('when_to_use', '')}".strip()[:LISTING_CAP]
            note = "user-invoked only; may not be listed" if fm.get("disable-model-invocation", "").lower() == "true" else ""
            always.append({"group": "skills", "name": f"skill {p.parent.name}", "tokens": est(text), "path": str(p), "note": note})
    for ad in [ch / "agents"] + [d / ".claude" / "agents" for d in (cwd, *cwd.parents)]:
        for p in sorted(ad.glob("*.md")) if ad.is_dir() else []:
            if not fresh(p):
                continue
            fm = frontmatter(p)
            text = f"{fm.get('name', p.stem)}: {fm.get('description', '')} (Tools: {fm.get('tools', 'all')})"
            always.append({"group": "agents", "name": f"agent {p.stem}", "tokens": est(text), "path": str(p), "note": ""})
    # Claude Code's own per-project memory index.
    mem = ch / "projects" / str(cwd).replace("/", "-") / "memory" / "MEMORY.md"
    if mem.is_file():
        always.append(_file_item("auto-memory index (MEMORY.md)", mem, "memory"))
    # What the SessionStart hook of this tool injects.
    if ws is not None:
        from .overview import cmd_context
        buf = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(io.StringIO()):
            cmd_context(ws)
        always.append({"group": "hooks", "name": "ms-workspace context (SessionStart)", "tokens": est(buf.getvalue()), "path": "", "note": ""})
    servers: list[str] = []
    try:
        cfg = json.loads((home_dir() / ".claude.json").read_text())
        servers = sorted(set(cfg.get("mcpServers", {})) | set((cfg.get("projects", {}).get(str(cwd), {}) or {}).get("mcpServers", {})))
    except (OSError, ValueError):
        pass
    return [i for i in always if i], [i for i in demand if i], servers


def hints(always: list[dict], servers: list[str]) -> list[str]:
    out = []
    by = lambda g: sum(i["tokens"] for i in always if i["group"] == g)
    for i in always:
        if i["group"] == "instructions" and i["tokens"] > 1500:
            out.append(f"{i['name']} is ~{i['tokens']} tokens and loads every session: move rarely needed parts into a skill or a path-scoped rule.")
        if i["group"] == "skills" and i["tokens"] > 250:
            out.append(f"{i['name']} has a ~{i['tokens']}-token description in every session: keep descriptions near 100 tokens.")
        if i["group"] == "memory" and i["tokens"] > 1000:
            out.append(f"{i['name']} is ~{i['tokens']} tokens: prune stale entries.")
        if i["group"] == "hooks" and i["tokens"] > 400:
            out.append(f"{i['name']} injects ~{i['tokens']} tokens at every start: trim what it prints.")
    if by("skills") + by("agents") > 3000:
        out.append(f"Skills and agents list ~{by('skills') + by('agents')} tokens together: remove the ones you do not use.")
    if len(servers) >= 3:
        out.append(f"{len(servers)} MCP servers are configured; their tool schemas are not counted here and are usually the largest hidden cost.")
    return out[:6]


def cmd_budget(ws: Workspace | None, args: list[str]) -> int:
    top, as_json, cwd = 12, False, Path.cwd()
    it = iter(args)
    for a in it:
        if a == "--top":
            try:
                top = int(next(it))
            except (StopIteration, ValueError):
                die("--top needs a number")
        elif a == "--json":
            as_json = True
        elif a == "--cwd":
            cwd = Path(next(it, ".")).resolve()
        else:
            die(f"budget: unknown option {a}")
    always, demand, servers = collect(cwd, ws)
    always.sort(key=lambda i: -i["tokens"])
    total = sum(i["tokens"] for i in always)
    groups: dict[str, int] = {}
    for i in always:
        groups[i["group"]] = groups.get(i["group"], 0) + i["tokens"]
    result = {"cwd": str(cwd), "total_tokens": total, "groups": groups, "items": always, "on_demand": demand,
              "mcp_servers": servers, "hints": hints(always, servers)}
    if as_json:
        print(json.dumps(result, separators=(",", ":")))
        return 0
    print(f"Context budget for {cwd} (estimate: characters / 4, upper bound)")
    print("Loaded at the start of every session:")
    for i in always[:top]:
        print(f"  {i['tokens']:>6}  {i['name']}" + (f"  [{i['note']}]" if i["note"] else ""))
    rest = always[top:]
    if rest:
        print(f"  {sum(i['tokens'] for i in rest):>6}  ... and {len(rest)} smaller items")
    print(f"Total: ~{total} tokens ({', '.join(f'{g} {t}' for g, t in sorted(groups.items(), key=lambda kv: -kv[1]))})")
    if demand:
        print(f"On demand only: {len(demand)} path-scoped rules (~{sum(i['tokens'] for i in demand)} tokens)")
    print(f"MCP servers: {', '.join(servers) if servers else 'none'} (their tool schemas are not measured)")
    for h in result["hints"]:
        print("Hint: " + h)
    return 0
