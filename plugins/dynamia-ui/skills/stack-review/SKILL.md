---
name: stack-review
description: Maps a project's frontend stack and recommends what to use or keep, depending on the target - web, PWA, hybrid mobile, native mobile or desktop. Use when the user starts a new frontend, asks which framework or stack to choose, wants to evaluate or modernize an existing one, or asks how to ship a web app as a mobile or desktop app.
argument-hint: "[path] [map|recommend]"
---

# dynamia-ui:stack-review

Read-only. Map first, recommend second. Opinions per target are in `references/`; read only the one that applies.

## 1. Map what exists
Read `package.json`, lockfile name, `vite.config`/`nuxt.config`/`next.config`, `tailwind.config`, `capacitor.config.*`, `src-tauri/`, `electron` entries, `pubspec.yaml`, `Package.swift`, `build.gradle`, `index.html`. Output a table: framework, language, build tool, styling, component library, state, routing, tests, and **delivery target** (web, PWA, hybrid, native, desktop). Flag dependencies that are deprecated, far behind their major version, or heavy (check `npm outdated` only if the user allows running it).

## 2. Ask only what is missing
Target platforms, who builds and maintains it (team skills), offline and native device needs (camera, push, files, Bluetooth), SEO needs, expected lifetime, performance bar. One short message.

## 3. Recommend
One main choice and one alternative, each with a reason in one line, then cost of getting there.
- **New project, nothing decided**: Vue 3 + Vite + Tailwind. Nuxt when SEO or SSR matters.
- **Existing stack**: judge fit to the target; do not push a rewrite. Say what to keep, what to fix, and what a migration would cost (effort S/M/L and risk).
- Target tables: `references/web.md` (web, PWA, SEO), `references/mobile.md` (hybrid and native), `references/desktop.md`.

## 4. Report
Stack map, fit to target, risks (unsupported versions, abandoned packages, bundle weight, single points of failure), recommendation, next step. Hand off: `dynamia-ui:design-system` for styling, `dynamia-ui:ux-review` for mobile, `dynamia-ui:seo-review`, `dynamia-ui:offline-review`, `dynamia-ui:perf-review`.

References were checked on 2026-10-22 and carry no version numbers on purpose. Before recommending a specific version or API, look up the official docs; frameworks change fast. End with one line: what was mapped, what was assumed, any risk left.
