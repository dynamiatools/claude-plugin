# Designing tax calculations

## Rules as data
A tax rule is a row: `tax`, `concept`, `appliesTo` (party/operation conditions), `rate` or table, `baseMinUVT`, `validFrom`, `validTo`, `source` (rule and article). The engine picks the rule valid on the **operation date** (not today's date). A change of law is a new row, not a code change; old documents keep recalculating with the rule they had.

## Thresholds in UVT
Store `baseMinUVT` and a `UVT(year)` table. Convert at calculation time: `thresholdPesos = baseMinUVT * UVT(year of the operation)`. Never store pesos amounts that were UVT multiples.

## Typical calculation order for a purchase or sale line
1. Base = quantity * unit price - discounts that reduce the taxable base (conditioned vs unconditioned discounts differ: read the rule).
2. IVA = base * rate (excluded: none; exempt: 0% with right to deduct).
3. INC if applicable (a separate tax, shown separately).
4. Withholdings: retención (renta) on the base if it exceeds the minimum and the payer is an agent; ReteIVA on the IVA if applicable; reteICA per municipality.
5. Totals: subtotal, taxes, withholdings, payable = total - withholdings.
Check the exact base and the order in the rule: they differ by tax. For VAT-included prices, extract the base first, then tax (do not add IVA twice).

## Rounding
Decimal arithmetic with an explicit scale and rounding mode; electronic invoices follow the annex decimals; declarations round amounts as their instructions say (forms usually approximate to the nearest thousand: confirm for the form you build). Reconcile line, document and ledger totals; a one-peso difference is a rounding policy question to settle with the accountant.

## Who withholds
The withholding depends on the payer (agente de retención, autorretenedor, gran contribuyente) and the payee (régimen, responsabilidades, residence), both from the RUT. Model them as attributes of the third party with `validFrom`/`validTo`, not as booleans without dates.

## Testing
- One test per rule row and per edge: exactly at the threshold, one peso below/above, before/after the change date.
- Real examples from the accountant (invoice, withholding certificate) as golden tests.
- A test per municipality for ICA/reteICA you support.
- Property check: sum of line totals equals document totals under the chosen rounding policy.

## Parameters and configuration
Keep company-level facts (regime, responsabilidades, municipality, ICA activity codes, withholding agent status) in configuration that can change over time and per tenant. In SaaS apps they are per account (`AccountTenants`, see `dynamia-platform`).

## What not to do
- Don't hard-code 19, UVT or any rate without a source and an effective date.
- Don't compute with `double` or `float`.
- Don't mix excluded and exempt as the same thing: the right to deduct differs.
- Don't present a result as tax advice; the accountant signs off.
