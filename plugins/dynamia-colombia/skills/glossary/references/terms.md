# Terms

Explanatory, as of 2026-10-23. The binding text is the rule cited by `dynamia-colombia:normativa`. A "(check)" marks a code or detail to confirm in the DIAN technical tables before using it in software.

## Identification
| Term | Meaning |
|---|---|
| **NIT** | Número de Identificación Tributaria of a company or taxpayer. Written `900.302.344-1`: body (up to 9 digits for companies; 15 supported by the DV algorithm) and **DV**. In software store the body and the DV in separate fields |
| **DV** | Dígito de verificación, computed from the NIT body (`co-nit`) |
| **Cédula (CC)** | Citizen id; for a natural person the NIT is usually the cédula number plus a DV |
| **Tipo de documento de identificación** | Code of the id type in invoices and exógena: 11 registro civil, 12 tarjeta de identidad, 13 cédula de ciudadanía, 21 tarjeta de extranjería, 22 cédula de extranjería, 31 NIT, 41 pasaporte, 42 documento extranjero, 43 sin identificación del exterior o para uso definido por la DIAN, 47 PEP, 50 NIT de otro país, 91 NUIP (check in the annex tables). Verified use: type 43 with number 888888888 for an unidentifiable seller, and 444444001 to 444449999 for foreign third parties without a tax number (Res. 162 de 2023) |
| **RUT** | Registro Único Tributario: the taxpayer's registry at the DIAN, with identity, activities (CIIU), and **responsabilidades** (obligations) |
| **Responsabilidades del RUT** | Codes that say what the taxpayer is: for example responsable de IVA, agente de retención, autorretenedor, gran contribuyente, régimen SIMPLE, facturador electrónico, informante de exógena. In e-invoices they appear as codes like `O-13` gran contribuyente, `O-15` autorretenedor, `O-23` agente de retención de IVA, `O-47` régimen simple, `R-99-PN` no responsable (check) |
| **CIIU** | Clasificación Industrial Internacional Uniforme: economic activity code (Rev. 4 A.C.) |

## Units and taxes
| Term | Meaning |
|---|---|
| **UVT** | Unidad de Valor Tributario: yearly-updated unit in which thresholds and fines are set. 2026: $52.374 (Resolución 000238 de 2025). Store thresholds in UVT and the UVT by year, never converted pesos |
| **IVA** | Impuesto sobre las ventas. Responsables vs no responsables; goods/services *excluidos* (no IVA, no right to deduct), *exentos* (0% with right to deduct), tarifa general and diferenciales (Estatuto Tributario, art. 468 and following) |
| **INC** | Impuesto nacional al consumo (restaurants, mobile telephony, vehicles...) |
| **ICA** | Impuesto de industria y comercio: municipal; rates per municipality and activity; has its own retention (reteICA) |
| **Retención en la fuente** | Advance collection of a tax by the payer: a *retención a título de renta*, **ReteIVA** (withholding of IVA) and **reteICA**. The company that withholds is an *agente de retención* |
| **Autorretenedor** | A taxpayer authorized to withhold from itself |
| **Gran contribuyente** | A taxpayer designated by the DIAN with its own deadlines and duties |
| **Régimen SIMPLE** | Simplified tax regime (impuesto unificado) for small businesses, with its own invoicing and filing rules |
| **Renta** | Income tax (personas jurídicas and naturales) |
| **GMF** | Gravamen a los movimientos financieros (the "4 por mil") |

## Electronic invoicing
| Term | Meaning |
|---|---|
| **Factura electrónica de venta** | The invoice in XML (UBL 2.1), digitally signed, validated by the DIAN **before** it is issued (validación previa) |
| **Documento equivalente electrónico** | Electronic version of documents that replace the invoice in some cases: POS ticket (tiquete de máquina registradora), cinema ticket, transport ticket, public services bills, and others; has its own technical annex |
| **Documento soporte** | Document that supports purchases from sellers not obliged to invoice (it lets the buyer deduct); also for some foreign services |
| **Nota crédito / nota débito** | Electronic documents that reduce/cancel or increase an invoice; they reference the original invoice |
| **Nómina electrónica** | Electronic payroll support document |
| **CUFE** | Código Único de Factura Electrónica: SHA-384 hash that identifies an invoice that went through validación previa |
| **CUDE** | Same idea for notes and equivalent documents. **CUDS**: for the documento soporte |
| **Anexo técnico** | The DIAN document that defines fields, formats, rules and code lists for each electronic document; versioned (the sales invoice annex is v1.9 as of 2026-10-23, see `einvoicing`) |
| **Validación previa** | The DIAN checks the document before it can be issued; the result comes as a response document; an invoice is considered issued only when validated and delivered to the buyer |
| **Habilitación** | The process to get authorized to invoice electronically: register, run test sets in the *habilitación* environment, then move to *producción* |
| **Resolución de numeración** | The DIAN authorization of a numbering range (prefix, from-to, validity dates) |
| **Proveedor tecnológico** | Authorized company that issues and transmits documents for others, or the software provider that the invoicer declares |
| **Contenedor electrónico (AttachedDocument)** | XML that packages the signed document and the DIAN validation response for delivery to the buyer |
| **Representación gráfica** | The human-readable PDF of the document, with the QR code and CUFE |
| **RADIAN** | Registro de facturas electrónicas de venta como título valor: events (acuse, recibo, aceptación, endoso, etc.) that let an invoice be traded or financed |
| **Contingencia** | Allowed fallbacks when the system cannot validate (invoice without prior validation, to be transmitted within 48 hours after the DIAN service returns; paper only in cases the rule allows) |

## Reporting
| Term | Meaning |
|---|---|
| **Información exógena / medios magnéticos** | Yearly reports of third-party information that obligated taxpayers send to the DIAN, in numbered **formatos** (1001, 1005, 1006...). "Medios magnéticos" is the old name |
| **Año gravable (AG)** | The tax year reported (the filing happens the following year) |
| **Formato / concepto** | A format is a report layout (for example 1001, payments and withholdings); a concepto is a category inside it (for example 5002...) |
| **Cuantías menores** | Amounts below a threshold that are grouped in one aggregated record under a generic third party |
| **MUISCA** | The DIAN's online services platform where reports and declarations are filed |
| **Sanción por exógena** | Penalty for not filing, filing late or with errors (Estatuto Tributario, art. 651) |

## Legal texts
| Term | Meaning |
|---|---|
| **Estatuto Tributario (ET)** | Decreto 624 de 1989: the tax code, with all later modifications |
| **DUR 1625 de 2016** | Decreto Único Reglamentario en materia tributaria: compiles the tax decrees |
| **Resolución 000227 de 2025** | The DIAN's single compilation of tax resolutions |
| **Normograma** | The DIAN's official compilation of rules with their modification history |
| **Concepto / Oficio** | DIAN interpretation of a rule: not law, but the DIAN's position |
