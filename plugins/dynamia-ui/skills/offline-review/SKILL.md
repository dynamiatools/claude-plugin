---
name: offline-review
description: Reviews how a web app behaves offline and on bad networks, covering service worker, caching strategy, installable PWA manifest, local data, sync and updates, then fixes it with approval. Use when the user asks about offline support, PWA, service workers, caching, or flaky connectivity.
argument-hint: "[path] [review|fix]"
---

# dynamia-ui:offline-review

**Review** is read-only; **fix** changes code only after approval. Rules and facts are in `references/checklist.md`.

## Review
1. **Decide what offline should mean** for this app before judging it: nothing (online-only is a valid choice), read cached content, or full work offline with sync. Ask one short question if it is not clear; a data-entry app needs more than a content site.
2. **Find the pieces**: service worker file and where it is registered, the build plugin that generates it (Workbox, vite-plugin-pwa), `manifest`, local storage use (IndexedDB, localStorage), the HTTP layer and retry code, and how updates are shipped.
3. **Check** against the checklist. Distinguish what the code shows from what needs a browser (DevTools Application panel, Lighthouse, airplane mode). Say which you did not run.
4. **Report**, most severe first, one line each: `file:line`, the problem, the fix. Critical: stale app that can never update, or private data cached for the wrong user. End with "Not verified" and the steps to test offline by hand.

## Fix
Offer the list; on approval change in small steps. Prefer a maintained tool (Workbox or the framework's PWA plugin) over a hand-written service worker. Test: build, load, go offline in DevTools, reload, then ship a new version and confirm it updates.

End with one line: what was reviewed, what was not verified, any risk left.
