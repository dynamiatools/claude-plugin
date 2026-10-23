# Review checklist for an electronic invoicing implementation

Mark each item OK / gap / not verified, with `file:line` when it is code.

**Legal flow**
- [ ] Issued only after validación previa and delivery; UI never shows "issued" before.
- [ ] Numbering uses an authorized range and prefix, within validity; no gaps by retries; no reuse.
- [ ] Annex version is explicit and matches what the DIAN requires on the document date.
- [ ] Notes reference the original CUFE; cancellations are done by credit note.
- [ ] Contingency path exists and transmits within the allowed time.

**Data**
- [ ] NIT stored as body + DV, DV validated; identification type codes from the annex lists.
- [ ] Tax codes, payment form/means, units of measure, currency and country codes come from the annex lists, not free text.
- [ ] Decimal arithmetic (`BigDecimal`/`Money`), no floating point; totals reconcile line by line.
- [ ] Dates and times in Colombia time; generation date consistent with the signature.
- [ ] Buyer reception email stored and used for delivery.

**Security and operations**
- [ ] Certificate and password, software PIN and test-set id are per company/environment, stored securely, not logged, not committed; certificate expiry is monitored.
- [ ] Habilitación and producción are separated; a test document can never go to producción.
- [ ] Transmission is asynchronous, idempotent, with retries and visible status; DIAN rule codes are surfaced.
- [ ] XML, response, container and PDF are stored and retrievable by CUFE; retention period is defined by the company's accountant.
- [ ] Tenant isolation: one company's documents, numbering and secrets are never visible to another.

**Tests**
- [ ] Unit tests for totals and rounding with real invoices (exempt, excluded, several IVA rates, discounts, withholdings).
- [ ] Contract tests against the annex (generate XML, validate against the XSD/rules in habilitación).
- [ ] A rejected-document path and a retry path.

Output: findings by severity (blocks legal validity, risk, improvement), then "Not verified" and who should confirm.
