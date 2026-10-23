# Frontend performance checklist

Thresholds from web.dev (Core Web Vitals, checked 2026-10-22): LCP 2.5 s, INP 200 ms, CLS 0.1, at the 75th percentile, mobile and desktop separately.

## Loading (LCP)
- The LCP element (hero image or heading) is in the first HTML, not injected late by script. Give an LCP image `fetchpriority="high"` and never `loading="lazy"`.
- Fewer render-blocking CSS and JS requests on the critical path. Inline only small critical CSS; defer the rest. `defer` or `type="module"` for scripts.
- Fast server response: caching headers, compression (brotli or gzip), HTTP/2 or 3, a CDN for static files. SSR or prerender for content pages.
- `preconnect` only to origins used right away; `preload` only for resources found late (fonts, LCP image).

## Bundle
- Route-level code splitting (lazy routes). Heavy widgets (charts, editors, maps, PDF) are loaded on demand.
- Look at the largest dependencies first: moment, lodash (full), icon packs imported whole, UI libraries without tree-shaking, duplicate versions. Use the lighter equivalent or per-module imports.
- No dead code or unused CSS shipped (Tailwind purges by default; check content globs). Production build, minified, source maps not served publicly.
- Third-party scripts (analytics, chat, ads) loaded async, late, and counted in the budget.
- Rough budgets to start from: initial JS under ~170 KB gzip for a content page, under ~300 KB for an app. Adjust to the audience's devices and networks.

## Images and fonts
- Right format (AVIF or WebP, SVG for icons), right size (`srcset`/`sizes`), compressed; lazy load below the fold; `width` and `height` or `aspect-ratio` set.
- Fonts: WOFF2, subset, at most 2 families and few weights, `font-display: swap` (or `optional`), preload the one used above the fold. System fonts cost nothing.
- Video and large animations: no autoplay of heavy files; poster images.

## Interactivity (INP)
- No long tasks (over 50 ms) on input: split work, defer non-urgent work (`requestIdleCallback`, `scheduler.yield` where supported), move heavy computation to a Web Worker.
- Event handlers are cheap; debounce or throttle scroll, resize and typing handlers; passive listeners for scroll and touch.
- Hydration cost on SSR pages: hydrate only what is interactive (islands, lazy hydration).

## Rendering cost
- Long lists are virtualized or paginated. Avoid rendering thousands of DOM nodes.
- Framework hot spots: avoid recomputing in render or in templates, avoid watchers on big objects, use `v-memo`/`computed` (Vue) or `memo`/`useMemo` (React) only where profiling shows a cost. Stable keys in lists.
- Animate `transform` and `opacity`; avoid layout thrashing (read then write DOM in batches). `content-visibility: auto` for long off-screen sections.

## Stability (CLS)
- Reserve space for images, ads, embeds and late content. Skeletons match final size. Do not insert content above what the user is reading.
- Font swap does not move layout (size-adjust or matching fallback metrics).

## Network
- Cache API responses and static files with correct headers; hashed filenames with long `max-age`, HTML with revalidation.
- Avoid request waterfalls: fetch in parallel, do not wait for a component to mount to start loading its data. Batch or paginate chatty APIs.
- Offline and repeat visits: see `dynamia-ui:offline-review`.

## Tools
Build size report or bundle visualizer, Lighthouse, Chrome DevTools Performance panel, WebPageTest, and real-user data (CrUX, `web-vitals` library) when it exists. Lab numbers guide fixes; field data decides if it worked.
