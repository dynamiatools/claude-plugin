---
name: design-system
description: Extracts the design system a project really uses, improves it, or creates one for a new project, all in one design-system/MASTER.md. Use when the user asks for the design system, tokens, palette, typography or spacing of a UI, wants to clean up inconsistent styles, or starts a UI from scratch.
argument-hint: "[extract|improve|create] [path]"
---

# dynamia-ui:design-system

One file, `design-system/MASTER.md`, is the source of truth. Three modes read and write it in the same format (`references/master-template.md`).

## Pick the mode
- The user named one: use it.
- The project has UI code and no `MASTER.md`: **extract**.
- `MASTER.md` exists, or the user wants it cleaner or more consistent: **improve**.
- No UI yet, or the user wants a new look: **create**.

Always read an existing `MASTER.md` first. Never overwrite it silently: show a diff of what changes and why.

## Modes
| Mode | Read | Result |
|---|---|---|
| extract | `references/extract.md` | `MASTER.md` that describes what the code does today, with counts and drift |
| improve | `references/improve.md` | prioritized list of changes and an updated `MASTER.md`; code only after approval |
| create | `references/create.md` | a new `MASTER.md` from a few answers |

## Rules
- Measure, do not guess: for extract and improve run `${CLAUDE_PLUGIN_ROOT}/bin/ds-scan <path>` (Python 3, read-only). If it is not available, grep for the same things and say the numbers are approximate.
- Page overrides go in `design-system/pages/<page>.md`; they only list what differs from Master.
- Changing code is a separate step the user approves. Small steps, one token family at a time, and re-run `ds-scan` to prove the drift went down.
- Contrast and dark mode are checked on the semantic tokens, not on single screens.

End with one line: what was measured, what was assumed, and what was not checked.
