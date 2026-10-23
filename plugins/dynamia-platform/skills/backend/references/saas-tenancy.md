# SaaS multi-tenancy: tenants, `@TenantId`, `AccountTenants`

Extension `saas`, checked against framework 26.10 (`AccountTenants`, `AccountTenantIdentifierResolver`, `AccountTenantContextCapturer`, `AccountServiceAPI`, `AccountAdminAction`, `SecurityTenancy`, `docs/backend/SAAS_MULTITENANCY.md`). The framework doc still says "spike, not yet adopted" in its header; the code below is what runs.

## Model
- The **tenant is the account id** (`Long`). Rows of all accounts share the tables, split by an `accountId` column.
- Hibernate's `@TenantId` on `accountId` isolates **every** HQL/Criteria query, load by id, association and bulk statement, and assigns the tenant on persist. The older `AccountAwareCrudServiceListener` stays for entities without `@TenantId` (it only covers `CrudService` queries). **Native SQL is not filtered**: add the `accountId` condition yourself.
- Hibernate fixes the tenant **when the session opens**; it cannot change afterwards.

## Making an entity tenant-aware
- Extend a SaaS base (preferred): `BaseEntitySaaS`, `SimpleEntitySaaS`, `BaseEntityUuidSaaS`, `SimpleEntityUuidSaaS`. They declare `@NotNull @TenantId private Long accountId`.
- Or annotate your own field when the superclass cannot change:
```java
@TenantId
private Long accountId;
```
- Already annotated: the four bases, `AccountParameter`, and the security entities `User`, `Profile`, `UserProfile`, `Permission`, `UserAccessToken`. Entities of reports, email-sms and http-functions inherit it from the bases. `EntityFile` is not annotated (entity-files does not depend on SaaS).
- Behavior: persisting an entity whose `accountId` differs from the session tenant is **rejected** (`PropertyValueException`); changing `accountId` on a managed entity is ignored; `find` by id of another account's row returns `null`; bulk update/delete only touch the current tenant.
- An app without SaaS still works: with no `CurrentTenantIdentifierResolver` bean, `JpaConfigurationAdapter` registers a resolver that always answers root. An app that defines its own resolver bean replaces it.

## Which tenant is current
`AccountTenantIdentifierResolver` resolves, in order: a binding made with `AccountTenants`, the request attribute `currentAccountId`, the thread's `AccountSessionHolder`. It never touches the database (Hibernate calls it while opening a session).

**It fails closed.** When nothing resolves (startup, a background thread that lost its context) it answers `AccountTenants.NO_TENANT_ID` (`-1`), a tenant that does not exist, so nothing is visible; it logs a warning at most once a minute. Seeing every account is only possible inside an explicit `withRoot`, `runAsRoot` or `callWithRoot`.

## The main (root) tenant
- `AccountTenants.rootTenantId()` is the **root tenant**: not an account, it sees and may write every account. Default `0` (`ROOT_TENANT_ID`).
- Change it with the property `dynamia.saas.root-tenant-id`. It is a plain number on purpose (Hibernate asks while opening sessions, so it cannot be looked up in the database). It cannot be empty or `-1`; the app fails to start otherwise. Set it once, before the first session, and never change it with data in place.
- Not the same as the **system account**: `AccountServiceAPI.getSystemAccountId()` is the real administrative account (found by the name `System`, cached), the one that works on customer accounts. Root is a tenant id, the system account is an account row.
- Entities persisted under root without an `accountId` get the root tenant id.

## AccountTenants
| Method | Transaction | Use for |
|---|---|---|
| `runAs(accountId, work)` | new (`REQUIRES_NEW`, new session) | short work for one account: account initializers, administration |
| `runAsRoot(work)` | new | short work across accounts |
| `with(accountId, work)` | none, only binds | code that manages its own sessions and transactions (long jobs) |
| `withRoot(work)` | none | same, for every account |
| `callWithRoot(callable)` | none | tasks sent to executors that throw checked exceptions |
| `callBoundTo(tenantId, op)` | none | re-apply a tenant captured elsewhere (used by the capturer) |
| `forcedTenantId()` | | the tenant bound now, or `null` |
| `rootTenantId()` | | the configured root id |

