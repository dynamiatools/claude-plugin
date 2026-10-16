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
| `ms-workspace` | Mechanical helper for the multi-repo batch workflow. Skills and hooks call it so the model spends no tokens on git/test plumbing. Implemented so far: `batch new`, `affected`, `test t0`, `log` |

`ms-workspace` keeps an action log in `<workspace>/.ms-workspace/logs/YYYY-MM-DD.jsonl` (one JSON line per action, one file per day, old files pruned after `log_retention_days`, default 14). Read it with `ms-workspace log [-n N] [--day D] [--action A]`.

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
- [ ] `ws` script and hooks for the multi-repo batch workflow (local integration, incremental tests)
