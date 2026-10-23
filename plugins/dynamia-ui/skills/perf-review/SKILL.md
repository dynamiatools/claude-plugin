---
name: perf-review
description: Reviews frontend performance and fixes it with approval. Covers Core Web Vitals, bundle size, code splitting, images, fonts, rendering cost and network use. Use when the user says the app or page is slow, asks about bundle size, Lighthouse, LCP, INP or CLS, or wants a performance audit.
argument-hint: "[path or URL] [review|fix]"
---

# dynamia-ui:perf-review

**Review** is read-only; **fix** changes code only after approval. Measure before and after: no fix without a number. Checklist in `references/checklist.md`.

## Review
1. **Get numbers** if the project allows it, cheapest first: the build's own size report, `du` of the output folder, bundle analyzer output, Lighthouse (`npx lighthouse <url> --only-categories=performance` if the user has a URL or local server). State which numbers you could not get.
2. **Find the cost** by reading entry points, router (is it lazy?), heaviest dependencies in `package.json`, image and font loading, and the largest components or lists.
3. **Report** by expected gain, biggest first, one line each: `file:line`, the cost (with the number when you have it), the fix. Targets (75th percentile): LCP 2.5 s or less, INP 200 ms or less, CLS 0.1 or less. End with "Not verified" (field data, real devices, slow networks).

## Fix
Offer the list; on approval do one change at a time, rebuild, and show the new number next to the old. Revert a change that does not move its metric. Do not trade accessibility or correctness for speed.

End with one line: what was measured, what was not, any risk left.
