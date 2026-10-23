# Create

Goal: a small, coherent system for a new UI, from few answers.

## Ask (one short message, all at once)
Product type and audience, tone (for example calm, playful, serious, technical), brand colors or logo if any, platforms (web, mobile web, app), stack, dark mode yes or no. If the user gives a reference site or screenshot, use it.

## Decide
- **Stack default**: Vue + Tailwind unless the project says otherwise. Tokens go in CSS custom properties, exposed to Tailwind as theme colors, so both stay in sync.
- **Color**: one primary, one neutral ramp, and success, warning, danger. Derive 50 to 900 ramps; map them to semantic roles. Check contrast of every text/background pair (4.5:1) and of UI boundaries (3:1), in dark too.
- **Type**: at most two families (system stack is a fine choice). Base 16px, ratio-based scale (for example 1.25), line-height 1.5 for body. Check the font license if it is not a system font.
- **Spacing**: 4px grid, scale 4, 8, 12, 16, 24, 32, 48, 64.
- **Shape and depth**: 2 or 3 radii, 2 or 3 shadows, one border style.
- **Components**: button, input, select, checkbox, card, modal, table, nav with all states, including focus, disabled, loading, error and empty.
- **Motion**: 2 or 3 durations (for example 120, 200, 300 ms), one easing, honor `prefers-reduced-motion`.
- **Mobile**: touch targets of 44px or more, safe areas, body text 16px.

## Write
`design-system/MASTER.md` from `master-template.md`, plus the token file in the project's own format (CSS variables or Tailwind config) if the user asks for it. Show the palette and type scale as a short table, then wait for feedback before writing code that uses it.
