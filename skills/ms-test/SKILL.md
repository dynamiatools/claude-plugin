---
name: ms-test
description: Runs the workspace test levels with ms-workspace test, t0 for what changed here, t1 for a whole batch, t2 for end to end. Use when the user asks to test, run the tests or check that a change works.
argument-hint: "t0 | t1 [batch] | t2 [batch]"
---

# ms-test

| Level | Command | Tests |
|---|---|---|
| t0 | `ms-workspace test t0` | what changed in the current repo; a pass is remembered by code hash, `--no-cache` forces a run |
| t1 | `ms-workspace test t1 [batch]` | affected plus `critical` modules of every changed repo of the batch |
| t2 | `ms-workspace test t2 [batch]` | the `[e2e]` command |

## Steps
1. Default to `t0` inside a worktree, `t1` when the user names a batch, `t2` only when asked.
2. Show the PASS/FAIL line. On failure hand the printed output to the `ms-agent-test-triage` agent first and fix only what it points to; when JUnit reports exist the tool already prints a summary.
3. Say plainly when a result was cached ("same code and command already passed").
4. Repo `env = [...]` variables from `workspace.toml` are applied by the tool; do not export them by hand.
