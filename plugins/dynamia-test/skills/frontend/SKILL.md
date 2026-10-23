---
name: frontend
description: Writes and fixes frontend tests for Vue and TypeScript apps - Vitest unit and component tests, Vue Test Utils or Testing Library, mocking APIs, Playwright end-to-end, visual and accessibility checks, and stable selectors. Use when writing, running or debugging tests for a web UI, setting up Vitest or Playwright, or deciding what to test in the browser.
argument-hint: "[component or flow]"
---

# dynamia-test:frontend

Versions read on 2026-10-23: **Vitest 5** needs Vite 6.4 or later and Node 22.12 or later and reuses `vite.config`; **Playwright** supports Node 22, 24 and 26, runs Chromium, WebKit and Firefox, and ships locators, web-first assertions, UI Mode, Trace Viewer, codegen, visual comparisons and an HTML reporter. Follow the versions in the project's `package.json`.

## Layers
| What | Tool | Notes |
|---|---|---|
| Pure logic, composables, stores, converters | Vitest (`*.test.ts`) | no DOM when possible; test dates and money formatting with fixed locale and time zone |
| A component's behavior | Vitest + Vue Test Utils or Testing Library for Vue; or Vitest browser mode for real-browser component tests | render, interact like a user, assert on visible output and emitted events |
| API client / SDK | Vitest with a mocked `fetch` or a mock service layer | assert request shape (method, path, body, headers) and error mapping |
| A user journey | Playwright | few, on critical paths: login, create-edit-delete a record, checkout, permission denial |
| Visual regression | Playwright visual comparisons or Vitest browser mode | only stable, deterministic screens; fixed viewport, fonts, data, animations off |
| Accessibility | axe checks in Playwright/component tests + keyboard-only flows | complements manual review (`dynamia-ui:ux-review` if installed) |

## Rules
- **Query like a user**: roles, labels and visible text first (`getByRole`, `getByLabel`, `getByText`), `data-testid` only when nothing semantic exists. Never CSS classes or DOM structure.
- **Assert on outcomes**: what the user sees (text, enabled state, URL), not component internals, refs or `wrapper.vm`.
- **No sleeps**: rely on auto-waiting and web-first assertions (`await expect(locator).toBeVisible()`), `await nextTick`/`flushPromises` in unit tests, explicit waits on network or state.
- **Control the network**: in unit/component tests mock `fetch`/the client module; in Playwright either run against a seeded test backend or intercept routes for external services; never hit production or third parties.
- **Own your data**: each e2e test creates its records (API or fixture), uses unique names, cleans up or runs on a disposable database; tests must pass in any order and in parallel.
- **Auth**: log in once through the API and reuse the stored state (Playwright `storageState`) instead of the UI in every test; test the login UI separately.
- **Dates and locale**: fix the clock (`vi.useFakeTimers`, `page.clock`), time zone and locale; date-only values must show the same calendar day.
- **Snapshots** only for small, intentional structures; review diffs, never bulk-update blindly.
- **Flakes**: reproduce with `--repeat-each`, read the trace, fix the cause (race, shared data, animation); retries are a diagnostic aid in CI, not a fix.

## Running
- Vitest: `npx vitest run` (one pass), `npx vitest run path/to/file.test.ts -t "name"`, `--coverage` for a report, `--reporter=verbose`.
- Playwright: `npx playwright test`, `--project=chromium`, `--headed`, `--ui`, a file path, `--trace on`, `--repeat-each=N`, `--retries=N` (CI), `npx playwright show-report`; install browsers with `npx playwright install --with-deps` in CI images.
- Typecheck the tests too (`vue-tsc --noEmit`); keep test files out of the production bundle.

## Dynamia Vue apps
Test screens that render server-driven views (`DynamiaViewer`, `DynamiaCrudPage`) with a mocked `DynamiaClient` that returns a view descriptor and rows; assert on rendered fields and actions rather than internals. See `/dynamia-platform:vue-frontend` if that plugin is installed.

## Checklist
- [ ] Selectors are semantic; no sleeps; each test independent and parallel-safe.
- [ ] Network and time controlled; no real third parties.
- [ ] Failures leave useful output (trace/screenshot/video on first retry in CI).
- [ ] Coverage is a signal, not the goal (`dynamia-test:quality`).

End with one line: commands run and result, browsers/projects covered, what was not run.
