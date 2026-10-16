"""PreToolUse hook: stop agents inside batch worktrees from publishing."""
from __future__ import annotations

import json
import os
import re
import sys

from .core import Workspace

PATTERN = re.compile(
    r"\bgit\b(\s+(-C|-c)\s+\S+|\s+--\S+)*\s+push\b|\bgh\s+pr\s+(create|merge)\b|\bms-workspace\s+(ship|clean)\b")


def cmd_guard() -> int:
    try:
        payload = json.loads(sys.stdin.read())
        command = payload["tool_input"]["command"]
        cwd = payload.get("cwd") or ""
    except (ValueError, KeyError, TypeError):
        return 0
    if not command:
        return 0
    if cwd and os.path.isdir(cwd):
        os.chdir(cwd)
    ws = Workspace.load(required=False)
    if ws is None or not (os.getcwd() + "/").startswith(str(ws.batch_dir) + "/"):
        return 0
    if PATTERN.search(command):
        ws.log("guard", "blocked", "", "", command)
        print("Blocked: agents in a batch worktree must not push, open/merge PRs, or run 'ms-workspace ship|clean'. "
              "Commit locally; the human integrates with 'ms-workspace ship'.", file=sys.stderr)
        return 2
    return 0
