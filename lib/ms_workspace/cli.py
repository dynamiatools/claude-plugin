"""Command dispatch for ms-workspace."""
from __future__ import annotations

import sys

from .core import MsError, Workspace

USAGE = """\
ms-workspace: mechanical helper for the multi-repo batch workflow.
Reads <workspace>/workspace.toml (created by the ms-workspace-init skill).
Deterministic on purpose: skills and hooks call it so the model does not
have to spend tokens on git/test plumbing.

Usage:
  ms-workspace batch new <name> [repo...]    create a batch (one worktree per repo, branch int/<name>)
  ms-workspace affected                      JSON: changed repos/modules and their dependents
  ms-workspace agent new <batch> <task> [repo...]   isolated worktree per agent (branch agent/<batch>/<task>)
  ms-workspace env [batch] [--setup] [--trust]   copy ignored files (.worktreeinclude, env_files) into the batch worktrees
  ms-workspace test t0                       test what changed in the current repo (add --no-cache to force a run)
  ms-workspace test t1 [batch]               affected + critical modules for every changed repo of the batch
  ms-workspace test t2 [batch]               end-to-end command from [e2e] in workspace.toml
  ms-workspace integrate <batch> [--dry-run] merge agent branches into int/<batch> (conflicts detected first)
  ms-workspace ship <batch> [--yes] [--skip-e2e]   sync with base, test, push (plan only without --yes)
  ms-workspace clean [<batch>] [--force]     list batches, or remove one that is already merged
  ms-workspace log [-n N] [--day YYYY-MM-DD] [--action A]   show recent actions
  ms-workspace context                       ~15-line briefing (for a SessionStart hook)
  ms-workspace status [--fetch]              one line per repo: branch, ahead/behind base, dirty, batches
  ms-workspace claude-md [--print]           (re)generate <workspace>/CLAUDE.md; only the managed block is touched
  ms-workspace usage [--check] [--need PCT] [--json|--line]   plan usage: 5h session and 7d week, pace, verdict
  ms-workspace images [list|capture|backfill]   archive images pasted in chat into <workspace>/.ms-workspace/images/
  ms-workspace doctor                        check tools, versions, resources and workspace.toml
  ms-workspace guard                         PreToolUse hook: blocks git push / gh pr create|merge in batch worktrees

Workspace discovery: $MS_WORKSPACE, else the nearest parent holding workspace.toml.
"""


def main(argv: list[str]) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except AttributeError:
            pass
    cmd, args = (argv[0], argv[1:]) if argv else ("", [])
    try:
        return _dispatch(cmd, args)
    except MsError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    except BrokenPipeError:
        return 0
    except KeyboardInterrupt:
        return 130


def _dispatch(cmd: str, args: list[str]) -> int:
    if cmd in ("", "-h", "--help", "help"):
        print(USAGE, end="")
        return 0
    # Commands that must work (or stay silent) without a workspace.
    if cmd == "guard":
        from .guard import cmd_guard
        return cmd_guard()
    if cmd == "images":
        from .images import cmd_images
        return cmd_images(args)
    if cmd == "usage":
        from .usage import cmd_usage
        return cmd_usage(Workspace.load(required=False), args)
    if cmd == "context":
        from .overview import cmd_context
        return cmd_context(Workspace.load(required=False))
    if cmd == "doctor":
        from .overview import cmd_doctor
        return cmd_doctor(Workspace.load(required=False))

    from . import batches, claude_md, overview, runner
    table = {
        "batch": batches.cmd_batch, "agent": batches.cmd_agent, "affected": batches.cmd_affected,
        "env": batches.cmd_env, "integrate": batches.cmd_integrate, "ship": batches.cmd_ship,
        "clean": batches.cmd_clean, "test": runner.cmd_test, "log": overview.cmd_log,
        "status": overview.cmd_status, "claude-md": claude_md.cmd_claude_md,
    }
    if cmd not in table:
        print(f"ERROR: unknown command: {cmd}", file=sys.stderr)
        return 1
    return table[cmd](Workspace.load(), args)
