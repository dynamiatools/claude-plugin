---
name: dev-env
description: Registers development environment variables in the workspace's workspace.toml by asking which ones are needed, for one repo or all of them, and lists or removes them. They reach the test, e2e and setup commands the workspace runs. Use when the user wants to add, change, list or remove env vars for local development, or says a test or app needs a variable.
argument-hint: "[NAME=value ...]"
allowed-tools: Bash(ms-workspace dev-env list:*)
---

# dynamia:dev-env

Development variables live in `<project>/.dynamia/workspace.toml`:

```toml
[dev.env]              # every repo
API_URL = "http://localhost:8080"
[repos.erp.dev.env]    # one repo, wins over [dev.env]
DEBUG = "1"
```

`ms-workspace` applies them to the test, e2e and `env --setup` commands of the workspace (not to anything else), and a changed value invalidates a cached passing test. The tool edits only these tables, so comments and the rest of the file stay as they are. Values are plain text: this is for local development, not for secrets that matter.

## Steps

1. **See what exists**: `ms-workspace dev-env list`. If it fails with "no .dynamia/workspace.toml", run `/dynamia:workspace-init` first.

2. **Find out what is needed.** If `$ARGUMENTS` has `NAME=value` pairs, use them. Otherwise ask, in chat, for the variables as `NAME=value` lines, and for each (or for all) whether it applies to every repo or to one; list the repo names from step 1 so the user can pick. Suggest likely names from the repo only when the user asks (for example a variable that a test or an `.env.example` mentions).

3. **Check before writing.** A name that looks secret (PASSWORD, TOKEN, SECRET, KEY, AUTH...) goes into a plain file: say so once and ask to confirm. Never write a value the user did not give.

4. **Register** each one:
   ```bash
   ms-workspace dev-env add NAME=value [--repo R]
   ```
   Setting a name again replaces its value. Remove with `ms-workspace dev-env rm NAME [--repo R]`.

5. **Report** with `ms-workspace dev-env list` (secret-looking values are shown as `***`; `--show` reveals them, use it only if the user asks).

## Notes
- The `/env-panel` slash command of the plugin (panel with fields, or `/env-panel NAME=value [repo]`) does the same from the prompt.
- These variables are not added to the shell Claude uses for other commands, and not to `ship`.
