---
name: audit
description: Audits documentation against the code - finds stale commands, wrong paths, versions and config keys, broken links and missing docs after a change - and keeps agent instruction files (CLAUDE.md, AGENTS.md) short and accurate. Use when docs may be outdated, after a code or build change, before a release, when reviewing documentation, or when a CLAUDE.md has grown unwieldy.
argument-hint: "[docs folder or change]"
---

# dynamia-docs:audit

Docs are claims about the system. An audit **checks the claims against reality**.

## Procedure
1. **Inventory** the docs in scope (README, `docs/`, CHANGELOG, ADRs, runbooks, API specs, doc comments, CLAUDE.md/AGENTS.md).
2. **Extract the checkable claims**: commands, file paths, class/function names, config keys and defaults, ports, URLs, versions and prerequisites, environment variables, endpoints and payloads, diagrams' components, screenshots.
3. **Verify each** against the repo: path exists (`ls`/glob), symbol exists (grep/graph), command works (run it when safe, otherwise mark unverified), version matches the build file, default matches the code, endpoint exists in the controller/OpenAPI, link resolves. Prefer the source of truth (code, schema, `--help`).
4. **After a change**: from the diff, list what docs it touches (renamed config, removed flag, changed behavior, new dependency, moved module) and update them in the same change; check the CHANGELOG, the README quick start, runbooks, ADR status and API docs.
5. **Report** by severity: **Wrong** (would mislead or break a reader), **Stale/Missing** (true once, or needed and absent), **Style** (clarity, structure, tone). One line each: `path:line`, the claim, the evidence, the fix. Then "Not verified".
6. **Fix** (when asked) in small edits; keep the doc's voice; delete rather than patch text nobody will maintain.

## What good docs look like (quick test)
Right audience and a stated prerequisite; first success in minutes; commands copy-paste correctly; one fact lives in one place (others link to it); dates/versions where they matter; no secrets; consistent terms; links work; examples run. Structure by reader need (tutorial, how-to, reference, explanation: `dynamia-docs:readme`).

## Agent instruction files (CLAUDE.md, AGENTS.md)
These tell a coding agent how to work in the repo. Keep them **short, concrete and current**:
- Include: what the project is (two lines), how to build/test/run (verified commands), the conventions that are not obvious from the code (branching, commit style, language, versioning, scripts allowed), hard rules (what never to do, what needs confirmation), where deeper docs live.
- Exclude: what the code and build files already say, long tutorials, anything that changes weekly, secrets.
- Make rules **actionable and checkable** ("run X before committing"), say why for the non-obvious ones, and delete rules that are no longer true.
- Layer them: a global file for personal defaults, a repo file for the project, nested files for subprojects when they differ; avoid duplicating text across layers.
- Review them like code: when a command or convention changes, change the file in the same PR.

## Link and style checks
Use a link checker in CI for external and relative links, a Markdown linter for structure, and a spell/term list for product names. Language follows the repo convention; user-facing text follows the user's language.

## Optional pointers
For diagrams `dynamia-docs:diagrams`; for changelogs `dynamia-docs:changelog`. In Dynamia Platform projects, the framework's own docs are read live by `/dynamia-platform:docs` if that plugin is installed.

End with one line: claims checked vs unverifiable, what was fixed, what remains.
