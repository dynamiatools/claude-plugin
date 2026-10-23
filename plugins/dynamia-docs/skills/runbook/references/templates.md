# Templates

## Runbook
```markdown
# Runbook: <task or alert name>
Owner: <team/role> · Last verified: YYYY-MM-DD against <version/env> · Severity/use: <when to run>

## Purpose
<One or two sentences.>

## Prerequisites
- Access: <system, role>   - Tools: <cli, versions>   - Read first: <link>

## Steps
1. <Action.> `command --flag <placeholder>`
   Expected: <output or state>
2. ...

## Verify
- <Check and expected result>

## Rollback / abort
- Stop if: <condition>. To undo: <steps>.

## Escalation
<Who, how, when.>

## Links
Dashboards: ... · Logs: ... · Related ADRs: ...
```

## Postmortem
```markdown
# Postmortem: <title> (YYYY-MM-DD)
Status: draft | reviewed · Authors: <roles> · Severity: <level>
## Summary and impact
## Timeline (UTC)
| Time | Event | Source |
## Detection
## Root cause and contributing factors
## What went well / what went badly
## Action items
| Action | Owner | Due | Tracker |
## Lessons
```
