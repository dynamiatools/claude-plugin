# reports

Reports stored as queries (JPQL or SQL) with filters, run on screen, exported, sent by email, embedded in dashboards. Checked against `extensions/reports` (modules `api`, `core` without ZK, `ui` legacy ZK) and its README in framework 26.10.

## Concepts
`ReportGroup` has `Report`s; a report has a query (`queryLang`, `queryScript`), a data source (the app database or an external `ReportDataSource`), filters, columns, charts, export formats, `accessRoles`, `queryTimeout`, and an `endpoint` name. Definitions live in the database: users edit, copy, import and export them. The system account's reports are visible to every account.

## Run a report from code
`ReportsService` (core): `execute(report, filters, datasource)` returns `ReportData`; `findActives()`, `findActivesByGroup(group)`, `findByEndpoint(endpoint)` and `findByEndpoint(group, endpoint)`, `loadReportModel(id)`, `exportReport(report)` (a file) and `importReport(file)`, `findExportableReports(includeSystem)`. Exports go through `ReportDataExporter` implementations (CSV, Excel, formatted Excel, PDF, nested map).

## REST (`/apps/api/reports`)
Needs an authenticated user; only active reports of the current account and the system account that pass access policies are visible (else 404/403).
| Endpoint | Purpose |
|---|---|
| `GET /catalog` | groups with reports |
| `GET /{id}` | definition: filters, columns, charts, export formats |
| `GET /{id}/filters/{filter}/options?q=&limit=` | options of enum, entity, query and static filters |
| `POST /{id}/run` | body `{filters, page, size, sort, direction}` returns `{columns, rows, total, page, size, truncated, durationMs, charts}` |
| `POST /{id}/export?format=xlsx|csv|pdf` | file download; header `X-Report-Truncated: true` when the row limit was hit |
Filter values by name: text, number, boolean, date `yyyy-MM-dd`, date time `yyyy-MM-dd HH:mm:ss`, time `HH:mm:ss`, enum name or entity id. Charts use the Chart.js structure. CSV cells starting with `=`, `+`, `-`, `@` are prefixed with `'`. The older `/api/reports/{group}/{endpoint}` still works for integrations. Vue: `@dynamia-tools/reports-sdk` and `reports-vue` (list, viewer, designer tools, dashboard renderer).

## Extension points (api module)
- `EntityFilterProvider` (`getEntityClassName`, `getName`): publish an entity so report filters can offer it. **Only entities published this way are available** to entity filters.
- `EnumFilterProvider<T>` (`getEnumClassName`, `getValues`, `getName`): publish an enum for filters.
- `ReportGlobalParameterProvider` (`Map<String,Object> getParams()`): values available to every report query (for example the current user or account).
- `ReportAccessPolicy` bean: extra rules for who sees and runs a report (all policies must allow). The default (`RolesReportAccessPolicy`) checks `Report.accessRoles` with `isUserInRole`; a report with roles is denied when there is no request to evaluate them.
- `ReportDesignerPolicy` bean, or `dynamia.reports.designer-roles`: who may use the designer API.

## Queries and filters
- One `SELECT` / `WITH` statement (JPQL: `select`/`from`). Writes, DDL, `;` and executable comments are rejected when saving and when running; SQL runs on a read-only connection.
- Filter conditions use `:name` placeholders, are inserted at the `<FILTERS>` marker, or before the first top-level `GROUP BY` / `ORDER BY` / `LIMIT`. Values are always bound, never concatenated.

## Configuration
`dynamia.reports.ui` (`vue` default or `zk`), `dynamia.reports.max-rows` (100000), `dynamia.reports.query-timeout` (60 s; a report can override), `dynamia.reports.preview-limit`, `dynamia.reports.designer-roles` (empty means nobody), `dynamia.reports.allowed-drivers` (default MySQL, MariaDB, PostgreSQL, Oracle, SQL Server), `dynamia.reports.encryption-key` (AES-256-GCM for datasource passwords; set before first use and never change).

## Designer API (`/apps/api/reports/design`)
`GET /info`, `POST /preview`, `GET /{id}/definition`, `POST /import` (the imported report is inactive and has no datasource), `POST /datasources/{id}/test`. Closed unless the user is a designer.

## Dashboard widget
In a dashboard descriptor: `widget: report`, `report: <name or id>`, optional `group`, `display: table|chart|kpi`, `chart` (index or title), `filters.<name>` defaults, and for KPI `value`, `aggregate` (first, sum, avg, min, max, count), `unit`. It runs through the same service, so scoping, policies and limits apply.

## Do / don't
- Treat report queries as untrusted input from users: keep the read-only checks, a low `max-rows`, and a restricted designer role.
- Publish enums and entities through providers instead of hard-coding options in queries.
- Large exports: stream, respect `truncated`, and warn the user.
- Don't give a report access to another account's data: use account parameters through a `ReportGlobalParameterProvider`, and test with two accounts.
