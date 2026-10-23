---
name: readme
description: Writes or refreshes a project README and its docs structure using the four Diátaxis types (tutorial, how-to, reference, explanation), with commands that were actually run. Use when creating a README, onboarding docs or a docs folder layout, when a README is out of date, or when asked how to document a project or module.
argument-hint: "[project or module]"
---

# dynamia-docs:readme

A README answers, in this order: **what it is, who it is for, how to run it, how to test it, where to learn more**. Everything else lives in `docs/`.

## Procedure
1. **Read the project**: build files, entry points, existing docs, CI config, `CLAUDE.md`/`AGENTS.md`, the last commits. Do not describe what you have not read.
2. **Find the real commands** (build, test, run, lint) from the build files and CI, and **run them** when it is safe. Write only commands that worked; mark the rest "not verified".
3. **Write the README** from `references/readme-template.md`. Keep it to what a new reader needs in five minutes; link to deeper docs.
4. **Organize `docs/` by reader need** (Diátaxis, diataxis.fr): *tutorials* (learning, a guided first success), *how-to guides* (a task for someone who knows the basics), *reference* (precise facts: config keys, API, CLI), *explanation* (why and how it works: architecture, decisions). Do not mix the four in one page; link between them.
5. **Check the result**: every path exists, every link resolves, versions match the build files, examples are consistent with the code.

## Rules
- **Short and true beats long and stale.** Delete text that nobody will maintain; point to the source of truth (code, schema, `--help`) instead of copying it.
- Show, don't tell: a runnable example before an explanation.
- One audience per document; say the prerequisites (JDK version, Node version, Docker) explicitly with the versions the build requires.
- No secrets, tokens, internal URLs or customer data in docs of public repos; use placeholders.
- Language follows the repo convention (this marketplace: English); user-facing docs follow the user's language.
- Badges only if they carry information (build status, version); no decoration walls.
- Keep install/usage in sync with releases (`dynamia-docs:changelog`); record big choices as ADRs (`dynamia-docs:adr`).

## Structure of a docs folder (adapt, do not over-build)
`docs/tutorials/`, `docs/how-to/`, `docs/reference/`, `docs/explanation/` (architecture, concepts), `docs/decisions/` (ADRs), `docs/runbooks/`. A small project needs only README + `docs/decisions/` + a couple of how-tos.

## Optional pointers
For repository instructions aimed at Claude (`CLAUDE.md`) see `dynamia-docs:audit`. For diagrams `dynamia-docs:diagrams`.

End with one line: what was written, which commands were run, what is unverified.
