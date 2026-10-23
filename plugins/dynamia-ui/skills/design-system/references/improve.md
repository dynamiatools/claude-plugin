# Improve

Goal: a more consistent system with the least change to the code. Start from `MASTER.md`; if it does not exist, extract first.

1. **Re-measure** with `ds-scan` so the list is current.
2. **Find the wins**, in this order:
   - Raw colors that already equal a token: replace with the token.
   - Near-duplicate colors: pick one, merge the others.
   - Off-scale spacing and arbitrary values: round to the scale, unless it is deliberate.
   - Raw hex in components: promote to semantic tokens (`--color-text`, not `--gray-700`, in components).
   - Too many font sizes, weights, radii or shadows: collapse to a short scale.
   - Missing states (focus, disabled, error, empty) and missing dark values.
   - Contrast: text 4.5:1, large text and UI boundaries 3:1, in light and in dark.
3. **Report** a table: change, files touched, effort (S/M/L), risk, and the metric that will move (for example "raw colors 54 to 12"). Quick and safe first.
4. **Wait for approval.** Then apply one token family at a time, run the project's tests or build, and re-run `ds-scan` to show the numbers went down.
5. **Update `MASTER.md`** and add a dated line under Decisions.

Do not redesign (new look, new palette) in this mode; that is `create`. Do not touch a value the user has told you is deliberate.
