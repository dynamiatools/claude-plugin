# Offline and PWA checklist

Installability facts from MDN (Making PWAs installable), checked 2026-10-22. Recheck before quoting browser support.

## Installable
- Served over HTTPS (localhost is fine in development).
- Manifest linked from every page with `name` or `short_name`, `icons` (a 192 px and a 512 px, plus a maskable one), `start_url`, `display` or `display_override`, and `prefer_related_applications` false or absent. Add `theme_color`, `background_color`, `scope`.
- A service worker is **not** required to be installable in Chromium; it is required for offline behavior.
- Support differs: Firefox desktop does not install PWAs; iOS installs from the Share menu (16.4 and later in browsers other than Safari); `beforeinstallprompt` does not exist on iOS, so give iOS users instructions.

## Service worker
- Registered after load, from the site root or with a scope that covers the app; served with a no-cache header so updates are found.
- Lifecycle handled: `install` precaches the app shell, `activate` deletes old caches, and the page gets told when a new version is waiting.
- `skipWaiting` and `clients.claim` are used knowingly: forcing the new worker onto open pages can break them mid-session. Prefer "update available, reload" and keep the old worker until the user agrees.
- Never cache the service worker file itself.

## Caching strategy by resource
| Resource | Strategy |
|---|---|
| Hashed JS, CSS, fonts, images | cache-first, long life |
| App shell HTML | network-first with offline fallback, or precache and update |
| API reads | network-first with timeout, or stale-while-revalidate where stale is acceptable |
| API writes | never cached; queue them (below) |
| Third-party | cache only what you control; opaque responses count heavily against quota |
- Caches are versioned and bounded (max entries, max age); old ones removed.
- Do not cache authenticated responses in a shared cache without keying by user, and clear caches on logout. Do not cache error responses or `Set-Cookie` responses. Check `Cache-Control: private/no-store` is respected.
- Navigation requests have an offline fallback page that is useful, not a browser dinosaur.

## Data and sync
- Local data in IndexedDB (not localStorage for large or structured data), with a schema version and migration. Ask for persistent storage if the data matters (`navigator.storage.persist()`); expect eviction otherwise, especially on iOS.
- Writes made offline go into an outbox with an id, are retried with backoff, and are idempotent on the server (idempotency key). Background Sync is an enhancement, not a dependency: it is not available in every browser, so also sync on `online` and on app start.
- Conflicts: decide the rule (last write wins, merge, ask the user) and show it.
- Sensitive data stored locally is minimal and cleared on logout.

## Experience
- The UI shows connection state, queued changes ("3 changes waiting to sync") and sync errors, without blocking reading.
- Every screen has loading, empty, error and offline states with a retry. Buttons that need the network say so when offline.
- Update flow: a visible "new version available, reload" that does not lose unsaved input.
- Handle slow networks ("lie-fi") with timeouts, not only the offline event: `navigator.onLine` can be true with no connection.

## Test by hand
DevTools Application panel (service worker, cache storage, manifest), Network "Offline" and throttling, "Update on reload" off, Lighthouse PWA/installability checks, a real phone in airplane mode, then ship a second version and confirm the update.
