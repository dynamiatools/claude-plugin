---
name: ms-open
description: Opens a batch (or one agent's worktrees) in VS Code or IntelliJ IDEA with ms-workspace open. It never changes Git. Use when the user asks to open, show or see a batch, a repo or an agent's work in the IDE.
argument-hint: "<batch> [--ide code|idea] [--repo R] [--agent TASK]"
---

# ms-open

Opens the real worktree paths of a batch in an IDE. Read-only for Git: no checkout, commit, merge or push.

## Steps

1. **Pick the batch.** Use the one the user named. If none, run `ms-workspace clean` (lists batches) and ask which one only if several exist.
2. **Preview** (cheap, changes nothing):
   ```bash
   ms-workspace open <batch> [--ide code|idea] [--repo R] [--agent TASK] --dry-run
   ```
   If it says no IDE was found, show the message and stop: the user sets `[ide]` in `workspace.toml` (see the example file).
3. **Open** only if the user asked for it in this conversation (the command needs their approval anyway): rerun without `--dry-run`.
4. **Report** in one line what was opened. Mention the IDE-specific note it printed, if any (IntelliJ without `.idea/` in the repo's ignore file).

## Notes
- VS Code gets one window per batch (and per agent). IntelliJ gets one window per repo; use `--repo` to open just one.
- On a server without a display the launch can fail: say so, do not retry.
