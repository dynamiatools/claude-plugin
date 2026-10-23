# saas

Accounts (customers), plans, payments, profiles and data isolation. Tenant isolation, `AccountTenants` and `AccountServiceAPI` are in `dynamia-platform:backend` `references/saas-tenancy.md`; this file covers the rest of the extension. Checked against `extensions/saas` (modules `api`, `core`, `jpa`, `ui`, `remote`, `migration`) in framework 26.10. The README shows old versions: use the project's `pom.xml`.

## Modules
| Module | Use |
|---|---|
| `saas.api` | what your own modules depend on: `AccountAware`, `AccountServiceAPI`, DTOs (`AccountDTO`, `AccountStatus`...), `AccountAdminAction` |
| `saas.jpa` | base entities `BaseEntitySaaS`, `SimpleEntitySaaS`, `BaseEntityUuidSaaS`, `SimpleEntityUuidSaaS` (with `@TenantId`) and `AccountParameter` |
| `saas` (core) | implementation: `Account` and friends, services, REST, request filter, status cache |
| `saas.ui` | ZK CRUDs for accounts, types (plans), profiles, payments, payment methods and providers, regions, resellers, sale channels |
| `saas.remote` | check an account's status from an external system: `RemoteAccountServiceAPI`, `OneTimeRemoteAccountServiceAPI` |
| `saas.migration` | tenant mobility: export, import, clone, backup, restore |

## Accounts
- An account is a customer; each belongs to a type (plan) and has a status (`AccountStatus`), a subdomain, optional parent account (`getParentAccountId`), payments, logs and features. The special account named `System` administers the others (`getSystemAccountId()`).
- **Subdomain per account** is the default: `customer1.myapp.com`. In DNS create a wildcard `*.myapp.com` with an A record to the server; locally add each subdomain to `/etc/hosts`. `AccountServiceAPI.getAccountIdByDomain(domain)` resolves it (cached; `clearCache`, `initDomainCache`). `AccountRequestFilter` resolves the account per request.
- Feature flags and parameters per account: `hasFeature(accountId, "id")`, `findAccountsIdByFeature`, `getParameterValue(name)`, `setParameter`. Gate paid functions with `hasFeature` and read plan limits from account/type data.
- Status checks: `getAccountStatus`, `validateAccountStatus(accountId)`, `findActivePaymentRequiredAccounts()`; `AccountStatusCache` is a simple cache of account status.
- Payments: `AccountPayment`, `AccountPaymentMethod`, `AccountPaymentProvider` (fields for a checkout URL, libraries URL and provider alias were added in 26.10); `AccountPaymentProcessor` is the extension point for a gateway.

## Make your entities per-account
Prefer extending a SaaS base (`@TenantId`). A legacy module can implement `AccountAware` with a `Long accountId` set by the SaaS `CrudServiceListener`; then isolation covers only `CrudService` queries (`saas-tenancy.md`).

## Remote
`saas.remote`: an external system (another app, a license server) asks this one whether an account is active; `RemoteAccountNotAuthenticatedException` signals a failed check. Use for licensing of separately deployed products.

## Tenant mobility (`saas.migration`)
Async jobs on virtual threads: `EXPORT` (versioned ZIP, one JSON per entity), `IMPORT`, `CLONE`, `BACKUP`, `RESTORE` (`MIGRATE` across environments is planned).
- REST (under `/api/saas/migration/jobs`): `POST export/{accountId}`, `POST import` (multipart), `POST clone`, `POST backup/{accountId}`, `POST restore/{accountId}`, `GET` list and `GET /{jobId}` status, `POST /{jobId}/cancel`, `GET /{jobId}/download`.
- Mark what not to move: `@AccountExportIgnore` on an entity, `@ExportIgnore` on a field.
- Identity strategies: `KEEP_IDS` (restore to an empty database) and `REGENERATE_IDS` (cloning in the same database); `UUID7` is planned. SPI: `IdentityMapper`, `MigrationProgressListener`, `CancellationToken`.
- Always runs as root; the result ZIP is uploaded through `EntityFileService` (local, S3 or Buckie) and the temporary file is deleted. Properties: `dynamia.saas.migration.*` (`configuration-properties.md`). Secure these endpoints: they export a whole customer.

## Do / don't
- Don't query across accounts without `runAsRoot`/`withRoot`, and don't hide that in a helper.
- Don't hard-code the system account id; read `getSystemAccountId()`.
- Don't trust a subdomain alone for authorization.
- Test with two accounts every time.
