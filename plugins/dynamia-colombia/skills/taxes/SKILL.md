---
name: taxes
description: Guides implementing and reviewing Colombian tax calculations in business software - IVA, retención en la fuente, ReteIVA, reteICA and ICA, impuesto al consumo, renta, régimen SIMPLE, UVT-based thresholds and rounding - designed as dated, data-driven rules. Use when a task calculates, configures, tests or documents Colombian taxes, withholdings, invoices totals or tax parameters.
argument-hint: "[tax or calculation]"
---

# dynamia-colombia:taxes

Tax values are **data with an effective date**, not constants. Read `references/design.md` before writing a calculation, and `dynamia-colombia:normativa` for every rate, threshold and table you use.

## Quick map (what exists; look up the current values)
| Tax | Idea | Where to read |
|---|---|---|
| **IVA** | General rate 19% (Estatuto Tributario art. 468, set by Ley 1819 de 2016); differential rates (for example 5%) in art. 468-1 and others; goods/services *excluidos*, *exentos*. Rules can change by decree: Decreto 1474 de 2025 suspended some measures and ceased to produce effects on 29 January 2026, which brought back art. 468-1 numeral 2 (5% for certain liquors) | ET on the normograma; DIAN conceptos |
| **Retención en la fuente (renta)** | The payer withholds on payments by concept (purchases, services, fees, rent, labor...). Base minimums are in UVT; rates by concept; labor withholding uses a UVT table (art. 383) | ET arts. 365 and following; the current withholding decree and DIAN tables |
| **ReteIVA** | Withholding of IVA by designated agents on the IVA of the operation (a percentage of the IVA) | ET art. 437-1 and following (confirm the current percentage) |
| **ICA and reteICA** | Municipal: rate per municipality and activity, filed per municipality; a retention exists in many | Each municipality's rules; the exógena also includes a rate report by municipalities |
| **Impuesto al consumo (INC)** | Restaurants, mobile telephony, some vehicles; separate from IVA and shown on invoices | ET arts. 512-1 and following |
| **Renta (personas jurídicas)** | General rate 35% (ET art. 240, Ley 2277 de 2022), with additional points for some sectors/incomes by law: read the current article | ET art. 240 |
| **Régimen SIMPLE** | Unified regime; its own rates by group of activities and bracket in UVT; electronic invoicing rules | ET arts. 903 and following |
| **GMF** | 4 por mil on financial movements | ET arts. 871 and following |
| **UVT** | Yearly value; 2026: $52.374 (Resolución 000238 de 2025) | normograma |
Article numbers above are the stable anchors; the **values inside them change**.

## Procedure
1. Identify the tax, the party (seller, buyer, withholding agent), the operation (good, service, concept) and the date.
2. Look up the rule valid on that date (`normativa`); record the source and effective dates in the code comment or the config.
3. Implement as a rule table (below) with tests per case; compute with `BigDecimal`/`Money`, never floating point.
4. Round exactly where the rule says (per line, per document, or at the declaration), and keep the unrounded value if needed for reconciliation.
5. Show the calculation breakdown to the user (base, rate, amount, rule id), not only the total.

## Optional pointers
If `dynamia-platform` is installed, its `extensions` skill documents `finances` (charges with priority and base, `Money`, VAT-included prices with `extractBase`/`extractTax`). Otherwise, if the project is built on Dynamia Platform, you can suggest `/plugin install dynamia-platform@dynamia-tools`. Electronic invoice amounts go through `dynamia-colombia:einvoicing`; exógena reconciliation through `dynamia-colombia:exogena`.

End with one line: rule versions used and as-of date, what was not verified, and who should confirm (the company's accountant).
