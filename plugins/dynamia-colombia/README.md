# dynamia-colombia

Colombian tax and compliance knowledge for Claude Code, for teams that build business software in Colombia. No hooks. It explains the vocabulary, guides electronic invoicing and información exógena (medios magnéticos), structures tax calculations, and, above all, teaches Claude to **look up and cite current rules from official sources** instead of answering from memory.

> Not legal or tax advice. Rules change often; every answer carries an as-of date and links. Confirm with the company's accountant or tax lawyer. Facts here were read from the DIAN normograma on 2026-10-23.

| Skill | Use it to |
|---|---|
| `normativa` | Find, verify and cite current rules (DIAN normograma, Estatuto Tributario, resolutions, concepts); check a rule is in force |
| `glossary` | Explain DIAN terms (NIT, RUT, UVT, CUFE, RADIAN, retención...) and validate a NIT check digit |
| `einvoicing` | Build or review electronic invoicing: documents, numbering, CUFE, signing, validación previa, contingency |
| `exogena` | Generate and review información exógena (medios magnéticos): obligated parties, formats, calendar, mapping from the ERP |
| `taxes` | Design IVA, retenciones, ICA, INC, renta and SIMPLE calculations as dated, UVT-based rules |

Tool: `bin/co-nit dv|check|split <nit>` computes and checks the NIT check digit (Python 3, standard library). Tests: `python3 -m unittest discover -s tests`.

Official material is linked, never copied. If `dynamia-platform` is installed, the skills point to its `finances` reference as an optional extra.

Install:

```
/plugin marketplace add dynamiatools/claude-plugins
/plugin install dynamia-colombia@dynamia-tools
```
