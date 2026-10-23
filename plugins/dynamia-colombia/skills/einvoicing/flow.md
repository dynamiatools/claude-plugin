# The issuing flow

General shape, to be checked against the annex and the DIAN habilitación guide (see `normativa` sources). Web service names, endpoints and field names change between annex versions: copy them from the annex, not from this file.

## 1. Habilitación (once per company and software)
Register the invoicer in the DIAN invoicing service, declare the software (own or a proveedor tecnológico), get the test-set identifier, issue the documents the DIAN asks for in the *habilitación* environment, and pass its evaluation; then the company is enabled for *producción*. Request the **numbering authorization** (resolución de numeración) for each prefix and range. Each environment has its own credentials.

## 2. Issue (per document)
1. **Take the next number** inside the authorized range and validity; concurrency-safe and gap-aware (a number is consumed once).
2. **Build the data**: seller and buyer (NIT with DV, RUT responsibilities, identification type), lines, taxes, discounts, totals, payment form and means, dates in Colombia time, notes and references (the original invoice for notes).
3. **Compute totals** with decimal arithmetic and the rounding rules of the annex; line, tax and document totals must reconcile exactly, or validation rejects them.
4. **Generate the XML** (UBL 2.1 in the structure of the annex), with the **CUFE** (or CUDE for notes and equivalents) computed as the annex defines (a SHA-384 hash over an ordered list of fields; copy the exact field order and formats from the annex, they are validated).
5. **Sign** with the company's digital certificate (the signature profile is in the annex).
6. **Transmit** to the DIAN validation service; keep the response (accepted, rejected with rule codes, or notified warnings). Use the synchronous or asynchronous channel the annex offers; poll asynchronous results with the tracking id.
7. **Package** the signed document and the DIAN response in the electronic container (AttachedDocument), build the **PDF representation** with the QR and CUFE, and **deliver** to the buyer's reception email.
8. **Record** everything: XML, response, CUFE, container, PDF, timestamps, who triggered it.

## 3. After issuing
- **Notes**: correct or cancel with a credit note, increase with a debit note; each references the original CUFE.
- **Events** (RADIAN): acknowledgements of receipt and acceptance by the buyer, and endorsement flows for financing.
- **Contingency**: when the DIAN service cannot validate, the rules allow issuing without prior validation and transmitting later (48 hours after the service returns); keep the evidence of the outage.

## Design points for an ERP
- Model the **document** (draft, issued, rejected, cancelled-by-note) separately from the **transmission attempts** (many per document).
- Make sending **idempotent**: a retry must never create a second consecutive.
- Run transmission **in the background** with a queue, retries with backoff and a visible status; the user must see "issued" only after validation.
- Multi-company or SaaS: certificate, software id/PIN, numbering resolution, environment and test set are **per account**; load them with the tenant bound (`AccountTenants.runAs` in Dynamia apps). Never share one certificate across customers.
- Keep **clock and timezone** under control: use `America/Bogota`; compare the generation date with the signing time.
- Validate **before** sending: NIT DV (`co-nit`), required buyer fields, tax codes from the annex lists, totals reconciliation, number in range.
- Keep annex **versions** as data (`annexVersion` on the document or the environment) so a migration (v1.8 to v1.9) can run side by side.
- Log DIAN rule codes and show them to the user in plain language; the annex lists them.
