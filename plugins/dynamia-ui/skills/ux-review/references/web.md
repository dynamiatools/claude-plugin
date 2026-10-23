# Web UX checklist

Priority order. Rules adapted from ui-ux-pro-max (MIT), see NOTICE.

## 1. Accessibility (Critical)
- Text contrast 4.5:1 (3:1 for large text); icons, input borders and focus rings 3:1.
- Never remove the focus outline without a visible replacement. Keep focus not hidden behind sticky headers.
- Everything works with the keyboard, in a logical order; no keyboard traps; modals trap focus and return it on close.
- Use native elements (`button`, `a`, `input`, `label`) before ARIA. Icon-only buttons have an accessible name. Images have `alt` (empty for decoration).
- Information is never only color. Respect `prefers-reduced-motion`. Pages have `lang` and one `h1`.
- Form errors name the field and the fix, are linked to the field, and are announced.

## 2. Interaction (Critical)
- Every action gives feedback: pressed, loading, success, error. No silent failures. No double-submit.
- Hit areas at least 24px (WCAG 2.2 AA minimum), 44px preferred.
- Destructive actions confirm or can be undone. Disabled controls look and behave disabled.
- Do not depend on hover for anything needed.

## 3. Layout and responsive (High)
- Mobile-first breakpoints, viewport meta set, no horizontal scroll, no fixed-px page widths.
- Long text, long names, badges and chips wrap or truncate without breaking layout; translations can be 30% longer.
- Readable line length (about 45 to 80 characters). Body text 16px, line-height about 1.5.
- Reserve space for images and async content (no layout shift).

## 4. Style and consistency (High)
- One icon family and style; SVG, not emoji, for structure.
- Colors, spacing, radius and type come from tokens. No raw hex in components.
- Same component, same look and behavior everywhere.

## 5. Forms (Medium)
- Visible label for every field (placeholder is not a label). Helper text before the error. Error next to the field.
- Right input `type`, `autocomplete`, `inputmode`. Mark optional rather than required fields when most are required. Ask only what is needed.
- Preserve input on error. Disable submit only while sending, with feedback.

## 6. Navigation and states (High)
- Current location is visible. Back works as expected; URLs reflect state and can be shared.
- Every list, table and screen has loading, empty, error and success states.
- Feedback in the page, not only toasts that vanish.

## 7. Motion (Medium)
- Motion explains a change (enter, leave, move). 150 to 300 ms for small, up to 500 for large. Animate transform and opacity, not width or height.
- Different durations for different distances; interruptible; off with reduced motion.

## 8. Data display (Low)
- Charts: legend, labels, tooltip, color-blind safe palette, a table alternative. See `dynamia-ui:charts-forms`.
