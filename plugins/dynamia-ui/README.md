# dynamia-ui

UI and UX skills for Claude Code: describe, improve or create a design system, review UX (desktop and mobile), SEO, offline support and performance, and evaluate the frontend stack. No hooks. Review skills are read-only; changes happen only after you approve them.
UX rules adapted from [ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) (MIT), see `NOTICE`.

| Skill | Use it to |
|---|---|
| `design-system` | Extract the design system a project uses, improve it, or create one, in `design-system/MASTER.md` |
| `ux-review` | Review and fix usability and accessibility; web apps on phones follow mobile app conventions |
| `seo-review` | Crawling, indexing, metadata, structured data, SPA rendering risk |
| `offline-review` | Service worker, caching, PWA manifest, local data and sync |
| `perf-review` | Core Web Vitals, bundle, images, fonts, rendering cost |
| `charts-forms` | Chart choice and accessibility; form structure and validation |
| `landing` | Landing page structure by product type |
| `stack-review` | Map the frontend stack and recommend for web, hybrid or native mobile, desktop |

Agent: `ui-reviewer`, a read-only reviewer for a UI diff.

Script: `bin/ds-scan [path] [--json]` counts the colors, fonts, spacing, radii and shadows a project really uses (Python 3, standard library, read-only). Used by `design-system`.

Install:

```
/plugin marketplace add dynamiatools/claude-plugins
/plugin install dynamia-ui@dynamia-tools
```

Tests: `python3 -m unittest discover -s tests`
