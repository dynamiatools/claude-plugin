---
name: ms-integrate
description: Merges the agent branches of a batch into its integration branch, detects conflicts before they happen, and runs the incremental tests (t1). Use after parallel agents finish, or when the user asks to join, merge or validate the work of a batch locally.
argument-hint: "<batch-name>"
allowed-tools: Bash(ms-workspace:*)
---

# ms-integrate

Joins agent work into `int/<batch>` and validates it. Local only: nothing is pushed.

## Steps

0. **Check plan usage first**: `ms-workspace usage --check --need 10`. Exit 0 or 3 (no data): continue. Exit 1 or 2: show the printed numbers and use `AskUserQuestion` (continue / do a smaller step / stop) before doing anything else. Never start something that cannot be finished in the remaining window.
1. **Pick the batch**: `$ARGUMENTS`, or run `ms-workspace clean` to list batches and ask if ambiguous.

2. **Preview**: `ms-workspace integrate <batch> --dry-run`. It checks each agent branch against the current integration branch only; two agents that clash with each other show up in step 3.

3. **Integrate**: `ms-workspace integrate <batch>`.
   - On `CONFLICT <branch> -> <files>`: the earlier branches are already merged. Open only the conflicting files, resolve them by keeping both intents (ask the user when intent is unclear), commit in the batch worktree, and run step 3 again. Do not use `--force` style shortcuts.

4. **Validate**: `ms-workspace test t1 <batch>`.
   - On failure, delegate the first analysis to the `ms-agent-test-triage` agent (cheap model) with the printed output, then fix only what it points to.

5. **Report** in at most 6 lines: merged branches, conflicts resolved, t1 result. If everything passed, suggest `/ms-ship <batch>`.

## Notes
- Do not run `ms-workspace ship` or `clean` here.
- Use `ms-workspace log -n 10` to recall what already happened in this batch instead of re-reading git history.
