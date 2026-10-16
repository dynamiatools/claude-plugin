# my-claude

My portable [Claude Code](https://claude.com/claude-code) setup: skills, subagents, global instructions and a small tool (`ms-workspace`) for safe, token-cheap work across several repos. Clone it on any machine, run one script, and everything is ready.

## Quick start

```bash
git clone <repo-url> ~/IdeaProjects/my-claude
cd ~/IdeaProjects/my-claude
./install.sh --dry-run     # optional: preview
./install.sh               # link skills, agents, CLAUDE.md and the tools
```

Then, in a **new** Claude Code session:

1. `/ms-setup`: merges the hooks, status line and permissions into your `settings.json` (preview, confirmation, backup; `--remove` undoes it).
2. `/ms-workspace-init`: builds a workspace from scratch (asks which repos, clones them, detects stacks, writes `workspace.toml` and a workspace `CLAUDE.md`).
3. `/ms-batch`: opens a batch of local work. From there: work, `/ms-integrate`, `/ms-ship`.

About `install.sh`:
- It is idempotent and uses symlinks, so this repo stays the single source of truth: edit here, commit, share.
- Files that already exist are moved to `~/.claude/backups/my-claude-<timestamp>/`, never deleted. Your own `~/.claude/CLAUDE.md` is replaced by the one in this repo (backed up first); an `@RTK.md` import in it is no longer loaded, the rtk hook keeps working.
- `--uninstall` removes only links that point to this repo. `CLAUDE_HOME` and `BIN_DIR` redirect the targets (defaults `~/.claude` and `~/.local/bin`; make sure `BIN_DIR` is in your `PATH`).
- It warns about missing `git`, `jq`, `python3 >= 3.11`, `tmux`, `gh`, `node` and `claude`. `ms-workspace doctor` checks the same, plus your workspace.

## What's inside

```
install.sh   bin/ (ms-workspace, ms-statusline)   lib/ms_workspace/ (the tool)
skills/      agents/      CLAUDE.md (global instructions)   settings/ (hooks example)   tests/
```

Everything uses the `ms-` prefix so nothing collides with other skills; agents are `ms-agent-*` so they stand out in the `/` list.

**Skills**

| Skill | What it does |
|---|---|
| `/ms-workspace-init` | Creates or updates a multi-repo workspace from scratch |
| `/ms-batch` | Starts a batch: one isolated worktree per repo, optionally one per agent |
| `/ms-integrate` | Merges the agents' branches, reports conflicts, runs the incremental tests |
| `/ms-ship` | Shows what would be sent, asks, syncs, tests, pushes. User-invoked only |
| `/ms-setup` | Installs or removes the hooks, status line and permissions in `settings.json`. User-invoked only |
| `/ms-report` | How it is going: plan usage, where tokens went, flaky or slow tests, next step |
| `/ms-tmux-session` | Starts a tmux session with Claude Code (and Remote Control) in a project folder |
| `/ms-code-tunnel` | Opens a Cloudflare tunnel to the remote code viewer for the current repo |
| `/ms-git-status` | Compact, read-only status card of the current git repo |

**Agents** (read-only; the first three run on Haiku so the main model does not spend tokens on reading and summarizing)

| Agent | Use |
|---|---|
| `ms-agent-scout` | Finds where code lives: paths and one line each |
| `ms-agent-test-triage` | Classifies a failing run (code, test, flaky, environment, config, build) and points to the file |
| `ms-agent-summarizer` | Condenses diffs, history and logs; drafts commit messages in each repo's style |
| `ms-agent-boss` | Opus architecture review of a batch, diff or design; returns a verdict plus blocking and should-fix findings |

**Tools**: `ms-workspace` (Python 3.11+, standard library only) does the git, test and bookkeeping work so the model does not; `ms-statusline` (bash + jq) shows usage in the footer and saves the plan-usage snapshot.

## The batch workflow

Everything stays local until `ship`. Agents commit locally and never push.

| Step | Command | What happens |
|---|---|---|
| 1 | `batch new <batch> [repos]` | One worktree per repo on `int/<batch>`, branched from the base branch (for example `next`). Ignored files a fresh worktree lacks (`.env`, secrets) are copied from the main checkout; tracked files never are |
| 2 | `agent new <batch> <task> [repos]` | Optional isolated worktree per parallel agent (`agent/<batch>/<task>`), so agents never touch the same files |
| 3 | `test t0` | Tests only what changed in the current repo. A pass is remembered by a hash of the code and command, so repeating it is instant (`--no-cache` forces a run) |
| 4 | `integrate <batch> [--dry-run]` | Merges the agent branches into `int/<batch>` in dependency order and names conflicting files. `--dry-run` checks each branch against `int/<batch>` only, not against each other |
| 5 | `test t1 <batch>` | Affected modules plus the repo's `critical` modules, for each changed repo |
| 6 | `plan <batch>` | Shows what would be sent: per repo the target branch, push mode, commit subjects and a diffstat. Refuses while agent branches are not integrated |
| 7 | `ship <batch> --yes` | Merges a moved base branch, re-runs t1, runs the `[e2e]` command (or `--skip-e2e`), then pushes `int/<batch>` to the base branch (`push = "direct"`) or opens a PR (`push = "pr"`, needs `gh`). Never targets a `release` branch, never force-pushes |
| 8 | `undo <batch> [--yes]` | Reverts the last ship: every `ship --yes` records what each base branch pointed to before and after. `undo` shows the plan; with `--yes` it pushes one new commit per repo that restores the previous tree (history kept, never a force-push). If someone else pushed in the meantime it refuses for that repo and prints the exact `git revert` commands; in `pr` mode it prints how to close the PR. Works after `clean` too |
| 9 | `clean [<batch>]` | Lists batches, or removes one whose branch is in its base branch **and** whose agent branches are all integrated; otherwise it refuses and names them (`--force` discards on purpose) |

Names are validated, and a failed `batch new` or `agent new` rolls back what it created. `ms-workspace env [batch] [--setup] [--trust]` re-copies ignored files, runs each repo's `setup` command and marks worktrees as trusted so background agents skip the trust dialog.

## Guardrails

- **Permissions are narrow on purpose.** `allow` covers read-only and local subcommands (`status`, `log`, `usage`, `plan`, `test`, `integrate`, `batch new`, ...). `ship`, `undo`, `clean`, `env` and `setup-hooks` are in `ask`, so Claude Code always prompts before anything is pushed, deleted or run from configuration. `setup-hooks` replaces an older broad `Bash(ms-workspace:*)` rule.
- **The guard** (`ms-workspace guard`, a PreToolUse hook) blocks `git push`, `gh pr create|merge`, `gh api` writes, `ms-workspace ship|undo|clean|setup-hooks` and `env --setup` **inside batch worktrees**, including option variants, `bash -c`, `eval`, wrappers and `cd` into a batch from elsewhere. It fails closed: inside `.batches/` it decides from the command text alone, so a broken `workspace.toml` cannot open the gate. It stops mistakes and realistic variants, not a determined adversary. Blocked attempts are logged.
- **Plan usage.** Claude Code exposes the 5h session and weekly usage only to the status line, so `ms-statusline` stores a snapshot and `ms-workspace usage` reads it: percent used and left, time to reset, pace, projection and a verdict. `usage --check` exits 0 ok, 1 warn, 2 critical, 3 no data, so skills and agents confirm with you before starting; `--need <pct|auto>` checks that a planned task fits (`auto` uses the median of past completed batches, at least 3). Thresholds come from `[usage]` in `workspace.toml` (default 70/90). Projections only influence the verdict above 50 % used. Pro/Max plans only; data appears after the first reply of a session.
- **Token-saving hooks.** `readguard` (PreToolUse on Read) tells Claude when it is about to re-read an unchanged file that is already in its context (files under 4 000 characters are ignored; a compaction or `/clear` resets the memory, because re-reading is legitimate then). `outguard` (PostToolUse on Bash) replaces a Bash output longer than 30 000 characters with its first and last 60 lines, saves the full text to a file it names, and keeps `stderr` and the output shape. Tune it with `[context] bash_output_max_chars`, `MS_OUTGUARD_MAX_CHARS`, or turn it off with `MS_OUTGUARD=off`. Neither hook can fail a session.
- **Memory.** The log says what happened; `ms-workspace memory` keeps what was learned: one markdown note per fact (`decision`, `lesson`, `gotcha`, `handoff`) with `add`, `list`, `search`, `show`, `forget`. If an agent must stop early it leaves a handoff for the next session; `context` shows only a count and the latest handoff of each active batch, so it costs a few tokens. Handoffs disappear with their batch.

## Observability

- **`context`** (SessionStart hook) injects a short briefing: active batches, open tasks, plan usage, memory and handoffs, last actions. It prints nothing outside a workspace.
- **`log [-n N] [--day D] [--action A]`**: one JSON line per action in `<workspace>/.ms-workspace/logs/`, one file per day, pruned after `log_retention_days` (default 14). Test events carry duration, a code hash and the plan usage at that moment.
- **`budget [--top N] [--json]`**: what every session loads before you type anything, in tokens (estimate: characters / 4, an upper bound): global and workspace `CLAUDE.md` plus their imports, unscoped rules, the name and description of every skill and agent, Claude's auto-memory index and what `context` injects, with hints for the biggest items. Path-scoped rules are listed as on-demand, and MCP servers are counted but their tool schemas are not measurable from files.
- **`insights [--days N]`**: slow runs, flaky candidates (same code, both pass and fail), time per batch and an approximate plan cost per batch (usage jumps between a batch's events, so parallel work elsewhere is counted too).
- **`tokens [--days N]`**: reads Claude Code's local transcripts for sessions run inside the workspace and reports requests, new input, cache reads and output per batch or repo, the tools whose results were largest (characters divided by 4), repeated reads of one file, and hints. Everything stays local.
- **Pasted images.** Claude Code keeps chat images only as base64 inside the session transcript. `images capture` (Stop and SessionEnd hook) saves the new ones to `<workspace>/.ms-workspace/images/YYYY-MM-DD/HHMMSS_<session>_<n>.<ext>` with an `index.jsonl` (time, session, directory, the text sent with the image). Duplicates are skipped by hash, files older than `images_retention_days` (default 30) are pruned, `images [list]` shows recent ones and `images backfill` imports past sessions. They may contain sensitive data: they stay local, outside any repo.
- **`status [--fetch]`** (one line per repo), **`doctor`** (tools, versions, workspace, hooks, usage snapshot, resources), **`affected`** (changed modules and dependent repos).

## The workspace

A workspace is a folder with several repos plus a `workspace.toml` (see `skills/ms-workspace-init/references/workspace.example.toml` for every key). The folder that holds the file is the workspace root; batches live in `.batches/` and state in `.ms-workspace/`, both outside every repo.

```toml
name = "shop"
tasks = "local"                     # or "github"; a repo can override it
[repos.framework]
base = "next"
[repos.framework.test]
unit = "mvn -T1C -B test"
affected = "mvn -T1C -B test -pl {modules} -amd"
[repos.erp]
base = "next"
deps = ["framework"]
critical = ["sources/modulos/modulo-pagos"]   # always tested in t1
[e2e]
command = "docker compose -f e2e/docker-compose.yml up --abort-on-container-exit"
repo = "erp"
```

`ms-workspace claude-md` generates `<workspace>/CLAUDE.md` (repos in dependency order, agent rules, the flow, token and tool guidance, taken from `[tools]`). Only the block between the `ms-workspace:begin/end` markers is managed, so your notes around it survive every regeneration.

## Hooks

`/ms-setup` (or `ms-workspace setup-hooks [--dry-run] [--remove] [--project]`) merges `settings/hooks.example.json`: idempotent, keeps every other hook, permission and setting, keeps a status line someone else configured, writes a timestamped backup. It adds `guard` and `readguard` (PreToolUse on Bash and Read), `outguard` (PostToolUse on Bash), `images capture` (Stop, SessionEnd), `context` (SessionStart), `readguard --reset` (SessionStart after `/clear` or a compaction), `ms-statusline` and the permission rules above. `install.sh` never edits your `settings.json` by itself.

## Development

- Everything in the repo is in English; names use the `ms-` prefix; no secrets or machine-specific paths.
- `ms-workspace` stays standard-library only. The CLI is the contract: `tests/` drives the real tool (bare remotes, worktrees, conflicts, hooks, usage snapshots, images, installer, skill frontmatter).

```bash
python3 -m unittest discover -s tests            # about 45 s; throwaway repos and a private HOME
python3 -m unittest tests.test_ms_workspace.TestShip -v
```

`MS_WORKSPACE_BIN` runs the suite against another build of the tool.

**Add a skill**: create `skills/<name>/SKILL.md` with `name` and `description` frontmatter (avoid an unquoted `: ` in values, the suite checks it), write clear trigger conditions in `description`, run `./install.sh`, test it in a session, commit. Agents are one file each in `agents/` and must be named `ms-agent-*`.

## Roadmap

- [ ] First end-to-end run on real repos (Maven, pnpm, Gradle) and a live check of the image hook
- [ ] Exact integration plan across agents (merge-tree chain) instead of per-branch `--dry-run`
- [ ] Secret and large-file gate before `ship`
- [ ] Maven module graph from `pom.xml` and JUnit/Surefire report summaries
- [ ] `clean` recognising squash-merged PRs in `pr` mode
- [ ] Import the remaining personal skills and agents from `~/.claude`
