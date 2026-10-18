---
name: ms-powers-installers
description: Installs, checks and removes helper tools for coding agents (uv, rtk, codebase-memory-mcp, graphify, headroom) with one script. Shows the plan first and runs only after the user approves. Use when the user asks to install, set up, update the state of, or remove one of these tools, or what agent tools are available.
argument-hint: "[list | doctor | install <tool>... | remove <tool>...]"
---

# ms-powers-installers

```bash
S=~/.claude/skills/ms-powers-installers/scripts/powers.sh
bash $S list                         # catalog and what is installed
bash $S doctor                       # version of each installed tool
bash $S install <tool>...            # plan only
bash $S install <tool>... --yes      # run it
bash $S remove  <tool>... [--yes]
```

Tools: `uv`, `rtk`, `codebase-memory`, `graphify`, `headroom`. `graphify` and `headroom` need `uv` first.

## Steps
1. For a status question run `list` or `doctor` and answer from it.
2. To install or remove, run the command **without** `--yes` and show the plan. Say which tools are downloaded from the internet and that each installer's sha256 is printed before it runs.
3. Ask the user to approve (`AskUserQuestion`). Only then re-run with `--yes`. Approval for one tool does not cover another.
4. Repeat the `next` lines the script prints (for example `rtk init -g`, restart Claude Code); those edit settings and are not run for you.
5. Finish with `doctor` and quote its line for the tool.

## Notes
- Installers change `~/.local/bin` and, for some tools, Claude Code's settings or MCP config. Never run with `--yes` on your own initiative.
- `rtk` and `uv` document no uninstall command: `remove` prints manual steps instead of guessing.
- headroom sends an anonymous beacon by default; mention `HEADROOM_TELEMETRY=off`.
- To add a tool, extend the catalog functions at the top of `scripts/powers.sh` and the test.
