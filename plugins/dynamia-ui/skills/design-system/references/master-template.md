# MASTER.md format

Keep it short. Tables, not prose. Every value is either a token name or a raw value with a count.

```markdown
# Design system: <project>
Source: extracted | created | improved on <date>. Stack: <framework, styling>.

## Color
| Token | Value | Role | Uses |
|---|---|---|---|
| --color-primary | #2563eb | primary action, links | 41 |
Semantic roles: background, surface, text, text-muted, border, primary, success, warning, danger, focus.
Dark mode: <how it is switched, and the values that change>.

## Typography
| Token | Family / size / weight / line-height | Use |
Scale: <sizes in use>. Base: 16px.

## Spacing
Grid: 4 or 8 px. Scale: 4, 8, 12, 16, 24, 32, 48. Off-scale values still in code: <list with counts>.

## Shape and depth
Radius: <scale>. Shadows: <scale>. Borders: <widths and colors>.

## Components
| Component | Variants | States covered | Where |
Button: primary, secondary, ghost. States: hover, focus, active, disabled, loading.

## Motion
Durations and easing in use. Reduced-motion handled: yes/no.

## Drift and gaps (extract and improve)
- Raw colors outside tokens: <n>. Near-duplicates: <pairs>. Unused tokens: <names>.
- Missing states, missing dark values, contrast failures.

## Decisions
Dated one-liners: what was chosen and why. Never delete a prior decision without saying so.
```
