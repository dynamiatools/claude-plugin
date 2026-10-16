---
name: ms-setup
description: Installs or removes the ms-* hooks, status line and permission in Claude Code settings.json by merging them into the existing file, never overwriting other entries. Use after cloning the repo and running install.sh, when the hooks (guard, context, image archive) or the usage status line are missing, or when the user asks to enable or disable them.
argument-hint: "[--project] [--remove]"
disable-model-invocation: true
allowed-tools: Bash(ms-workspace doctor:*)
---

# ms-setup

Merges `settings/hooks.example.json` into a settings file. The merge is idempotent, keeps every other hook, permission and setting, keeps a status line that someone else configured, and writes a timestamped backup before changing anything.

Scope: `~/.claude/settings.json` by default, or the current project's `.claude/settings.json` with `--project`.

## Steps

1. **Check the tool is reachable**: `ms-workspace --help | head -1`. If it fails, tell the user to run `./install.sh` in the my-claude repo first and stop.

2. **Preview**: `ms-workspace setup-hooks --dry-run $ARGUMENTS`. Show the report: lines starting with `added` are what will change, `present` is already installed, `kept` is something left untouched on purpose (for example another status line).

3. **Confirm** with `AskUserQuestion`: apply to the user-level settings, apply to this project only, or cancel. If the report says `nothing to do` or `Already up to date`, say so and stop.

4. **Apply**: `ms-workspace setup-hooks $ARGUMENTS` (add `--project` if chosen). Report the backup path.

5. **Verify**: `ms-workspace doctor | sed -n '/Hooks:/,/Plan usage:/p'` and remind the user to start a new Claude Code session, because hooks load at session start.

## Notes
- To undo: `ms-workspace setup-hooks --remove`; it removes only what this tool added.
- If settings.json is not valid JSON the command stops without touching it; show the error and ask the user to fix the file.
- If another status line is already configured, usage tracking needs it chained to `ms-statusline`; explain this instead of overwriting it.
