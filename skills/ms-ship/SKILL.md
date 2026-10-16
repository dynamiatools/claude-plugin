---
name: ms-ship
description: Publishes a validated batch to each repo's base branch (direct push or PR, per workspace.toml) after syncing with the remote, re-running the incremental tests and the end-to-end command. Use only when the user explicitly asks to ship, publish or push a batch.
argument-hint: "<batch-name>"
disable-model-invocation: true
allowed-tools: Bash(ms-workspace:*)
---

# ms-ship

The only step that touches remotes. It never targets release branches and never force-pushes.

Run it from the workspace root (not from inside a batch worktree: a hook blocks `ship` there on purpose).

## Steps

0. **Check plan usage first**: `ms-workspace usage --check --need 5`. Exit 0 or 3 (no data): continue. Exit 1 or 2: show the printed numbers and use `AskUserQuestion` (continue / do a smaller step / stop) before doing anything else. Never start something that cannot be finished in the remaining window.
1. **Pick the batch**: `$ARGUMENTS`, or list with `ms-workspace clean`.

2. **Show the plan**: `ms-workspace ship <batch>` (plan only). It lists, per repo, the target branch, push mode and commit count.

3. **Confirm with the user** using `AskUserQuestion`, quoting the plan: ship now, ship with `--skip-e2e` (only if no e2e exists or the user explicitly accepts the risk), or stop. Never assume consent from earlier messages.

4. **Ship**: `ms-workspace ship <batch> --yes` (add `--skip-e2e` only if chosen).
   - Base moved: it merges `origin/<base>` into the batch and re-runs the tests; this is expected.
   - Conflict, failed t1/e2e, or a rejected push: nothing further is pushed. Report the exact error and stop; do not retry blindly.

5. **After success**: ask whether to run `ms-workspace clean <batch>` (removes worktrees and local branches), and report the pushed repos in one line each.

## Notes
- Promotion from the base branch to QA/production is a separate, human decision outside this skill.
- Everything is logged: `ms-workspace log --action ship`.
