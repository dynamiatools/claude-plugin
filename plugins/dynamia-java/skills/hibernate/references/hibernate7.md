# Hibernate ORM 7.0 migration points (read 2026-10-23 from the official 7.0 migration guide)

**Baseline**: Java 17+, Jakarta Persistence 3.2 (type parameters in Criteria and Entity Graph APIs changed). `Transaction#getTimeout` returns `Integer` (beware unboxing `NullPointerException`). Vibur, Proxool and UCP pools are dropped (use HikariCP or Agroal); entity scanning needs `hibernate-scan-jandex`; the annotation processor is `hibernate-processor` (replaces `hibernate-jpamodelgen`).

**Removed or replaced Session API**: `load` to `getReference`; `save`/`update`/`saveOrUpdate` to `persist`/`merge`; `delete` to `remove`; `get` deprecated for `find`; `CascadeType.SAVE_UPDATE`/`DELETE` removed (use `PERSIST`, `MERGE`, `REMOVE`); `LockOptions` deprecated (pass `LockMode` and `Timeouts`); `Query#setOrder` removed.

**Behavior changes**
- Persisting or flushing with a cascade to a **detached** instance throws `EntityExistsException`: `merge()` first and keep the managed copy.
- `refresh`/`lock` on a detached entity throws `IllegalArgumentException` (`hibernate.allow_refresh_detached_entity` removed).
- `PERSIST` cascade is no longer implicit for `@Id`/`@MapsId` associations: declare it.
- `createQuery` without a result type rejects ambiguous queries (add a select list, a result class or the alias `this`).
- Criteria by string no longer finds subtype attributes: use `treat()`; HQL still applies implicit treats.
- Native queries return `java.time` types by default (`hibernate.query.native.prefer_jdbc_datetime_types=true` restores `java.sql`).
- Bulk update/delete on **immutable** entities throws by default (`hibernate.query.immutable_entity_update_query_handling_mode=allow` restores).
- Stricter mapping validation: mixed attribute types, misplaced annotations (column annotation on a getter in field access), `SEQUENCE` without `@SequenceGenerator`, `TABLE` without `@TableGenerator`, bean-style names like `isDefault()` on a property, converters combined with `@Id`/`@Version`/`@Enumerated`/associations (use `@Convert(disableConversion = true)` for auto-applied ones).
- `StatelessSession` uses the second-level cache by default and ignores `hibernate.jdbc.batch_size` (use `setJdbcBatchSize()` or `insertMultiple`/`updateMultiple`/`deleteMultiple`).

**Annotation replacements**: `@Where`/`@WhereJoinTable` to `@SQLRestriction`/`@SQLJoinTableRestriction`; `@OrderBy` (Hibernate) to `@SQLOrder` or JPA `@OrderBy`; `@Proxy`, `@LazyToOne`, `@LazyCollection`, `@Persister`, `@Loader`, `@GeneratorType` removed; `@Target` to `@TargetEmbeddable`; `@Cache#include` to `includeLazy`.

**Schema effects** (check before deploying): Oracle `float`/`double` map to `binary_float`/`binary_double`; default timestamp precision 9 (Oracle) and 7 (SQL Server); basic arrays use `XML_ARRAY` or `JSON_ARRAY` on some databases (data must be re-saved); `char`/`Character` default to `varchar(1)`; the XML format mapper changed its collection format.

**SPI**: `Configurable#configure` takes `GeneratorCreationContext` (prefer `@IdGeneratorType`); `Interceptor` has default methods and `EmptyInterceptor` is gone; `UserType` `nullSafeGet`/`nullSafeSet` signatures changed; JFR events use `EventMonitor`/`DiagnosticEvent`. Maven plugin artifact: `org.hibernate.orm:hibernate-maven-plugin`.

**Not in that guide**: `@TenantId`, `@Filter`, default batch sizes and fetch defaults. Read the "What's New" page or the user guide of the exact version in use (7.2 with Boot 4.0).
