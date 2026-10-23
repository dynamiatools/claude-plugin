# SEO checklist

Facts here come from Google Search Central (JavaScript SEO basics and robots/sitemap docs), checked 2026-10-22. Recheck before quoting exact limits.

## Client-rendered apps (check first)
- Google renders JavaScript in a second pass, which can take longer than a few seconds, and needs the content to appear in the rendered HTML. It still recommends server-side rendering or prerendering. For public content in a SPA, recommend SSR or prerender (Nuxt, Astro, a prerender plugin). Private screens behind a login need none.
- Routes use the History API, never `#/fragment` URLs.
- Links are `<a href>` elements. A click handler on a `div` or a button is not a link to a crawler.
- Do not ship `noindex` in the initial HTML and try to remove it with script: Google may skip rendering when it sees `noindex`.
- A canonical set by script must match the HTML one, and there must be only one.
- Unknown routes return a real 404 status, or the error view gets `noindex`. A 200 with "not found" text is a soft 404.
- Use fingerprinted asset names; do not block CSS, JS or images in `robots.txt`.

## Crawling and indexing
- `robots.txt` exists at the root, does not block what should rank, and points to the sitemap. It controls crawling, not indexing: use `noindex` to keep a page out, and do not block a page you want `noindex` to be seen on.
- `sitemap.xml` lists the canonical, indexable URLs (200, no redirect, no `noindex`), with `lastmod` only if it is accurate.
- One canonical per page, absolute URL, self-referencing on the preferred version. One host and protocol (https, www or not) enforced by 301.
- Permanent redirects are 301/308, no chains. Deleted pages return 404 or 410.
- HTTPS everywhere, no mixed content. Pages respond fast and with a stable status.
- Staging and preview sites are `noindex` or behind auth.

## Metadata
- Unique `<title>` per page (describe the page, put the main words first, keep it readable, roughly under 60 characters shown) and a `<meta name="description">` that summarizes it (about 150 characters; Google may rewrite it).
- Open Graph (`og:title`, `og:description`, `og:image`, `og:url`) and Twitter card tags for sharing.
- `<html lang>` set. `hreflang` pairs are reciprocal and include a self reference, with `x-default` where useful.
- Favicon and theme color present.

## Content and structure
- One `h1` that matches the page's topic, then a sensible heading order. Semantic landmarks (`header`, `nav`, `main`, `footer`).
- Meaningful link text, not "click here". Descriptive `alt` for informative images and file names that say something.
- Text is real text in HTML, not an image. Important content is not hidden behind clicks or infinite scroll without crawlable URLs (paginate with links).
- Avoid thin and duplicate pages; consolidate with canonical or redirects.

## Structured data
- JSON-LD that matches visible content: Organization, WebSite, BreadcrumbList, Article, Product, FAQ only where the page truly qualifies. Valid JSON, required properties present. Validate in the Rich Results Test.

## Mobile and speed
- Responsive, viewport meta, same content on mobile and desktop (Google indexes the mobile version).
- Core Web Vitals at the 75th percentile: LCP 2.5 s or less, INP 200 ms or less, CLS 0.1 or less. Details in `dynamia-ui:perf-review`.
