# Navigation scope, application metadata and the REST surface

Checked against framework 26.10 (`NavigationManagerSession`, `ApplicationMetadataController`, `docs/backend/ARCHITECTURE.md` sections "REST API surface" and "Caching the metadata endpoints").

## NavigationManagerSession is a ScopedValue
It used to be a session bean (and before that a `ThreadLocal`). It now holds a navigation **intent** (`setPage(Page, params)`, `runLater(Callback)`) for the ZK desktop that is about to be built, backed by `ScopedValue<NavigationManagerSession> SCOPE`.
- A request-lifecycle filter (`NavigationManagerSessionScopeFilter`) binds a fresh instance for the whole request. Several ZK desktops (iframes, browser tabs) can bootstrap concurrently in one HTTP session without trampling each other, and nothing leaks into another request that reuses the platform thread (virtual threads included).
- `NavigationManagerSession.getInstance()` **throws `NoSuchElementException` outside the scope**: that is intended for code that *records* an intent (failing fast beats losing state). Code that only *consumes* one (a desktop bootstrap, ZK server push, `Executions.activate` from another thread, async/error dispatches) uses `current()`, which returns `null`.
- A redirect starts a new request. The filter **parks** a still-pending intent in the HTTP session and restores it lazily into the next request's instance, only when a desktop actually consumes it (static resources, `/zkau`, `/api` cannot take it). Parked state expires after `DEFAULT_PARKED_STATE_TTL` (2 minutes).
- In a test, bind one yourself: `ScopedValue.where(NavigationManagerSession.SCOPE, new NavigationManagerSession()).run(() -> ...)`.
- In a job or any thread you start, the binding does not exist (a `ScopedValue` is not inherited by plain threads). Do not call `getInstance()` there. For UI navigation from an action use the `UINavigation` facade, which works in ZK and headless.
- The same pattern is used elsewhere: `UIMessages.withDisplayer(...)` binds a displayer per execution. Prefer `ScopedValue` over `ThreadLocal` for per-request state in new code.

## Application metadata (`/apps/api/metadata`)
`ApplicationMetadataLoader` builds the metadata that API and UI clients consume from `ApplicationInfo` and the `ViewDescriptorFactory`; `ApplicationMetadataController` serves it.

| Endpoint | Returns |
|---|---|
| `GET /apps/api/metadata` | application metadata |
| `GET .../navigation` | the navigation tree (modules, groups, pages) |
| `GET .../actions`, `POST .../actions/{action}` | global actions, run one |
| `GET .../entities`, `.../entities/{id}` | entities and one entity's metadata (includes the headless actions it publishes) |
| `GET .../entities/by-path` | entity for a navigation path |
| `GET .../entities/{id}/views[/{view}]`, `GET .../views/{id}` | view descriptors |
| `POST .../entities/{id}/action/{action}` | run an entity action (headless flow, see `headless-actions.md`) |
| `GET .../entities/ref/{alias}/{id}`, `.../ref/{alias}/search` | entity references for pickers |

Rules
- **Never expose class names or classpaths.** Navigation and entity metadata use ids and aliases (a 26.09 fix removed FQCN leaks, and view descriptors no longer carry class names). Do not add them back in custom metadata or descriptors.
- The entity of an entity action comes from the URL, not from the request body.
- Descriptors are practically static but locale-dependent. Caching is **opt-in**: `dynamia.app.metadata.http-cache=etag` turns on a strong ETag from content and locale, `Cache-Control: private, no-cache`, `Vary: Accept-Language` (clients get `304`). Your own `MetadataHttpCachePolicy` bean replaces it (for example an ETag from the app version, or `Vary` by user). Only the read-only descriptor, entity and navigation endpoints take part; actions, `entities/ref/**`, dashboard and reports are never cached.
- Metadata that varies per user must not use a shared cache policy.

## `/api` versus `/apps/api`
| Prefix | Audience | Auth |
|---|---|---|
| `/api/{module}/...` | external or public integrations; generated CRUD REST `/api/{crudPath}` | stateless JWT (`Authorization: Bearer` or the `DYNAMIA_JWT` cookie) |
| `/apps/api/{module}/...` | the application's own frontends and micro-frontends: metadata, dashboard, reports designer, `crud-service/{className}`, jobs, transfers | web session by default; Bearer also accepted; the JWT cookie is **ignored** |

- Same module name under both; no version segment.
- Anything that exists to feed a Dynamia frontend goes under `/apps/api`; anything a third party calls goes under `/api`.
- `/apps/api/**` has CSRF disabled: writes (`POST`, `PUT`, `PATCH`, `DELETE`) must be same-origin (`Origin` or `Sec-Fetch-Site`), checked by `AppsApiSameOriginAuthorizationManager`; Bearer requests are exempt.
- Unauthenticated requests get a JSON `401`, not a redirect to `/login`, so `fetch` callers can handle them.
- A host app protects each prefix with its own security chain.

## Checklist when adding an endpoint
1. Who calls it: your frontend (`/apps/api`) or a third party (`/api`)?
2. Return DTOs or `BeanMap`, not entities (OSIV may be off).
3. Dates as ISO strings (`yyyy-MM-dd`, ISO date-time); see `dynamia-platform:dates`.
4. Write operations: same-origin rules apply under `/apps/api`; add authorization, not just authentication.
