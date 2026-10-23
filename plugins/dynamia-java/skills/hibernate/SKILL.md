---
name: hibernate
description: JPA and Hibernate 7 practices - entity mapping, fetch strategies, N+1, lazy loading outside a transaction, equals and hashCode, transactions, batching, projections, locking, multi-tenancy with @TenantId - and Hibernate 6 to 7 migration. Use when writing or reviewing entities, repositories or queries, fixing LazyInitializationException or slow queries, or upgrading Hibernate.
argument-hint: "[entity or query]"
---

# dynamia-java:hibernate

Hibernate 7 implements Jakarta Persistence 3.2 and runs under Spring Boot 4 (Hibernate 7.2 in Boot 4.0; the local Maven repository also holds 7.4). Version-specific changes: `references/hibernate7.md`.

## Mapping
- Entities are classes (not records) with a no-arg constructor, a stable id, and `@Version` where concurrent updates matter.
- Associations **lazy by default**: `@ManyToOne(fetch = LAZY)` (the JPA default for to-one is eager), `@OneToMany` lazy. Map the owning side correctly (`mappedBy` on the inverse), keep both sides in sync with helper methods.
- Enums as `@Enumerated(EnumType.STRING)`; time as `java.time` types (no `@Temporal`); money as `BigDecimal` with `precision`/`scale`.
- `equals`/`hashCode`: based on the business key or on the id **only when set**, safe with proxies (compare through `Hibernate.getClass` or an id accessor); never on mutable lazy collections; never `lombok @Data` on entities.
- `@Table`/`@Index` for indexes you rely on; the schema is managed by migrations (Flyway/Liquibase), `ddl-auto=validate` or `none` in production, never `update`.
- IDs: `SEQUENCE` with an explicit `@SequenceGenerator` (Hibernate 7 requires the pairing), or UUIDs with `@UuidGenerator`.

## Queries and fetching
- **N+1** is the default failure: loading a list then touching a lazy association per row. Fix with `join fetch` in the query, an `@EntityGraph`, batch fetching (`@BatchSize`), or a **projection** that selects only what the screen needs (records/DTOs, interface projections).
- Don't `join fetch` two collections in one query (cartesian product / `MultipleBagFetchException`): fetch one, batch the other.
- Pagination with collections fetch joins is done in memory: paginate ids first, then fetch.
- `createQuery` in Hibernate 7 rejects ambiguous queries: give an explicit select list or result class.
- Read-only queries: `@Transactional(readOnly = true)`; for bulk reads/writes consider `StatelessSession` and `insertMultiple`/`updateMultiple`/`deleteMultiple` (Hibernate 7).
- Never build JPQL/SQL by string concatenation with user input; use parameters. Native SQL only when needed and tested on the real database.

## Transactions
- Open at the **service** layer, short, around the database work only; never around remote calls or user interaction.
- Pitfalls: self-invocation (`this.method()`) skips the proxy; `@Transactional` on private/package methods of proxied classes does nothing; checked exceptions do not roll back unless `rollbackFor`; catching an exception inside the transaction hides the failure and the commit still happens; `REQUIRES_NEW` opens another connection and sees only committed data.
- `LazyInitializationException` means you touched a lazy association after the session closed. Fix by loading what you need **inside** the transaction (fetch join, entity graph, explicit initialize, projection) and returning DTOs. Do not hide it with `spring.jpa.open-in-view=true` or `enable_lazy_load_no_trans`.
- Detached entities: Hibernate 7 throws if you `refresh`/`lock` a detached entity and if persist/flush cascades to a detached instance: `merge` first and use the managed copy.

## Concurrency and consistency
Optimistic locking (`@Version`) by default; pessimistic locks (`LockModeType.PESSIMISTIC_WRITE`, with timeouts) for scarce resources; idempotency keys for retried writes; unique constraints in the database as the last line of defense.

## Multi-tenancy
`@TenantId` on the discriminator column filters queries, loads and bulk statements, and sets the value on persist; a `CurrentTenantIdentifierResolver` supplies the tenant when the session opens. Native SQL is not filtered. Details in the Dynamia Platform SaaS reference: if `dynamia-platform` is installed (skills listed as `/dynamia-platform:*`) see `/dynamia-platform:backend` `references/saas-tenancy.md`; otherwise suggest `/plugin install dynamia-platform@dynamia-tools` for Dynamia projects.

## Review checklist
- [ ] Every to-many and to-one is lazy; list endpoints use projections or fetch plans; no N+1 (check SQL logs or a statement counter in tests).
- [ ] `equals`/`hashCode` proxy-safe; no `@Data` on entities; no entity in API responses.
- [ ] Transactions at service level, short; no lazy access after commit; `rollbackFor` where checked exceptions occur.
- [ ] Indexes for filters and joins used by real queries; migrations reviewed; `ddl-auto` safe.
- [ ] Queries parameterized; bulk operations bounded; large reads streamed or paged.
- [ ] Tests run against the real database engine for native SQL and locking.

End with one line: Hibernate version assumed, queries/SQL checked, what was not run against a real database.
