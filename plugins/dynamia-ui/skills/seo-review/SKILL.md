---
name: seo-review
description: Reviews a website or web app for search engine visibility and fixes it with approval. Covers crawling and indexing, metadata, headings, structured data, links, internationalization and client-side rendering risk. Use when the user asks for an SEO review or audit, why pages are not indexed, or how to improve search visibility.
argument-hint: "[path or URL] [review|fix]"
---

# dynamia-ui:seo-review

**Review** is read-only; **fix** changes code only after approval. Checklist and the facts it rests on are in `references/checklist.md`.

## Review
1. **Detect how pages are produced**: static HTML, SSR or prerender (Nuxt, Next, Astro), or a client-rendered SPA. This sets the biggest risk, so say it first.
2. **Read the code** that decides what a crawler gets: index.html or layout, router, head management, `robots.txt`, `sitemap.xml`, server redirects, structured data. Review the templates, not every page.
3. **Run** only what is available and safe: a local build output, or `curl -sI` and `curl -s` against a URL the user gave. Do not crawl third-party sites.
4. **Report**, most severe first, one line each: `file:line` or URL, the problem, the fix. Levels: Critical (blocks indexing), High, Medium. End with "Not verified" (real index status, Search Console data, rendered output) and tell the user how to check: URL Inspection tool and Rich Results Test.

## Fix
Offer the list; on approval apply in small steps (indexing blockers first), run the build, and re-check with the same command or file read. Keep titles and descriptions as proposals the user can edit; do not invent claims about the business.

Core Web Vitals and page weight go to `dynamia-ui:perf-review`. End with one line: what was reviewed, what was not verified, any risk left.
