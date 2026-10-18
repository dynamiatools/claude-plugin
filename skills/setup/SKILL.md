---
name: setup
description: Finishes the dynamia setup in Claude Code settings.json, the part a plugin cannot do itself (status line and permissions), by merging into the existing file without overwriting other entries. Use right after installing the plugin, after a plugin update, or when the status line or permissions are missing.
argument-hint: "[--project] [--remove]"
disable-model-invocation: true
allowed-tools: Bash(ms-workspace doctor:*), Bash(ms-workspace --help:*)
---

# dynamia:setup

A plugin ships skills, agents, hooks and `bin/`, but it cannot set `statusLine` or `permissions`. This skill does that part by merging `settings/hooks.example.json` into a settings file. The merge is idempotent, keeps every other hook, permission and setting, keeps a status line that someone else configured, and writes a timestamped backup before changing anything.

Scope: `~/.claude/settings.json` by default, or the current project's `.claude/settings.json` with `--project`.

## Steps

1. **Pick the mode**: if this skill runs from the installed plugin, its folder is `${CLAUDE_PLUGIN_ROOT}`; use it as `--plugin-root "${CLAUDE_PLUGIN_ROOT}"` (the plugin provides the hooks, so they are not copied into settings.json, and an older copy of them is removed). The plugin's `bin/` is on the PATH of the Bash tool, so use `"${CLAUDE_PLUGIN_ROOT}/bin/ms-workspace"` for every command below if `ms-workspace` is not found. Without the plugin (a clone plus `./install.sh`), omit `--plugin-root` and check `ms-workspace --help | head -1`; if that fails, tell the user to run `./install.sh` and stop.

2. **Preview**: `ms-workspace setup-hooks --dry-run --plugin-root "${CLAUDE_PLUGIN_ROOT}" $ARGUMENTS`. Show the report: lines starting with `added` are what will change, `present` is already installed, `kept` is something left untouched on purpose (for example another status line).

3. **Confirm** with `AskUserQuestion`: apply to the user-level settings, apply to this project only, or cancel. If the report says `nothing to do` or `Already up to date`, say so and stop.

4. **Apply**: the same command without `--dry-run` (add `--project` if chosen). Report the backup path.

5. **Verify**: `ms-workspace doctor | sed -n '/Hooks:/,/Plan usage:/p'` and remind the user to start a new Claude Code session, because hooks load at session start.

## Notes
- The status line path contains the plugin version, so run this skill again after `/plugin update`.
- To undo: `ms-workspace setup-hooks --remove`; it removes only what this tool added.
- If settings.json is not valid JSON the command stops without touching it; show the error and ask the user to fix the file.
- If another status line is already configured, usage tracking needs it chained to `ms-statusline`; explain this instead of overwriting it.
