---
name: ship
description: Publishes a validated batch to each repo's base branch (direct push or PR, per workspace.toml) after syncing with the remote, re-running the incremental tests and the end-to-end command. Use when the user explicitly asks to ship, publish or push a batch, or to open a pull request (PR) for it; "open a PR" means ship with --pr. Never on your own initiative.
argument-hint: "<batch-name> [--pr|--direct]"
allowed-tools: Bash(ms-workspace usage:*) Bash(ms-workspace plan:*)
---

# dynamia:ship

The only step that touches remotes. It never targets release branches and never force-pushes.

It works from the workspace root or from inside the batch worktree. In a batch worktree the guard blocks `git push`, `gh pr create` and `ship --skip-gate` typed by hand, so always go through `ms-workspace ship`.

**What the user's words mean**
- "open a PR", "abre un PR", "crea el pull request" -> `--pr`: every repo gets `int/<batch>` pushed and a PR to its base branch, whatever its `push` setting.
- "ship", "publish", "push it", "sube esto" -> no `--pr`: each repo uses its configured `push` mode (`direct` pushes to the base branch, `pr` opens a PR).
- If a repo has `push = "ask"`, always ask (PR or direct push) before step 2 and pass the answer as `--pr` or `--direct`; `plan` and `ship` refuse to run without one.
- If it is unclear whether they want a PR or a direct push, ask before step 2: a direct push cannot be undone with a close button.
- An explicit request for a PR is enough: go straight to the plan with `--pr`, without asking whether they would rather push directly.
- "We are done for today" or any plain request to publish is **not** a request for a PR: use the configured mode.

## Steps

0. **Check plan usage first**: `ms-workspace usage --check --need 5`. Exit 0 or 3 (no data): continue. Exit 1 or 2: show the printed numbers and use `AskUserQuestion` (continue / do a smaller step / stop) before doing anything else. If the user stops mid-batch, leave a handoff first: `ms-workspace memory add --type handoff --batch <batch> "state, next step, files touched"`. Never start something that cannot be finished in the remaining window.
1. **Pick the batch**: `$ARGUMENTS`, or list with `ms-workspace clean`.

2. **Show the plan**: `ms-workspace plan <batch> [--pr]`. For every repo it lists the target branch, push mode, the commit subjects that would be sent and a diffstat. It refuses while agent branches are not integrated: run `/dynamia:integrate` first.

   If the plan prints `RECOMMEND A PR` (many files, lines or new files) and the user did not ask for a PR, relay it in one line and offer the choice: open a PR (recommended for a big change) or push as configured. Never switch to a PR on your own; the user decides.

3. **Confirm with the user** using `AskUserQuestion`, quoting the plan (repos, target branches and commit subjects so they see exactly what will be sent): ship now, ship with `--skip-e2e` (only if no e2e exists or the user explicitly accepts the risk), or stop. Never assume consent from earlier messages.

4. **Ship**: `ms-workspace ship <batch> --yes [--pr]` (Claude Code asks for permission on this command by design; do not try to avoid it) (add `--skip-e2e` only if chosen). Never pass `--skip-gate`: the guard blocks it.
   - Base moved: it merges `origin/<base>` into the batch and re-runs the tests; this is expected.
   - Conflict, failed t1/e2e, or a rejected push: nothing further is pushed. Report the exact error and stop; do not retry blindly.

5. **After success**: ask whether to run `ms-workspace clean <batch>` (removes worktrees and local branches), and report the pushed repos in one line each, with the t1/e2e result taken from the ship output and anything skipped (`--skip-e2e`, repos without tests).

## Notes
- Promotion from the base branch to QA/production is a separate, human decision outside this skill.
- Everything is logged: `ms-workspace log --action ship`.
