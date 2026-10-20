---
name: batch
description: Starts or inspects a batch of local work across the repos of a workspace. Creates isolated worktrees (one per repo, optionally one per agent) so changes never touch shared checkouts and nothing is pushed; for a small task it recommends a plain local branch instead and asks which the user prefers. Use when the user wants to start a feature or fix that spans repos, run several agents in parallel safely, or see which batches exist.
argument-hint: "[batch-name]"
allowed-tools: Bash(ms-workspace status:*) Bash(ms-workspace usage:*) Bash(ms-workspace batch new:*) Bash(ms-workspace agent new:*) Bash(ms-workspace memory:*)
---

# dynamia:batch

Opens a **batch**: one `int/<batch>` worktree per repo under `<workspace>/working-trees/<batch>/`. All work stays local until `/dynamia:ship`.

## Steps

0. **Check plan usage first**: `ms-workspace usage --check`. Exit 0 or 3 (no data): continue. Exit 1 or 2: show the printed numbers and use `AskUserQuestion` (continue / do a smaller step / stop) before doing anything else. If the user stops mid-batch, leave a handoff first: `ms-workspace memory add --type handoff --batch <batch> "state, next step, files touched"`. Never start something that cannot be finished in the remaining window.
1. **Orient cheaply.** Run `ms-workspace status` and `ms-workspace clean` (lists existing batches). If the user named an existing batch, skip to step 4.

   **Worktree or a plain branch?** A worktree is the default, not a rule. From `status` (current branch and `vs <base>`, dirty count) and the request, estimate whether the task fits a plain local branch in the repo's own checkout, to make a recommendation. Weigh:
   - Worktree gets priority when: the current branch is **not** the repo's base branch (the checkout already holds other work), the task is **new** (not a continuation of the branch you are on), the checkout is dirty, it spans several repos or modules, it needs parallel agents, or it is long or risky.
   - A plain branch fits when all of these hold: one repo, small and well-bounded (a few files), the checkout is clean, and it is on the base branch or already on the branch of this same task.
   - When unsure, recommend the worktree.
   Never pick for the user: give the recommendation and its reason in one line, and ask with `AskUserQuestion` (worktree / plain branch, recommended option first). You can fold this into the question round of step 2.
   If they choose the plain branch: `git switch -c <task-branch>` from the base branch (or stay on the task's branch), commit locally, run `ms-workspace test t0`, and skip steps 2-5. There is no `int/<batch>`; nothing is pushed from here. To publish it later the user runs `/dynamia:ship --branch` (it syncs, tests and pushes or opens a PR like a batch).

2. **Collect only what is missing** with one `AskUserQuestion` round:
   - Batch name (kebab-case; use `$ARGUMENTS` if given).
   - Which repos are involved (offer the names from `status`). Default to the smallest set that covers the task.

3. **Create the batch:**
   ```bash
   ms-workspace batch new <batch> <repo> [<repo>...]
   ```
   Then write the task list into `<workspace>/working-trees/<batch>/TASKS.md` (short checkbox lines; if the repo tracks work in GitHub issues, put only issue numbers there).
   If the DynamiaTasks MCP (`mcp__dynamia-tasks__*`, in development) is available, create and update the tasks through it instead of writing `TASKS.md`; `TASKS.md` stays the fallback.
   If the tracking mode is `ask` (`tasks = "ask"`, see the Tasks block of the workspace CLAUDE.md), do not write the file yet: ask with `AskUserQuestion` where the tasks go (local `TASKS.md` or a GitHub issue) and remember the answer for the rest of the session. Also confirm before creating any other local task file later in the session.

4. **Decide the agent layout.** Default to **one agent, no extra worktrees**: work directly in `working-trees/<batch>/<repo>`. Only when there are independent areas (different repos or modules that do not share files), create one worktree per agent:
   ```bash
   ms-workspace agent new <batch> <task> [<repo>...]
   ```
   Each parallel agent costs its own tokens; say so before creating more than two.

   `batch new` and `agent new` already copy the ignored files the repos need (`.env`, secrets). Before launching background agents run `ms-workspace env <batch> --setup --trust` (agents themselves may run `env --setup`; only `--trust` is blocked for them) so dependencies are installed and the trust dialog does not block them.

5. **Tell the user how to work in it**: `cd` into the worktree and run `claude`, or `claude --bg` per agent worktree and watch them with `claude agents`. To see the code in an IDE, suggest `ms-workspace open <batch>` (VS Code or IntelliJ, add `--agent <task>` for an agent's worktrees); the user runs it, it never changes Git. Remind that agents commit locally only and that `/dynamia:integrate` comes next.

## Notes
- Never run `git push` or `gh pr create` by hand, nor `ms-workspace clean`, from here. Publishing is `/dynamia:ship`, only when the user asks.
- To see what changed so far: `ms-workspace affected` (inside a worktree).
