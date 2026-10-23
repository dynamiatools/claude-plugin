# finances

A calculation framework for financial documents: lines, taxes, discounts, withholdings and fees, totals, money and currency. Module `extensions/finances/sources/api` only (no persistence, no UI). Checked against the source and tests in framework 26.10. **The README is a design spec and drifts from the code** (it shows `setQuantity(BigDecimal)`, the code takes `double`); follow the signatures below and the tests in `api/src/test`.

## Principles
- The document holds state; **calculation is a separate engine** (`FinancialCalculator`) that is deterministic, persists nothing and never queries exchange rates (the document stores the rate used).
- One abstraction, `Charge`, for taxes, discounts, withholdings and fees.
- Money is a value object with a currency; mixing currencies without a rate is an error.
- You persist your own entities and map them to/from `FinancialDocument`; store the totals for audit.

## Model
| Class | Notes |
|---|---|
| `FinancialDocument` | `of(DocumentType, currency)`; `type` (SALE, PURCHASE, CREDIT_NOTE, DEBIT_NOTE, ADJUSTMENT, QUOTE), `status` (DRAFT, POSTED, CANCELLED), `issueDate`/`dueDate` (`LocalDate`), `party`, `currency`, `exchangeRate`, `lines`, `charges`, `totals`; `addLine`, `addCharge`, `addTax/addDiscount/addFixedDiscount/addWithholding/addFee/addPercentageFee`, `validate()`, `post()`, `cancel()`, `copy()` |
| `DocumentLine` | `DocumentLine.of(description, quantity(double), Money unitPrice)`, fluent `.tax(code, name, pct)`, `.discount`, `.withholding`, `.fee`, `.itemCode`, `.itemName`; `totals` (`LineTotals`) |
| `Charge` | `code`, `name`, `type` (TAX, DISCOUNT, WITHHOLDING, FEE), `rateType` (PERCENTAGE, FIXED, FORMULA), `value`, `appliesTo` (LINE, DOCUMENT), `base` (`ChargeBase`: NET, GROSS, PREVIOUS_TOTAL), `priority` (ascending order), `refundable` |
| `DocumentTotals` | `subTotal`, `discountTotal`, `taxTotal`, `withholdingTotal`, `feeTotal`, `grandTotal`, `payableTotal` (= grandTotal - withholdingTotal) |
| `LineTotals` | `baseAmount`, `discountTotal`, `taxTotal`, `withholdingTotal`, `feeTotal`, `netTotal` |
| `Money` | immutable; `Money.of(amount, "COP")`, `zero(currency)`, `add`, `subtract`, `multiply`, `divide(d, scale, mode)`, `percentage`, `round(scale)`, `roundToCurrency()`, `negate`, `abs`, `isZero/isPositive/isNegative`, `extractBase(pct)`, `extractTax(pct)`, `addTax(pct)` |
| `ExchangeRate` | `fromCurrency`, `toCurrency`, `rate`, `date` |

## Calculate
```java
FinancialDocument invoice = FinancialDocument.of(DocumentType.SALE, "COP");
invoice.setIssueDate(LocalDate.now());
invoice.addLine(DocumentLine.of("Product A", 10, Money.of("100000", "COP"))
        .discount("DISC10", "Commercial discount", new BigDecimal("10"))   // priority 10
        .tax("IVA19", "VAT 19%", new BigDecimal("19")));                    // applied after
invoice.addWithholding("RETE", "Withholding 2.5%", new BigDecimal("2.5"));  // document level

FinancialCalculator calc = new DefaultFinancialCalculator();
calc.calculateDocument(invoice);       // also calculateLine(line), recalculate(invoice)
Money total = invoice.getTotals().getGrandTotal();
```
Charges apply in ascending `priority`; a charge's `base` says what it applies to. A `POSTED` document is frozen and is not recalculated; changes need a reversal or a note (`InvalidDocumentStateException`). Invalid input raises `FinancialCalculationException`; mixed currencies raise `InvalidCurrencyOperationException`. Check what is exact in the source before relying on a message.

## Prices that already include tax (Colombian style)
Menus and shops often show the price with VAT. Do not feed that price to the engine as a unit price and add VAT again. First split it:
```java
Money withVat = Money.of("20000", "COP");
Money base = withVat.extractBase(new BigDecimal("19"));   // 16806.72
Money vat  = withVat.extractTax(new BigDecimal("19"));    // 3193.28
Money back = base.addTax(new BigDecimal("19"));           // 20000.00
```
Rules from the project's own guide (`extensions/finances/docs/COLOMBIA-INVOICING.md`): use `extractBase` when the displayed price includes VAT; put VAT as a document-level charge to apply it to all lines; keep taxed and exempt products on separate lines; use `ChargeBase.NET` for withholdings (on the taxable base), not `PREVIOUS_TOTAL`; never apply VAT twice (in the price and as a charge).

## Extend
- New rate logic: implement `ChargeStrategy` (`Money calculate(Charge, Money base, Object context)`, `boolean supports(RateType)`) and register it with `ChargeCalculator.registerStrategy(...)`; built-ins: `PercentageChargeStrategy`, `FixedChargeStrategy`, `FormulaChargeStrategy`. Use `new DefaultFinancialCalculator(lineCalculator, totalsAggregator)` to swap parts.
- Hooks: `BeforeDocumentCalculateEvent`, `AfterDocumentCalculateEvent`, `ChargeAppliedEvent`, `TotalsCalculatedEvent`, `BeforeDocumentPostEvent`, `AfterDocumentPostEvent` (all `DocumentEvent`s with the document and a timestamp), compatible with Spring's `ApplicationEventPublisher` and `@EventListener`. Use them for validations, regional rules and integrations.
- Regional rules (a country's taxes) are data and strategies you add, not changes to the core.

## Do / don't
- Use `BigDecimal` and `Money`, never `double`, for amounts (`DocumentLine` quantity is the exception).
- Keep currency codes consistent; set the exchange rate on the document once.
- Round at the end through the engine; do not round each line by hand.
- Don't call the calculator inside a loop of UI events without debouncing; it recalculates the whole document.
- Don't use it for accounting ledgers or e-invoicing formats: it computes totals only (the README lists what it does not implement).
