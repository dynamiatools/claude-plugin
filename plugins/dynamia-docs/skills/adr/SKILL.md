---
name: adr
description: Records architecture decisions and short design docs with MADR 4 - context, options, outcome, consequences - keeps them numbered and linked, and supersedes old ones. Use when a significant technical choice is made or revisited (framework, database, API style, boundaries, security model), when asked to document why something is built the way it is, or when an old decision needs replacing.
argument-hint: "[decision]"
---

# dynamia-docs:adr

An Architecture Decision Record captures **one decision, why it was made, and what it costs**. Format: **MADR 4.0.0** (Markdown Architectural Decision Records, released 2024-09-17), stored in `docs/decisions/` as `NNNN-title-with-dashes.md` with the next sequence number.

## When to write one
A choice that is expensive to reverse or that people will ask about later: language/framework/library, data store, API style, module boundaries, security and multi-tenancy model, build/deploy approach, a deliberate exception to a standard. Not for small, easily reversed changes; those belong in the commit message or the PR.

## Procedure
1. **Gather the facts** from code, issues and the people involved; read the existing ADRs first (`docs/decisions/`) so numbering and links are right and you do not contradict a live decision.
2. **State the problem**, the **drivers** (requirements, constraints, deadlines), and **at least two real options** including "do nothing" when it is one.
3. **Decide and justify**: the chosen option and why it wins against the drivers; list **consequences** (good and bad) and how compliance will be **confirmed** (a test, an architecture rule, a review checklist).
4. **Fill the template** (`references/madr-template.md`). Status in front matter: `proposed`, `accepted`, `rejected`, `deprecated` or `superseded by ADR-NNNN`.
5. **Link**: reference the ADR from the code/README where it matters; when a decision changes, write a **new** ADR that supersedes the old one and update the old one's status; never rewrite history.
6. **Review** with the team before marking `accepted`; date it.

## Rules
- One decision per ADR; short (one page); plain language; the options section is honest about the downsides of the winner.
- Record the **context at the time** (what was known), not hindsight.
- Don't invent facts, benchmarks or approvals: mark unknowns "to confirm".
- Keep ADRs in the repository next to the code; large projects may group by category with local numbering.

## Design docs (when an ADR is too small)
For a feature spanning modules, write a short design doc: goal and non-goals, current state, proposal, alternatives, data/API changes, migration and rollback, risks, test plan, open questions. Link the resulting ADRs.

## Optional pointers
If `dynamia-craft` is installed, its `plans` skill turns an agreed design into implementation steps (`/dynamia-craft:plans`); its `brainstorming` skill helps clarify the problem first. Otherwise suggest `/plugin install dynamia-craft@dynamia-tools` once.

End with one line: the ADR file path, its status, and what remains to confirm.
