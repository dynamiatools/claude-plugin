---
name: exogena
description: Guides generating and reviewing Colombian información exógena (medios magnéticos) reports for the DIAN - who must file, formats such as 1001 or 1005, cuantías, third-party identification rules, the yearly calendar and the changes by año gravable - from an ERP or accounting database. Use when a task builds, maps, validates or schedules medios magnéticos or exógena formats.
argument-hint: "[año gravable] [formato]"
---

# dynamia-colombia:exógena

Read on 2026-10-23 from the DIAN normograma and the exógena pages. The **resolution of the año gravable and its annexes** (field layouts, versions, technical specifications) are the contract: this skill gives the map and the method, `dynamia-colombia:normativa` gives the lookup.

## Where the rules are
- Compiled in **Resolución 000227 de 2025, Parte 1, Título 3** (12 chapters: obligated parties, financial entities, deadlines, formats, sanctions, how to file). Article numbers look like `1.3.x`; formats are in `1.3.12.x`; deadlines in `1.3.9.x`.
- Rules per año gravable: AG 2024 and 2025 follow **Resoluciones 000162 de 2023 and 000188 de 2024** (plus later modifications such as 000208 and 000213 de 2025 for AG 2024). **Resoluciones 000233 and 000237 de 2025 change formats and specifications from AG 2026** (per DIAN comunicado 053 de 2026, which says they do not apply to AG 2025). The DIAN lists the rules by tax year on its "Normatividad" page (`normativa/references/sources.md`).
- Each format has a **versioned technical annex** (for example 1001 v11, 1476 v13 in Res. 233/2025). Always take the version of the año gravable.
- Sanctions for not filing, filing late or with errors: Estatuto Tributario art. 651. Filing obligations: art. 631.

## Method
1. **Fix the año gravable and the filer** (company NIT, type: persona jurídica, natural, gran contribuyente, retenedor...). Everything else depends on it.
2. **Decide whether the filer is obligated** (`references/formats.md`): thresholds are in UVT of the reported year or the previous one; many parties (retenedores, financial entities, facturadores...) are obligated without a threshold.
3. **List the formats that apply** and the version of each for that año gravable.
4. **Map ERP data to each format**: for every field of the annex, name the source table/column, the transformation, and the rule for empty values. Keep the mapping as a table in the repo and review it with the accountant.
5. **Apply the common rules**: third parties by id type and NIT body with DV; foreigners without a tax number; unidentifiable sellers; cuantías menores grouped; amounts and signs as the annex says; each payment reported once (a payment in a special format is not repeated in 1001).
6. **Generate the files** exactly per the annex (XML structure, naming, one file per format and sequence as specified). Validate with the DIAN **prevalidadores** (the comunicado recommends the "Prevalidadores Información Tributaria" for the year) and follow the DIAN "Cartilla de Presentación de Información por Envío de Archivos" for upload; confirm the channel and signing requirements there.
7. **Reconcile** against the accounting: totals of 1001 vs withholdings accounts, 1005/1006 vs IVA ledgers, 1007 vs income, 1008/1009 vs balances. Differences must be explained before filing.
8. **Plan the calendar** per NIT last digit and filer type; deadlines are set by decree/resolution and sometimes extended; look them up each year.

## Design for an ERP
- Store the **tax year, format, version** and a run id on every generated file; keep the input snapshot so a run can be reproduced.
- Build **one generator per format** with its own tests (golden files from the DIAN examples) so a new annex version adds a generator, not a rewrite.
- Keep **third-party master data** clean (id type, NIT/DV, names, address, DANE municipality and department codes, country); most rejections are data quality.
- Keep thresholds as **data with UVT by year**, never constants (`UVT` 2026 = $52.374, Res. 000238 de 2025).
- Treat generation as a **background job** with a validation report (errors by format/row) the accountant can read.

## Output rules
Cite the resolution and annex version per format, say the as-of date, and end with: what was verified, what is pending the accountant, and the filing deadline source.
