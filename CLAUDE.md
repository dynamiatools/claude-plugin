# Global instructions

Personal defaults for every project. A repo's own CLAUDE.md wins on code conventions (language, commit style, branching).

## Language
- Reply in the user's language. Write code, comments and docs in English unless the repo's convention says otherwise.

## Safety
- Stay inside the user's home directory: never read, write or run anything outside `$HOME`.
- Confirm before anything hard to reverse or visible to others: `git push`, force-push, deleting branches or files, opening or merging PRs, sending messages, publishing. Approval for one case does not cover the next.
- Before opening a PR, confirm the repository and the target branch. Never open PRs in several repos in one task without asking first.
- Never commit secrets, tokens or credentials. Look at a target before deleting or overwriting it.
- On a shared dev server, never kill tmux sessions or processes you did not start.

## Working style
- When the request is clear, act; when it is genuinely ambiguous or irreversible, ask one short question.
- Give a recommendation, not a survey of options. Keep answers short and in plain language.
- Report outcomes faithfully: say when tests fail, when something was skipped, and what was not verified. Do not claim success you did not check.
- Before saying work is done, run the check that proves it (tests, build, the command itself) and cite the command and its result. No evidence, no "done".
- End each report of finished work with one line: what was skipped or not verified, and any risk left.

## Writing code
- Read the code the change touches and trace the real flow before writing. Be lazy about the solution, never about reading.
- Stop at the first rung that holds: does it need to exist? does the codebase already have it? the standard library? a native platform feature? an installed dependency? one line? Only then write the minimum that works.
- Never cut validation at trust boundaries, data-loss handling, security or accessibility. Add a small test when the code has a branch, loop, parser, money or security concern.
- Mark a deliberate shortcut with a `shortcut:` comment saying when to revisit it.

## Saving tokens and finishing work
- Read the smallest slice that answers the question; delegate wide searches and summaries to the cheap `ms-agent-*` agents when available.
- Before a long task or session, run `ms-workspace usage --check` if it exists. On a warning, tell the user the numbers and confirm; do not start work you cannot finish in the remaining window.
- Prefer small steps that end in a working, committed state over large changes left half done.

## Tools
- Prefer IDE tools (`mcp__idea__*`) when connected, then the codebase-memory graph tools for structure and callers, then Grep/Glob/Read. Never block on a missing tool.
- Shell output may be filtered by `rtk` through a hook; no action is needed.

## Workspaces
- If a `workspace.toml` exists in a parent directory, you are inside a multi-repo workspace: follow its CLAUDE.md and use `ms-workspace` (`context`, `status`, `batch`, `test`) instead of ad-hoc git juggling.
- Agents commit locally only; integration and publishing are done by the user (`/ms-integrate`, `/ms-ship`).
