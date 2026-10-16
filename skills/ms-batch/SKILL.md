---
name: ms-batch
description: Starts or inspects a batch of local work across the repos of a workspace. Creates isolated worktrees (one per repo, optionally one per agent) so changes never touch shared checkouts and nothing is pushed. Use when the user wants to start a feature or fix that spans repos, run several agents in parallel safely, or see which batches exist.
argument-hint: "[batch-name]"
allowed-tools: Bash(ms-workspace:*)
---

# ms-batch

Opens a **batch**: one `int/<batch>` worktree per repo under `<workspace>/.batches/<batch>/`. All work stays local until `/ms-ship`.

## Steps

0. **Check plan usage first**: `ms-workspace usage --check`. Exit 0 or 3 (no data): continue. Exit 1 or 2: show the printed numbers and use `AskUserQuestion` (continue / do a smaller step / stop) before doing anything else. Never start something that cannot be finished in the remaining window.
1. **Orient cheaply.** Run `ms-workspace status` and `ms-workspace clean` (lists existing batches). If the user named an existing batch, skip to step 4.

2. **Collect only what is missing** with one `AskUserQuestion` round:
   - Batch name (kebab-case; use `$ARGUMENTS` if given).
   - Which repos are involved (offer the names from `status`). Default to the smallest set that covers the task.

3. **Create the batch:**
   ```bash
   ms-workspace batch new <batch> <repo> [<repo>...]
   ```
   Then write the task list into `<workspace>/.batches/<batch>/TASKS.md` (short checkbox lines; if the repo tracks work in GitHub issues, put only issue numbers there).

4. **Decide the agent layout.** Default to **one agent, no extra worktrees**: work directly in `.batches/<batch>/<repo>`. Only when there are independent areas (different repos or modules that do not share files), create one worktree per agent:
   ```bash
   ms-workspace agent new <batch> <task> [<repo>...]
   ```
   Each parallel agent costs its own tokens; say so before creating more than two.

   `batch new` and `agent new` already copy the ignored files the repos need (`.env`, secrets). Before launching background agents run `ms-workspace env <batch> --setup --trust` so dependencies are installed and the trust dialog does not block them.

5. **Tell the user how to work in it**: `cd` into the worktree and run `claude`, or `claude --bg` per agent worktree and watch them with `claude agents`. Remind that agents commit locally only and that `/ms-integrate` comes next.

## Notes
- Never run `git push`, `gh pr create`, or `ms-workspace ship|clean` from here.
- To see what changed so far: `ms-workspace affected` (inside a worktree).
