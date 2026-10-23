---
name: normativa
description: How to find, verify and cite current Colombian tax and invoicing rules from official sources (DIAN normograma, Estatuto Tributario, resolutions, decrees, concepts) before writing code or answering. Use whenever a task depends on a rate, a UVT value, a deadline, an annex version, an obligation threshold or whether a rule is still in force.
argument-hint: "[topic or rule]"
---

# dynamia-colombia:normativa

Colombian tax rules change every year, sometimes by decree within weeks. **Do not answer a rule from memory and do not hard-code a value that has an effective date.** Look it up, cite it, and say as of when.

## Procedure
1. **Name the rule you need** (for example "UVT 2026", "annex version for electronic invoice", "exógena obligation thresholds AG 2025").
2. **Find it in an official source** (`references/sources.md`). The DIAN **normograma** is the first stop: it shows each rule with its modifications and whether its articles were compiled into another rule.
3. **Check it is in force.** Look for: a later rule that modifies or repeals it; a compilation (Resolución 000227 de 2025 compiles most DIAN tax resolutions into one text); suspensions or loss of effect (for example Decreto 1474 de 2025 stopped producing effects on 29 January 2026, which brought back articles that it had suspended).
4. **Check the period.** Tax year (año gravable) versus the year the report is filed; effective date versus publication date.
5. **Answer short, with citations**: rule (type, number, year, article), what it says in your own words, the as-of date, and the link. Quote at most a short clause. Do not paste article texts, tables or annexes.
6. **Say what you could not confirm** (page unreachable, truncated, only a draft/proyecto found) and how the user can confirm it.

## Hierarchy (to resolve conflicts)
Constitution, Ley (Congress), Decreto (Government; the Decreto Único Reglamentario 1625 de 2016 compiles tax decrees), Resolución (DIAN technical rules, annexes), then doctrine: Concepto / Oficio (DIAN interpretation, not binding law but what the DIAN will apply) and court rulings. A *proyecto de resolución* is a draft: never treat it as in force.

## What is volatile (always look up)
UVT value (yearly), rates and thresholds expressed in UVT, tax calendar and deadlines (often changed by decree or extraordinary resolutions), technical annex versions and their dates, formats and fields of información exógena, withholding tables, municipal ICA rates, anything introduced by a recent reform or an emergency decree.

## What is stable enough to explain from knowledge
The structure of the system (what an electronic invoice is, what CUFE means, what exógena is), the vocabulary (`dynamia-colombia:glossary`), the order of a flow. Still cite the rule for anything a user will rely on.

## Output rules
- Always include an "as of <date>" line and the links.
- Never present this as legal or tax advice; for decisions with money or penalties, recommend the company's accountant or tax lawyer.
- If the sources disagree or are unclear, say so and give both.
- Keep the user's data private: do not put NITs, invoices or customer data into searches.

End with one line: what was verified, what was not, and how to confirm it.
