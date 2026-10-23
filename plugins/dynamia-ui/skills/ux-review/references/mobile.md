# Mobile UX checklist (native apps and web apps on a phone)

A web app on a small screen should feel like a current mobile app: same conventions, same reach and touch rules. Rules adapted from ui-ux-pro-max (MIT), see NOTICE.

## Navigation
- Primary destinations: bottom tab bar with 3 to 5 items, icon plus label, current one marked. Not a hamburger for core features, not a desktop sidebar.
- Back is predictable and matches the system back gesture. Deep links open the right screen. Do not trap the user.
- Secondary actions in sheets: a bottom sheet or action sheet instead of a centered modal or a dropdown.
- Top bar: title, one or two actions. Large lists scroll under a collapsing header.

## Touch
- Targets at least 44x44 px (iOS) or 48x48 dp (Android), 8px or more between them; enlarge the hit area when the icon is smaller.
- Primary actions in the thumb zone (bottom). Destructive ones away from the main one.
- Pressed feedback within 80 to 150 ms by color, opacity or elevation; never shift layout on press.
- No hover-only behavior. Every gesture (swipe, long press, drag) has a visible alternative. Do not fight edge swipes used by the system.

## Screen and keyboard
- `viewport` with `width=device-width, initial-scale=1`; add `viewport-fit=cover` and pad fixed bars with `env(safe-area-inset-*)`. Never disable zoom.
- Use `100dvh` (or `svh`), not `100vh`, for full-height layouts.
- Open keyboard must not cover the focused field or the submit button; scroll the field into view.
- Inputs are at least 16px font size, or iOS Safari zooms on focus.
- Right keyboard: `type="email|tel|number|url"`, `inputmode`, `autocomplete`, `enterkeyhint`. One column forms. Show a password toggle.
- Prefer native pickers for date, select and file.

## Content
- Tables become cards or stacked rows; no sideways scroll for core data. Long lists are virtualized or paged.
- Pull to refresh only where it makes sense; skeletons instead of blank screens; optimistic UI for quick actions.
- Truncate with intent: show the full text on tap.
- Text scales with the system text size; test the largest.

## States and connectivity
- Loading, empty, error, offline and retry states for every screen. Say what happened and what to do.
- Offline: see `dynamia-ui:offline-review`.

## Theme
- Light and dark both checked: contrast 4.5:1 in each, borders and dividers visible in each, same state coverage in each. Use semantic tokens, not per-screen hex.

## Performance as UX
- WebP or AVIF, responsive `srcset`, lazy load below the fold, no layout shift (CLS under 0.1). See `dynamia-ui:perf-review`.

## Test matrix
375 px wide and landscape; largest text size; reduced motion on; dark mode; slow network; one real device when possible.
