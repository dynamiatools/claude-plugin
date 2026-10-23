---
name: glossary
description: Explains Colombian DIAN and tax vocabulary used in software for businesses - NIT and its check digit, RUT, UVT, CUFE, CUDE, RADIAN, retención, exógena, régimen SIMPLE - and validates a NIT. Use when a task, spec or code mentions a DIAN term, an identification type code, a RUT responsibility or an unfamiliar Colombian tax acronym.
argument-hint: "[term or NIT]"
---

# dynamia-colombia:glossary

1. Find the term in `references/terms.md` and explain it in plain language, in the user's language, with the code or field name it has in software when there is one.
2. These are explanations, not the binding text. For anything a user will rely on (rates, thresholds, obligations, deadlines) go to `dynamia-colombia:normativa`.
3. **NIT check digit**: `${CLAUDE_PLUGIN_ROOT}/bin/co-nit dv <nit>` computes the DV, `check 900302344-1` validates it, `split` separates the body and the DV (Python 3, standard library). The algorithm is the DIAN's (weights 3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71 from the right, modulo 11). A valid DV proves only that the number is well formed, not that the taxpayer exists: the RUT is the source of truth.
4. If the term is not in the file, say so and look it up (normograma, DIAN site) instead of guessing.

Keep answers short: the term, what it is, where it shows up in software, the rule to read.
