---
name: ms-workspace-init
description: Creates (or updates) a multi-repo workspace from scratch. Asks which repos to include, clones the missing ones, detects each repo's stack and base branch, asks for dependencies, e2e and release branches, then writes workspace.toml and a short workspace-level CLAUDE.md. Use when the user wants to set up a new workspace, add a repo to an existing one, or bootstrap a new machine with its repos.
---

# ms-workspace-init

Builds a **workspace**: a folder with several related git repos plus a
`workspace.toml` that the rest of the `ms-*` workflow reads (batches,
integration, shipping). It works from zero: no folder, no repos, no config.

Token rule: do the mechanical work with the bundled script, ask the user only
what cannot be detected, and keep every question short.

## Steps

1. **Check for an existing workspace.** If the user gave a folder (or the cwd
   contains `workspace.toml`), read it and switch to *update mode*: only add or
   change what the user asks for. Otherwise continue to *new workspace*.

2. **Ask for the basics** in a single `AskUserQuestion` round when possible:
   - Workspace name and root folder (suggest `~/IdeaProjects/<name>` if unsure;
     create it if missing).
   - Which repos: GitHub `org/repo`, full URLs, or names of repos that already
     exist inside the root. Accept a free-text list.
   - Task tracking: `local` (a `TASKS.md` per batch, cheapest) or `github`
     (issues). Recommend `local`; see Notes.

3. **Clone what is missing** into the root, one directory per repo:
   ```bash
   git clone <url> "<root>/<repo>"
   ```
   Confirm with the user before cloning if there are more than 3 repos or
   the clone needs credentials. Report failures verbatim and continue with the
   rest.

4. **Detect each repo** with the bundled script (one JSON per repo, tiny output):
   ```bash
   bash ~/.claude/skills/ms-workspace-init/scripts/detect-repo.sh "<root>/<repo>"
   ```
   It returns the remote URL, default branch, suggested base branch (`next` if
   it exists), stacks (maven, gradle, pnpm, npm, yarn, go, python, rust) and a
   suggested test command.

5. **Show one compact table** (repo, base, stacks, test command) and ask only
   what is still unknown. Group these into as few questions as possible:
   - Base branch per repo, only if the suggestion looks wrong.
   - **Dependencies** between repos (which repo consumes which). Offer the
     repo names as options. Hint: shared SNAPSHOT versions in a `pom.xml`, or
     workspace/`file:` dependencies in `package.json`, usually reveal them.
   - **Release branches** per repo (e.g. `qa`, `main`), or none.
   - **e2e**: the command and the repo that owns it, or "none yet".
   - Whether the base branch accepts direct push (default: yes).
   - Optional, only if the user brings them up: `env = ["NAME=value"]` per repo (variables for its test, e2e and setup commands; never secrets) and `[ide]` (`default`, `code`, `idea`) for `ms-workspace open`. Both are documented in the example file.

6. **Write `<root>/workspace.toml`** following
   `~/.claude/skills/ms-workspace-init/references/workspace.example.toml`.
   - Do not write a `root` key: the workspace root is simply the folder that holds `workspace.toml`, so the file works on any machine.
   - For stacks with module-level selection, set `test.affected` (Maven:
     `-pl {modules} -amd`; pnpm: `pnpm --filter "...[origin/<base>]" test`).
     Otherwise reuse the full test command.
   - Never invent dependencies or e2e commands; leave `deps: []` / omit `e2e`
     if the user does not know.

7. **Generate `<root>/CLAUDE.md`** with the tool instead of writing it by hand:
   ```bash
   MS_WORKSPACE="<root>" ms-workspace claude-md
   ```
   It writes a short managed block (repos in dependency order, agent rules,
   batch flow, token and tool guidance, tracking mode) between
   `ms-workspace:begin/end` markers. Anything the user writes outside the
   markers is preserved, and the command can be re-run after any change to
   `workspace.toml`. Claude Code loads this file automatically from any repo
   below the workspace root.

8. **No `.gitignore` changes are needed**: batches (`.batches/`) and state (`.ms-workspace/`: logs, memory, archived images) live in the workspace root, outside every repo. Mention that the archived images can contain sensitive data.

9. **Report**: path of `workspace.toml`, the dependency order, what was
   cloned, and what was left blank (so the user knows what to fill in later).

## Notes

- **Update mode** must never overwrite user edits: read the current file, change
  only the requested keys, write it back.
- **Task tracking**: `local` keeps tasks in a small `TASKS.md` inside the batch
  folder, which agents read cheaply. `github` uses one tracking issue per
  batch (not per repo) to limit `gh` calls and tokens. Use it only when other
  people need visibility.
- This skill never pushes, opens PRs or changes remote branches.
- The workspace file contains no secrets: only URLs, branch names and commands.
