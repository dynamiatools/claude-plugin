# MADR 4 template (minimal)

File: `docs/decisions/NNNN-title-with-dashes.md`

```markdown
---
status: "proposed"        # proposed | accepted | rejected | deprecated | superseded by ADR-NNNN
date: YYYY-MM-DD
decision-makers: <names or roles>
consulted: <optional>
informed: <optional>
---

# <Short title: the problem and the solution>

## Context and Problem Statement
<2 to 5 sentences: the situation, the forces, the question to decide.>

## Decision Drivers
* <requirement or constraint>
* <...>

## Considered Options
* <Option A>
* <Option B>
* <Do nothing> (if relevant)

## Decision Outcome
Chosen option: "<Option A>", because <justification against the drivers>.

### Consequences
* Good, because <...>
* Bad, because <...>

### Confirmation
<How we will verify compliance: a test, an architecture rule, a review step.>

## Pros and Cons of the Options
### <Option A>
* Good, because <...>
* Neutral, because <...>
* Bad, because <...>
### <Option B>
* ...

## More Information
<Links to issues, benchmarks, related ADRs, and when to revisit this decision.>
```
Only the title, context, considered options and decision outcome are essential; the rest is optional in MADR.
