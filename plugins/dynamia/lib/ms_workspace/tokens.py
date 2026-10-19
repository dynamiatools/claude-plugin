"""Token audit: where did the tokens of Claude Code sessions in this workspace go? (reads the local transcripts)"""
from __future__ import annotations

import json
import os
import time
from collections import Counter, defaultdict
from pathlib import Path

from .core import Workspace, die


def fmt(n: float) -> str:
    return f"{n / 1e6:.1f}M" if n >= 1e6 else f"{n / 1e3:.0f}K" if n >= 1e3 else str(int(n))


def _target(name: str, inp: dict) -> str:
    for k in ("file_path", "path", "command", "pattern", "query", "url", "prompt", "description"):
        if inp.get(k):
            return str(inp[k]).replace("\n", " ")[:70]
    return ""


def _scope(ws: Workspace, cwd: str) -> str | None:
    """'batch/repo' or 'repo' for a directory inside the workspace; None when outside."""
    parts = ws.rel_parts(cwd)
    if parts is None:
        return None
    if parts and parts[0] == ws.batch_dir.name and len(parts) >= 3:
        repo = parts[4] if parts[2] == ".agents" and len(parts) >= 5 else parts[2]
        return f"{parts[1]}/{repo}"
    return parts[0] if parts else "(workspace root)"


def _first_cwd(path: Path) -> str:
    with open(path, errors="replace") as fh:
        for _, raw in zip(range(200), fh):
            try:
                cwd = json.loads(raw).get("cwd")
            except ValueError:
                continue
            if cwd:
                return cwd
    return ""


def read_session(path: Path, ws: Workspace) -> dict | None:
    first = _first_cwd(path)
    if not first or _scope(ws, first) is None:  # out of scope: skip without reading the whole file
        return None
    msgs, tool_use, results = {}, {}, []
    scope, start, end, cwd0 = None, "", "", ""
    for raw in path.read_text(errors="replace").splitlines():
        try:
            d = json.loads(raw)
        except ValueError:
            continue
        cwd = d.get("cwd") or ""
        if cwd and not cwd0:
            cwd0 = cwd
            scope = _scope(ws, cwd)
            if scope is None:
                return None
        ts = d.get("timestamp", "")
        if ts:
            start, end = start or ts, ts
        m = d.get("message") if isinstance(d.get("message"), dict) else {}
        if d.get("type") == "assistant" and m.get("usage"):
            msgs[m.get("id") or d.get("uuid")] = (m["usage"], m.get("model", "?"))  # same message repeats per content block
            for b in m.get("content") or []:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    tool_use[b["id"]] = (b.get("name", "?"), _target(b.get("name", ""), b.get("input") or {}))
        elif d.get("type") == "user" and isinstance(m.get("content"), list):
            for b in m["content"]:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    c = b.get("content")
                    chars = len(c) if isinstance(c, str) else sum(len(x.get("text", "")) for x in c or [] if isinstance(x, dict))
                    results.append((b.get("tool_use_id"), chars))
    if scope is None or not msgs:
        return None
    new = sum(u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0) for u, _ in msgs.values())
    return {"session": path.stem, "scope": scope, "requests": len(msgs), "start": start, "end": end,
            "new_input": new, "cache_read": sum(u.get("cache_read_input_tokens", 0) for u, _ in msgs.values()),
            "output": sum(u.get("output_tokens", 0) for u, _ in msgs.values()),
            "models": sorted({m for _, m in msgs.values()}), "tool_use": tool_use, "results": results}