```java
AccountTenants.runAs(newAccountId, () -> crudService.create(new Customer("default")));
long total = AccountTenants.runAsRoot(() -> crudService.count(Invoice.class));
```
`runAs` and `with` reject a `null` account id (use the root variants on purpose).

## ScopedValue rules
The tenant lives in a `ScopedValue`: bound only while the work runs, nested bindings shadow the outer one and are undone even on exceptions, and it never leaks to later work on a pooled thread. It is **not inherited** by threads you start (executors, virtual threads), except `StructuredTaskScope` forks. So:
- **Tasks started with `SchedulerUtil`** (or any `ObjectsContext` snapshot) carry the tenant automatically: `AccountTenantContextCapturer` captures the effective tenant (bound, request, session; never the `-1` sentinel) and re-applies it in the task.
- **Your own executor or thread**: bind inside the task (`AccountTenants.with(id, ...)`, `callWithRoot`).
- **Callbacks that run later** (dialog answers, long operations, `UIMessages.showQuestion` callbacks) must bind again; binding in `actionPerformed` does not reach them.
- **Session timing**: a method already inside `@Transactional` has its session open; `runAs` with `REQUIRES_NEW` is for starting a new one, `with` is not enough there. Wrap **before** the transactional method is entered.

## AccountServiceAPI helpers
`AccountServiceAPI.get()` (or injection) in code that must not depend on the saas core:
| Method | Meaning |
|---|---|
| `getCurrentAccountId()` / `getCurrentAccount()` | the account of the work now: bound tenant first (`runAs`/`with`, if > 0), else request attribute, session, `AccountContext` |
| `withRootIfNoAccount(work)` | runs as the current account if there is one, otherwise as root. For login lookups by username/token and startup defaults. Open its own session: never call it from inside a transactional method |
| `withAccount(accountId, work)` / `runAsAccount(accountId, runnable)` | bind another account, no transaction. For administration from another account |
| `getSystemAccountId()`, `getParentAccountId(id)`, `getAccountIdByDomain(domain)` | account lookups |
| `getParameterValue(name[, default])`, `setParameter`, `hasFeature(accountId, featureId)`, `findAccountsIdByFeature` | per-account configuration and features |
| `clearCache()`, `clearCache(id, domain)`, `initDomainCache()` | caches |
Security code uses `SecurityTenancy.withRootIfNoAccount(...)` / `runWithRootIfNoAccount(...)`, which delegate to the service (and just run the work if there is none).

## Admin actions on another account
Extend `AccountAdminAction` (api module) for actions that run from the system account on a customer account. Use `withAccount(account, ...)`, `runAsAccount(account, ...)` and the wrappers `inAccount(account, callback)` for dialog answers and confirmations:
```java
UIMessages.showQuestion("Delete " + account.getName() + "?", inAccount(account, () -> service.delete(account)));
```
`setAuthorizationRequired(true)` delegates to an `AccountAdminActionAuthorizationProvider` before running.

## Pitfalls
- Session opened before the account is resolved (an open-EM-in-view before account resolution) or in another thread gets the wrong tenant.
- A query with an explicit `accountId = X` under tenant `Y` returns nothing; use `runAs(X, ...)` or root.
- Writing for another account (new-account initializers) fails with `PropertyValueException` unless under `runAs`/root.
- Cross-account reads of tenant-aware entities (a shared template owned by the system account) need `runAs`/root.
- Login with no resolved account runs as root via `SecurityTenancy` and sees all users; with a subdomain-resolved account it sees only that account's users.
- **Account migration always runs as root** (`AccountMigrationServiceImpl`, and `ExportPipeline` rebinds it in each worker).
- Inside `runAs`, `getCurrentAccountId()` is the bound account; code that sets `accountId` on save from it creates rows for that account.
- Tests: bind the tenant explicitly (`AccountTenants.with(...)`), and add one test with no tenant to prove nothing leaks (the answer must be an empty result, not an error).

## Adopting it in an app
1. Annotate or extend a base for every entity that owns `accountId`.
2. Move initializers and cross-account jobs to `runAs`/`runAsRoot`/`with`.
3. Review native SQL and direct `EntityManager` use.
4. Review queries that pass an explicit `accountId` for another account.
5. Review async code and where sessions open relative to account resolution.
6. Wrap code that legitimately has no account in `withRoot`/`runAsRoot`/`withRootIfNoAccount`.
