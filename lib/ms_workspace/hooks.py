"""Hooks that cut avoidable token spend: repeated reads of an unchanged file and huge Bash output."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from .usage import cache_dir

MIN_READ_CHARS = 4000        # smaller files are cheap to re-read; do not nag
DEFAULT_OUTPUT_MAX = 30000   # characters (about 7.5K tokens)
HEAD_LINES = TAIL_LINES = 60
MAX_LINE = 400


def _prune(folder: Path, days: float) -> None:
    cutoff = time.time() - days * 86400
    try:
        for p in folder.iterdir():
            if p.is_file() and p.stat().st_mtime < cutoff:
                p.unlink()
    except OSError:
        pass


def _emit(event: str, **fields) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": event, **fields}}, separators=(",", ":")))


def cmd_readguard(args: list[str]) -> int:
    """PreToolUse on Read: tell Claude when it is about to re-read an unchanged file already in its context.

    SessionStart (clear/compact) resets the memory of reads, because after a compaction re-reading is legitimate."""
    try:
        payload = json.loads(sys.stdin.read() or "{}")
        sid = payload.get("session_id") or "unknown"
        folder = cache_dir() / "reads"
        state_file = folder / f"{sid}.json"
        if payload.get("hook_event_name") == "SessionStart" or "--reset" in args:
            state_file.unlink(missing_ok=True)
            return 0
        info = payload.get("tool_input") or {}
        path = info.get("file_path")
        if not path:
            return 0
        st = os.stat(path)
        key = f"{path}|{info.get('offset') or 0}|{info.get('limit') or 0}"
        try:
            state = json.loads(state_file.read_text())
        except (OSError, ValueError):
            state = {}
        sig = [st.st_mtime_ns, st.st_size]
        entry = state.get(key)
        repeat = bool(entry and entry["sig"] == sig)
        state[key] = {"sig": sig, "count": entry["count"] + 1 if repeat else 1}
        folder.mkdir(parents=True, exist_ok=True)
        tmp = state_file.with_suffix(f".{os.getpid()}.tmp")
        tmp.write_text(json.dumps(state))
        os.replace(tmp, state_file)
        if time.time() % 50 < 1:
            _prune(folder, 7)
        count = state[key]["count"]
        if repeat and st.st_size >= MIN_READ_CHARS and not (info.get("limit") and st.st_size > 200000):
            msg = (f"ms-workspace: {os.path.basename(path)} was already read {count - 1} time(s) in this session and has not changed; "
                   f"its contents (about {st.st_size // 4} tokens) are already in your context and re-reading adds them again. "
                   "Use what you have, or read only the lines you need with offset/limit.")
            if count >= 4:
                msg += " Repeated reads are the largest avoidable token cost; keep the facts you need in a memory note."
            _emit("PreToolUse", additionalContext=msg)
    except Exception:
        pass
    return 0


def _squeeze(text: str, limit: int) -> tuple[str, int]:
    """Keep the head and tail of a long text. Returns (text, omitted_lines)."""
    if len(text) <= limit:
        return text, 0
    lines = [l if len(l) <= MAX_LINE else l[:MAX_LINE] + " ...[line cut]" for l in text.splitlines()]
    if len(lines) > HEAD_LINES + TAIL_LINES:
        omitted = len(lines) - HEAD_LINES - TAIL_LINES
        return "\n".join(lines[:HEAD_LINES] + [f"[... {omitted} lines omitted ...]"] + lines[-TAIL_LINES:]), omitted
    half = limit // 2  # few but very long lines: cut by characters
    return text[:half] + "\n[... characters omitted ...]\n" + text[-half:], 1


def cmd_outguard() -> int:
    """PostToolUse on Bash: replace a huge output with its head and tail; the full text is saved to a file."""
    try:
        if os.environ.get("MS_OUTGUARD") == "off":
            return 0
        payload = json.loads(sys.stdin.read() or "{}")
        resp = payload.get("tool_response")
        if payload.get("tool_name") != "Bash" or not isinstance(resp, dict):
            return 0
        limit = int(os.environ.get("MS_OUTGUARD_MAX_CHARS") or 0)
        if not limit:
            limit = DEFAULT_OUTPUT_MAX
            try:
                from .core import Workspace
                ws = Workspace.load(required=False, start=payload.get("cwd") or None)
                limit = int(ws.get("context", "bash_output_max_chars", default=DEFAULT_OUTPUT_MAX)) if ws else limit
            except Exception:
                pass
        out, err = resp.get("stdout") or "", resp.get("stderr") or ""
        if not isinstance(out, str) or not isinstance(err, str) or len(out) + len(err) <= limit:
            return 0
        folder = cache_dir() / "outputs"
        folder.mkdir(parents=True, exist_ok=True)
        _prune(folder, 3)
        saved = folder / f"{payload.get('tool_use_id') or int(time.time())}.txt"
        saved.write_text(f"$ {(payload.get('tool_input') or {}).get('command', '')}\n\n--- stdout ---\n{out}\n\n--- stderr ---\n{err}\n")
        new_out, omitted_out = _squeeze(out, limit // 2 if err else limit)
        new_err, omitted_err = _squeeze(err, limit // 2)
        note = (f"\n[ms-workspace outguard: output was ~{(len(out) + len(err)) // 4} tokens; shortened to its first and last lines. "
                f"Full output: {saved} (read only the part you need). Narrow the command next time: grep, head, tail, or the failing test only.]")
        _emit("PostToolUse", updatedToolOutput={**resp, "stdout": new_out + (note if new_out else ""), "stderr": new_err + (note if not new_out and new_err else "")})
    except Exception:
        pass
    return 0
