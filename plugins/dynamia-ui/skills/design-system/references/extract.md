# Extract

Goal: describe the design system the code really uses, not the one it claims.

1. **Find the sources.** Run `ds-scan <project-root>`. It lists token sources (tailwind config, token JSON, theme files), stack hints and CSS custom properties. Then read only those config files, not the whole tree. For the stack this plugin does not scan natively (MUI `createTheme`, Vuetify theme, SCSS maps, ZK sclass), read the theme file once.
2. **Measure real use.** From the same scan: colors (raw vs defined), near-duplicates, font families, sizes and weights, spacing and off-scale spacing, radii, shadows, Tailwind arbitrary values.
3. **Declared vs used.** A token never used is dead. A raw value used many times and with no token is a missing token. Two colors a few units apart are one color that drifted.
4. **Components.** List the repeated UI pieces (button, input, card, modal, table, nav) with their variants. Look at 2 or 3 files per piece, not all of them. Note which states exist (hover, focus, disabled, loading, error, empty).
5. **Dark mode and responsive.** How is the theme switched (class, media query, attribute)? Which breakpoints exist?
6. **Write `design-system/MASTER.md`** from `master-template.md`. Group raw values into proposed tokens, with their counts, but mark them as proposed. Fill "Drift and gaps" honestly, including what the scan cannot see (inline JS styles, images, third-party CSS).

Do not change source code in this mode.
