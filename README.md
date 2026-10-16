# my-claude

Personal, portable [Claude Code](https://claude.com/claude-code) setup: skills, subagents, global `CLAUDE.md` instructions and settings that I reuse across machines and work teams.

The goal is simple: on a fresh machine, clone this repo, run the setup, and have everything needed to work with Claude Code right away.

## What's inside

```
my-claude/
├── install.sh       # One-step setup after cloning
├── bin/             # CLI tools (-> ~/.local/bin/), e.g. ms-workspace
├── skills/          # Reusable skills   (-> ~/.claude/skills/)
├── agents/          # Custom subagents  (-> ~/.claude/agents/)   [planned]
├── CLAUDE.md        # Global instructions (-> ~/.claude/CLAUDE.md) [planned]
└── RTK.md           # Extra instructions imported from CLAUDE.md   [planned]
```

### Skills

All skills use the `ms-` prefix (so they never collide with other skills).

| Skill | What it does |
|---|---|
| `/ms-tmux-session` | Starts a tmux session with Claude Code (and Remote Control) in a project folder |
| `/ms-code-tunnel` | Opens a Cloudflare tunnel to the remote code viewer for the current repo |
| `/ms-git-status` | Prints a compact, read-only status card of the current git repo |
| `/ms-workspace-init` | Builds a multi-repo workspace from scratch (clones repos, detects stacks, writes `workspace.toml`) |

### Tools

| Tool | What it does |
|---|---|
| `ms-workspace` | Mechanical helper for the multi-repo batch workflow. Skills and hooks call it so the model spends no tokens on git/test plumbing. See the flow below |

**Batch flow** (all local until `ship`):

1. `ms-workspace batch new <batch> [repos]`: one worktree per repo on `int/<batch>`, branched from the base branch.
2. `ms-workspace agent new <batch> <task> [repos]`: an isolated worktree per agent (`agent/<batch>/<task>`), so parallel agents never touch the same files. Optional: a single agent can work directly in the `int/<batch>` worktree.
3. `ms-workspace test t0`: tests only what changed in the current repo.
4. `ms-workspace integrate <batch> [--dry-run]`: merges the agent branches into `int/<batch>` in dependency order, reporting conflicting files. `--dry-run` checks each branch against the current `int/<batch>` only, not against each other.
5. `ms-workspace test t1 <batch>`: affected modules plus the repo's `critical` modules, for every changed repo.
6. `ms-workspace ship <batch>`: prints the plan. With `--yes` it merges the moved base branch, re-runs t1, runs the `[e2e]` command (or `--skip-e2e`), then pushes `int/<batch>` to the base branch (`push = "direct"`) or opens a PR (`push = "pr"`). It refuses release branches and never force-pushes.
7. `ms-workspace clean [<batch>]`: lists batches, or removes a merged one (worktrees and local branches).

Also: `log`, `affected`, `context`, `status [--fetch]`, `doctor` and `guard` (see Hooks).

`ms-workspace` keeps an action log in `<workspace>/.ms-workspace/logs/YYYY-MM-DD.jsonl` (one JSON line per action, one file per day, old files pruned after `log_retention_days`, default 14). Read it with `ms-workspace log [-n N] [--day D] [--action A]`.

#### Hooks

`install.sh` never edits your `settings.json`. To enable the hooks, merge `settings/hooks.example.json` into `~/.claude/settings.json` (or a project's `.claude/settings.json`):

- `ms-workspace guard` (PreToolUse on Bash) blocks `git push`, `gh pr create|merge` and `ms-workspace ship|clean` **only inside batch worktrees**, so agents commit locally and a human integrates. Blocked attempts are logged.
- `ms-workspace context` (SessionStart) injects a ~15-line briefing (active batches, open tasks, last actions) so the agent does not have to explore. It prints nothing outside a workspace.
- The `permissions.allow` entry avoids a prompt on every `ms-workspace` call.

## Quick start (new machine)

```bash
git clone <repo-url> ~/IdeaProjects/my-claude
cd ~/IdeaProjects/my-claude
./install.sh
```

`install.sh` is idempotent and links everything into `~/.claude` with symlinks, so this repo stays the single source of truth: edit here, `git commit`, share.

- `./install.sh --dry-run` shows what would change without touching anything.
- `./install.sh --uninstall` removes only the links that point to this repo.
- Existing files with the same name are moved to `~/.claude/backups/my-claude-<timestamp>/`, never deleted.
- Set `CLAUDE_HOME` / `BIN_DIR` to target directories other than `~/.claude` / `~/.local/bin`.
- It also checks for `git`, `jq`, `tmux`, `gh`, `node` and `claude` and warns about missing ones.

Start a new Claude Code session afterwards so the skills are picked up.

## Conventions

- **Language:** everything in this repo (docs, skills, comments) is written in English.
- **One skill per directory:** `skills/<skill-name>/SKILL.md`, with optional supporting files next to it.
- **One agent per file:** `agents/<agent-name>.md` with the usual frontmatter (`name`, `description`, `tools`).
- **No secrets:** never commit tokens, credentials or machine-specific paths. Use templates and placeholders instead.
- **Keep skills generic:** a skill should work on any machine; anything environment-specific belongs in settings or in a local override.

## Adding a new skill

1. Create `skills/<skill-name>/SKILL.md` with `name` and `description` frontmatter.
2. Write clear trigger conditions in `description` — that is what Claude uses to decide when to load it.
3. Run `./install.sh` to link it and test it in a session.
4. Commit and push.

## Roadmap

- [ ] Import existing skills and agents from `~/.claude`
- [ ] Global `CLAUDE.md` and `RTK.md`
- [ ] Sanitized `settings.json` template
- [x] `install.sh` to link everything idempotently
- [ ] Document required external tools (e.g. `tmux`, `rtk`)
- [x] `ms-workspace`: batch new, agent new, affected, test t0/t1/t2, integrate, ship, clean, log, context, status, doctor, guard
- [ ] `ms-workspace`: env (copy ignored files into worktrees), per-repo task mode, test-result memo by tree hash
- [ ] Skills that wrap `ms-workspace` (`ms-batch`, `ms-integrate`, `ms-ship`)
- [ ] Haiku-based agents (`ms-scout`, `ms-test-triage`) and a `[tools]` policy in `workspace.toml`
