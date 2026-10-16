# my-claude

Personal, portable [Claude Code](https://claude.com/claude-code) setup: skills, subagents, global `CLAUDE.md` instructions and settings that I reuse across machines and work teams.

The goal is simple: on a fresh machine, clone this repo, run the setup, and have everything needed to work with Claude Code right away.

## What's inside

```
my-claude/
├── install.sh       # One-step setup after cloning
├── bin/             # CLI tools (-> ~/.local/bin/): ms-workspace, ms-statusline
├── lib/             # ms_workspace Python package used by bin/ms-workspace
├── tests/           # unittest suite for the tools
├── skills/          # Reusable skills   (-> ~/.claude/skills/)
├── agents/          # Custom subagents  (-> ~/.claude/agents/)
└── CLAUDE.md        # Global instructions (-> ~/.claude/CLAUDE.md)
```

### Skills

All skills use the `ms-` prefix (so they never collide with other skills).

| Skill | What it does |
|---|---|
| `/ms-tmux-session` | Starts a tmux session with Claude Code (and Remote Control) in a project folder |
| `/ms-code-tunnel` | Opens a Cloudflare tunnel to the remote code viewer for the current repo |
| `/ms-git-status` | Prints a compact, read-only status card of the current git repo |
| `/ms-batch` | Starts or inspects a local batch of work across repos (isolated worktrees, optional per-agent worktrees) |
| `/ms-integrate` | Merges agent branches into the batch, detects conflicts, runs the incremental tests |
| `/ms-ship` | Publishes a validated batch (plan, confirmation, sync, tests, e2e, push). User-invoked only |
| `/ms-setup` | Merges the ms-* hooks, status line and permission into `settings.json` (preview, confirmation, backup, `--remove`). User-invoked only |
| `/ms-report` | How it is going: plan usage and pace, where tokens went, flaky or slow tests, cost per batch, and the next step |
| `/ms-workspace-init` | Builds a multi-repo workspace from scratch (clones repos, detects stacks, writes `workspace.toml`) |

### Agents

Read-only helpers. Three cheap ones run on Haiku so the main model does not spend tokens on reading and summarizing; `ms-agent-boss` runs on Opus for architecture reviews:

| Agent | Use |
|---|---|
| `ms-agent-scout` | Finds where code lives (paths and one-line reasons only) |
| `ms-agent-test-triage` | Classifies a failing test run (code bug, flaky, environment, config, build) and points to the file |
| `ms-agent-boss` | Opus architecture review of a batch, diff or design: boundaries, contracts, data, security, rollback, tests. Returns a verdict plus blocking and should-fix findings. It delegates discovery to the Haiku agents to save tokens |
| `ms-agent-summarizer` | Condenses diffs, history and logs; drafts commit messages following each repo's convention |

### Tools

| Tool | What it does |
|---|---|
| `ms-statusline` | Claude Code status line (`[model] ctx | 5h % | 7d %`) that also saves the plan-usage snapshot read by `ms-workspace usage`. Needs a Pro/Max plan |
| `ms-workspace` | Mechanical helper for the multi-repo batch workflow. Skills and hooks call it so the model spends no tokens on git/test plumbing. See the flow below |

`ms-workspace` is Python 3.11+ using only the standard library (no pip). `ms-statusline` stays a small bash+jq script because it runs on every status update.

**Batch flow** (all local until `ship`):

1. `ms-workspace batch new <batch> [repos]`: one worktree per repo on `int/<batch>`, branched from the base branch. Gitignored files that a fresh worktree lacks (`.env`, secrets) are copied from the main checkout using the repo's `.worktreeinclude`, `env_files` in `workspace.toml` and `.claude/settings.local.json`; tracked files are never copied. `ms-workspace env [batch] [--setup] [--trust]` repeats that, runs each repo's `setup` command, and marks the worktrees as trusted so background agents skip the trust dialog.
2. `ms-workspace agent new <batch> <task> [repos]`: an isolated worktree per agent (`agent/<batch>/<task>`), so parallel agents never touch the same files. Optional: a single agent can work directly in the `int/<batch>` worktree.
3. `ms-workspace test t0`: tests only what changed in the current repo. A passing run is remembered by a hash of the code (tree, uncommitted changes, in-batch dependencies) and the command, so repeating it on identical code is instant; use `--no-cache` to force a run. The memo does not see dependency or environment changes outside git.
4. `ms-workspace integrate <batch> [--dry-run]`: merges the agent branches into `int/<batch>` in dependency order, reporting conflicting files. `--dry-run` checks each branch against the current `int/<batch>` only, not against each other.
5. `ms-workspace test t1 <batch>`: affected modules plus the repo's `critical` modules, for every changed repo.
6. `ms-workspace plan <batch>` (or `ship` without `--yes`) shows exactly what would be sent: per repo the target branch, push mode, the commit subjects and a diffstat. It refuses while agent branches are not integrated into `int/<batch>`. `ms-workspace ship <batch>` prints that plan too. With `--yes` it merges the moved base branch, re-runs t1, runs the `[e2e]` command (or `--skip-e2e`), then pushes `int/<batch>` to the base branch (`push = "direct"`) or opens a PR (`push = "pr"`). It refuses release branches and never force-pushes.
7. `ms-workspace clean [<batch>]`: lists batches, or removes one whose `int/<batch>` is part of its base branch **and** whose agent branches are all integrated; otherwise it refuses and names the branches (`--force` is the explicit way to discard). Batch and task names are validated, and a failed `batch new` or `agent new` rolls back what it created.

**Plan usage.** Claude Code only exposes session (5h) and weekly (7d) usage to the status line, so `ms-statusline` stores a snapshot and `ms-workspace usage` reads it: percent used and left, time to reset, pace, projection and a verdict (`ok`/`warn`/`critical`, thresholds `[usage]` in `workspace.toml`, default 70/90). `usage --check` exits 0/1/2 (3 = no data) so skills and agents can ask for confirmation before starting; `--need <pct>` checks that a planned task fits. Pace and projections are linear and only influence the verdict above 50 % used. Data refreshes while a session is running, and is empty until the first reply of a session.

**Pasted images.** Claude Code does not save images pasted in chat as files; they exist only as base64 inside the session transcript. `ms-workspace images capture` (a Stop/SessionEnd hook) reads just the new part of the transcript and saves each image to `<workspace>/.ms-workspace/images/YYYY-MM-DD/HHMMSS_<session>_<n>.<ext>`, with an `index.jsonl` (time, session, directory, and the text sent with the image). Duplicates are skipped by hash, images only land in the workspace that contains the session's directory, and files older than `images_retention_days` (default 30) are pruned. `ms-workspace images [list -n N --day D]` shows recent ones and `images backfill` imports past sessions. Images may contain sensitive data: they stay local, outside any repo.

**Memory.** The log says what happened; `ms-workspace memory` keeps what was learned: one markdown note per fact under `.ms-workspace/memory/`, typed `decision`, `lesson`, `gotcha` or `handoff` (`add`, `list`, `search`, `show`, `forget`). `context` shows only a count, the latest handoff of each active batch and a few titles, so it costs a handful of tokens. A handoff is how an agent stops cleanly (usage critical, interrupted) and how the next session resumes; handoffs disappear when their batch is cleaned.

**Insights and token audit.** Test events in the log now carry duration, a hash of the code under test and the plan usage at that moment. `ms-workspace insights` turns that into slow runs, flaky candidates (same code, both pass and fail), time per batch and an approximate plan cost per batch, which `usage --need auto` uses as the median of completed batches (it needs at least 3). `ms-workspace tokens` reads Claude Code's local transcripts for sessions run inside the workspace and reports requests, new input, cache reads and output per batch or repo, the tools whose results were largest (characters divided by 4), repeated reads of one file, and hints. Everything stays local.

Also: `images`, `usage`, `log`, `affected`, `context`, `status [--fetch]`, `doctor`, `guard` (see Hooks) and `claude-md`.

**Workspace CLAUDE.md.** `ms-workspace claude-md` (run by `/ms-workspace-init`) generates `<workspace>/CLAUDE.md`: repos in dependency order, agent rules, the batch flow, token and tool guidance. Only the block between the `ms-workspace:begin/end` markers is managed, so your own notes around it survive every regeneration.

`ms-workspace` keeps an action log in `<workspace>/.ms-workspace/logs/YYYY-MM-DD.jsonl` (one JSON line per action, one file per day, old files pruned after `log_retention_days`, default 14). Read it with `ms-workspace log [-n N] [--day D] [--action A]`.

#### Hooks

`install.sh` never edits your `settings.json`. Run **`/ms-setup`** (or `ms-workspace setup-hooks`) to merge `settings/hooks.example.json` into it. The merge is idempotent, shows a preview first (`--dry-run`), keeps every other hook, permission and setting, keeps a status line someone else configured, writes a timestamped backup, and `--remove` takes out only what it added. `ms-workspace doctor` reports whether the hooks are installed.

- `ms-workspace guard` (PreToolUse on Bash) blocks `git push`, `gh pr create|merge` and `ms-workspace ship|clean` **only inside batch worktrees**, so agents commit locally and a human integrates. Blocked attempts are logged.
- `ms-workspace images capture` (Stop and SessionEnd) archives images pasted in chat; see below.
- `ms-statusline` (as `statusLine`) shows usage in the footer and feeds `ms-workspace usage`.
- `ms-workspace context` (SessionStart) injects a short briefing (active batches, open tasks, plan usage, memory and handoffs, last actions) so the agent does not have to explore. It prints nothing outside a workspace.
- **Permissions are narrow on purpose.** `allow` covers read-only and local subcommands (`status`, `log`, `usage`, `plan`, `test`, `integrate`, `batch new`, ...). `ship`, `clean`, `env` and `setup-hooks` are in `ask`, so Claude Code always prompts before anything is pushed, deleted or run from configuration. An older broad `Bash(ms-workspace:*)` rule is removed by `setup-hooks`.
- **The guard fails closed.** Inside `.batches/` it decides from the command text alone (a real parser: option variants, `bash -c`, `eval`, wrappers, `cd` into a batch from elsewhere), never from `workspace.toml`, so a broken config cannot open the gate. It exists to stop mistakes and realistic variants, not a determined adversary.

## Quick start (new machine)

```bash
git clone <repo-url> ~/IdeaProjects/my-claude
cd ~/IdeaProjects/my-claude
./install.sh
```

`install.sh` is idempotent and links everything into `~/.claude` with symlinks, so this repo stays the single source of truth: edit here, `git commit`, share.

- `./install.sh --dry-run` shows what would change without touching anything.
- `./install.sh --uninstall` removes only the links that point to this repo.
- `CLAUDE.md` is linked as your global instructions. If you already have one, it is backed up (see below), and anything it imports such as `@RTK.md` is no longer loaded; the rtk hook keeps working without it.
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

## Tests

```bash
python3 -m unittest discover -s tests          # about 45 s; every test uses throwaway repos and a private HOME
python3 -m unittest tests.test_ms_workspace.TestShip -v
```

The suite drives the real CLI (bare remotes, worktrees, conflicts, hooks, usage snapshots, pasted images), so it also works as a spec when the implementation changes. Set `MS_WORKSPACE_BIN` to run it against another build of the tool.

## Adding a new skill

1. Create `skills/<skill-name>/SKILL.md` with `name` and `description` frontmatter.
2. Write clear trigger conditions in `description` — that is what Claude uses to decide when to load it.
3. Run `./install.sh` to link it and test it in a session.
4. Commit and push.

## Roadmap

- [ ] Import existing skills and agents from `~/.claude`
- [x] Global `CLAUDE.md` (RTK.md is not needed: the rtk hook works without it)
- [ ] Sanitized `settings.json` template
- [x] `install.sh` to link everything idempotently
- [ ] Document required external tools (e.g. `tmux`, `rtk`)
- [x] `ms-workspace`: batch new, agent new, affected, test t0/t1/t2, integrate, ship, clean, log, context, status, doctor, guard
- [x] `ms-workspace`: env, per-repo task mode, test-result memo, configurable `[tools]` policy
- [x] Skills that wrap `ms-workspace` (`ms-batch`, `ms-integrate`, `ms-ship`) and Haiku agents
- [x] Portable global `CLAUDE.md` (about 380 words, loaded in every session)