def audit(ws: Workspace, days: float, projects: Path | None = None) -> dict:
    projects = projects or Path(os.environ.get("HOME", "~")).expanduser() / ".claude" / "projects"
    cutoff = time.time() - days * 86400
    sessions = [s for f in sorted(projects.glob("*/*.jsonl")) if f.stat().st_mtime >= cutoff
                for s in [read_session(f, ws)] if s]
    by_scope = defaultdict(lambda: Counter())
    by_tool, calls, singles, reads = Counter(), Counter(), [], defaultdict(Counter)
    for s in sessions:
        c = by_scope[s["scope"]]
        c.update(requests=s["requests"], new_input=s["new_input"], cache_read=s["cache_read"], output=s["output"], sessions=1)
        for tid, chars in s["results"]:
            name, target = s["tool_use"].get(tid, ("?", ""))
            tok = chars // 4  # rough: 4 characters per token
            by_tool[name] += tok
            calls[name] += 1
            singles.append((tok, name, target, s["session"][:8]))
            if name == "Read" and target:
                reads[s["session"][:8]][target] += 1
    repeated = sorted(((n, f, sid) for sid, c in reads.items() for f, n in c.items() if n >= 3), reverse=True)[:5]
    total = Counter()
    for c in by_scope.values():
        total.update(c)
    return {"days": days, "sessions": len(sessions), "total": dict(total),
            "scopes": {k: dict(v) for k, v in sorted(by_scope.items(), key=lambda kv: -kv[1]["new_input"] - kv[1]["output"])},
            "tools": [{"tool": t, "approx_tokens": n, "calls": calls[t]} for t, n in by_tool.most_common(6)],
            "biggest": [{"approx_tokens": t, "tool": n, "target": g, "session": s} for t, n, g, s in sorted(singles, reverse=True)[:5]],
            "repeated_reads": [{"reads": n, "file": f, "session": sid} for n, f, sid in repeated]}


def hints(a: dict) -> list[str]:
    out = []
    if a["biggest"] and a["biggest"][0]["approx_tokens"] >= 8000:
        b = a["biggest"][0]
        out.append(f"A single {b['tool']} result was ~{fmt(b['approx_tokens'])} tokens ({b['target'][:40]}): narrow it (offset/limit, head/tail, rtk) or delegate to dynamia:scout.")
    if a["repeated_reads"]:
        out.append(f"{a['repeated_reads'][0]['file'][-40:]} was read {a['repeated_reads'][0]['reads']} times in one session: keep the facts in context or in a memory note.")
    t = a["total"]
    if t and t.get("cache_read", 0) < 2 * t.get("new_input", 1) and t.get("requests", 0) > 20:
        out.append("Low cache reuse: long idle gaps or frequent /clear make the prompt cache expire; keep related work in one session.")
    return out


def cmd_tokens(ws: Workspace, args: list[str]) -> int:
    days, as_json = 7.0, False
    it = iter(args)
    for a in it:
        if a == "--days":
            days = float(next(it, "7"))
        elif a == "--json":
            as_json = True
        else:
            die(f"tokens: unknown option {a}")
    a = audit(ws, days)
    if as_json:
        print(json.dumps(a, separators=(",", ":")))
        return 0
    if not a["sessions"]:
        print(f"No Claude Code sessions inside {ws.project} in the last {days:g} days.")
        return 0
    t = a["total"]
    print(f"Token audit: last {days:g} days, {a['sessions']} sessions in '{ws.get('name', default='workspace')}'")
    print(f"Totals: {t['requests']} requests | new input {fmt(t['new_input'])} | cache read {fmt(t['cache_read'])} | output {fmt(t['output'])}")
    print("By batch/repo (new input + output):")
    for k, v in list(a["scopes"].items())[:8]:
        print(f"  {k}: {v['sessions']} sessions, {v['requests']} requests, in {fmt(v['new_input'])}, out {fmt(v['output'])}, cache read {fmt(v['cache_read'])}")
    if a["tools"]:
        print("Tool results by size (approx tokens): " + ", ".join(f"{x['tool']} {fmt(x['approx_tokens'])} ({x['calls']} calls)" for x in a["tools"]))
    if a["biggest"]:
        print("Biggest single results:")
        for b in a["biggest"][:3]:
            print(f"  ~{fmt(b['approx_tokens'])} {b['tool']} {b['target']}")
    for h in hints(a):
        print("Hint: " + h)
    return 0
