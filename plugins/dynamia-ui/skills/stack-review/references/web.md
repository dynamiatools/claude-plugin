# Web targets

| Need | Pick | Alternative |
|---|---|---|
| New app or dashboard, behind login, no SEO | Vue 3 + Vite + Tailwind (Pinia for state, Vue Router) | React + Vite if the team already knows it |
| Public site, SEO, marketing + app | Nuxt (SSR or prerender) + Tailwind | Astro for mostly static content with islands |
| Mostly static content, blog, docs | Astro or VitePress | Nuxt Content |
| Offline-capable or installable | Vue + Tailwind + a PWA plugin (Workbox) | see `dynamia-ui:offline-review` |

Check list when judging an existing web stack
- Client-only rendering for public content is an SEO risk (see `dynamia-ui:seo-review`).
- A component library is a decision: it speeds screens and constrains design. Prefer headless or Tailwind-based pieces when a custom design system exists; a full library (Vuetify, PrimeVue, MUI) when speed and consistency matter more than a custom look.
- Tailwind: one config, tokens in CSS variables, content globs correct so unused CSS is purged.
- TypeScript on, strict where the team can bear it. Vite for builds. Vitest + Playwright for tests.
- Avoid: two UI libraries at once, state libraries for local state, jQuery plus a framework on the same page.
