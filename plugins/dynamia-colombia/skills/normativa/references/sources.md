# Official sources

Checked on 2026-10-23. A URL that worked then may move; if it fails, search the title on the DIAN site.

## DIAN normograma (compilación jurídica)
Base: `https://normograma.dian.gov.co/dian/compilacion/docs/`
| Document | URL pattern or page |
|---|---|
| Resolución | `resolucion_dian_<NNNN>_<YYYY>.htm`, for example `resolucion_dian_0227_2025.htm` |
| Concepto / Oficio | `oficio_dian_<NNNN>_<YYYY>.htm`, for example `oficio_dian_5480_2025.htm` |
| Estatuto Tributario | `estatuto_tributario.htm` (Decreto 624 de 1989, with modifications) |
Pages are long (hundreds of thousands of characters): ask for one section at a time; the end of a page may not be readable in one request.

## Rules this plugin leans on (all verified to exist on the normograma)
| Rule | What it is |
|---|---|
| Resolución 000227 de 2025 | "Única en Materia Tributaria, Aduanera y Cambiaria" (DIAN): compiles the tax resolutions. Parte 1: Título 1 Registro (RUT...), 2 Liquidación y declaración, **3 Información exógena**, 4 Otros reportes, **5 Sistema de facturación** (facturación, documento soporte, nómina electrónica, RADIAN), 6 Aspectos internacionales, 7 Procedimientos, 8 Recaudo y devoluciones. Article numbers like 1.3.x are exógena, 1.5.x are invoicing |
| Resolución 000165 de 2023 | invoicing system; adopts Anexo Técnico de Factura Electrónica de Venta v1.9 and Anexo Técnico del Documento Equivalente Electrónico v1.0; articles compiled into 000227 |
| Resolución 000008 de 2024 | timing for moving to annex v1.9 (1 May 2024; v1.8 until then) |
| Resolución 000162 de 2023, 000188 de 2024 | exógena rules and formats for AG 2024 onwards |
| Resolución 000233 and 000237 de 2025 | exógena changes (new formats, new versions) applying from AG 2026 and later; see `exogena` |
| Resolución 000238 de 2025 | UVT 2026 = $52.374 |
| Concepto 5480 de 2025 | an invoice produces effects only when validated and delivered |

## DIAN pages and documents
- Exógena, normatividad by tax year: `https://www.dian.gov.co/impuestos/sociedades/ExogenaTributaria/Normatividad/Paginas/default.aspx`
- Exógena, presentación (how to file): `https://www.dian.gov.co/impuestos/sociedades/ExogenaTributaria/Presentacion/Paginas/default.aspx`
- Comunicado 053 de 2026 (calendar exógena AG 2025): `https://www.dian.gov.co/Prensa/Paginas/NG-Comunicado-de-Prensa-053-2026.aspx`
- Anexo técnico factura electrónica de venta v1.9 (PDF, large): `https://www.dian.gov.co/impuestos/factura-electronica/Documents/Anexo-Tecnico-Factura-Electronica-de-Venta-vr-1-9.pdf`
- Anexo técnico documento equivalente electrónico v1.0 (PDF): `https://www.dian.gov.co/impuestos/factura-electronica/Documents/Anexo-Tecnico-Documento-Equivalente-Electronico-V1-0-final.pdf`
- Guía de habilitación de factura electrónica (PDF): `https://www.dian.gov.co/impuestos/factura-electronica/Documents/Presentacion_habilitacion.pdf`
- Draft rules (never in force): `https://www.dian.gov.co/normatividad/Proyectosnormas/...` (the path says "Proyectos")

## Not reachable when checked
The DIAN invoicing landing pages under `/impuestos/factura-electronica/Paginas/` answered 404 from this tool, and the Senate's Estatuto Tributario site refused the connection. Use the normograma, or ask the user to open them.

## Other official places (not verified from here)
Diario Oficial (publication date of a rule); Presidencia and Función Pública "Gestor Normativo" (laws and decrees); Superfinanciera and the Cámaras de Comercio (RUES, Registro Mercantil); municipal secretarías de hacienda (ICA); the Corte Constitucional and Consejo de Estado (rulings that annul or condition a rule).
