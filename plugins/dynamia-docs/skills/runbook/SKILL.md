---
name: runbook
description: Writes operational documentation - runbooks, troubleshooting guides, deployment and rollback procedures, onboarding guides and blameless incident postmortems - with exact commands, verification steps and ownership. Use when documenting how to operate, deploy, recover or debug a service, after an incident, or when onboarding people to a system.
argument-hint: "[service or incident]"
---

# dynamia-docs:runbook

A runbook is read under stress by someone who did not write it. It must be **exact, short, ordered and checkable**.

## Runbook (a procedure)
Use `references/templates.md`. Required parts: **purpose and when to use it**, **owner and last verified date**, **prerequisites** (access, tools, permissions), **steps** (numbered, one action each, the exact command, the expected output), **verification** after each risky step and at the end, **rollback / abort** conditions, **escalation** (who, how), and **links** (dashboards, logs, ADRs).
- Commands are copy-pasteable with placeholders in `<angle brackets>`; destructive ones are marked and say how to confirm the target first.
- Write the **symptom → cause → fix** table for common failures; link to the alert that triggers the runbook.
- Prefer automating a step to documenting a long manual one; keep the runbook as the human fallback.
- Never include secrets: say where to get them (vault path, secret name).

## Deployment and rollback docs
Versioning scheme, how a release is cut, environments and promotion, config and secrets per environment, database migration policy (forward-only, backward-compatible steps, how to roll back safely), health checks and smoke tests after deploy, rollback command and its data implications, feature flags, who approves.

## Troubleshooting guide
Organize by **symptom** the user or alert shows, not by component. Each entry: how to confirm, likely causes in order of probability, the check for each, the fix, and when to escalate. Include where logs/metrics/traces live and the correlation id convention.

## Onboarding guide
Day-one checklist (access, tools, repo setup that actually works), the architecture in one page (`dynamia-docs:diagrams`), how to run and test locally (`dynamia-docs:readme`), the first change walkthrough, who to ask, glossary. Test it by having a new person follow it and fix every stumble.

## Incident postmortem (blameless)
Facts, not blame: summary and impact (who, how long, how much), timeline in UTC with sources, detection (how and how late), root cause(s) and contributing factors, what went well, what went badly, **action items with owner and due date**, lessons. Distinguish cause from trigger. No names in blame positions; roles instead. Published within days, reviewed, and the actions tracked to completion.

## Rules
- Date every page ("verified on YYYY-MM-DD against <version/environment>") and review on a schedule; an unverified runbook is a risk.
- Test the runbook in a non-production environment; say so (or say it is untested).
- Keep it near the code or in the team's single docs home; avoid copies.

End with one line: what was documented, what was tested, who owns it.
