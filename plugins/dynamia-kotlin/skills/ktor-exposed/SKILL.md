---
name: ktor-exposed
description: Builds and reviews standalone Kotlin backend services with Ktor 3, Exposed 1.0, Flyway, kotlinx.serialization and Testcontainers - routing, content negotiation, status pages, authentication boundaries, database access and migrations, testing with testApplication. Use when writing or changing a Ktor service, Exposed tables or transactions, database migrations, or an Exposed 0.x to 1.0 upgrade.
argument-hint: "[file or topic]"
---

# dynamia-kotlin:ktor-exposed

Dynamia's own Kotlin services have this shape: Kotlin on a JDK 25 toolchain, Ktor server (Netty), Exposed over PostgreSQL with HikariCP, Flyway migrations, kotlinx.serialization and coroutines, Micrometer metrics, Testcontainers. Follow the repository's own `CLAUDE.md` and design docs first; this skill is the general layer.

## Service structure
- Layers: `routing` (HTTP in/out, validation, status codes) → application services (rules, transactions) → persistence (tables, queries). Domain types are plain Kotlin classes; request/response types are `@Serializable` data classes, separate from tables.
- Configure in modules: `fun Application.module()`; install plugins once (`ContentNegotiation` with `json()`, `StatusPages`, `CallLogging`, authentication); wire dependencies explicitly (constructor injection or a small DI) so tests can swap them.
- Errors: map domain exceptions to HTTP in `StatusPages` (one place), return a consistent error body, never leak stack traces or SQL; validate input at the edge (`require`, a validator) and return 4xx.
- Auth: authenticate in a plugin, authorize per route/resource (ownership, tenant), keep secrets in environment/config, constant-time comparison for secrets and signatures, no tokens in logs.
- Idempotency for payment-like POSTs (idempotency keys stored with a unique constraint), timeouts on outbound calls, retries only for idempotent operations.

## Exposed 1.0 (read from the official migration guide, 2026-10-23)
- Imports moved to `org.jetbrains.exposed.v1.<module>.*` (`core`, `jdbc`, `dao`, `javatime`, `json`...). `exposed-core` is driver-agnostic; JDBC classes (`Database`, `SchemaUtils`, `select`/`insert`/`update`, `TransactionManager`) are in `exposed-jdbc`; R2DBC in `exposed-r2dbc`. Spring Boot 4 uses `exposed-spring-boot4-starter` and `spring7-transaction`.
- Requires Kotlin 2.2 or later. `kotlinx-datetime` columns (`timestamp()`) use `kotlin.time.Instant`; the old `kotlinx.datetime.Instant` variants are the deprecated `x`-prefixed functions. `Table.uuid()` is `kotlin.uuid.Uuid`; `java.util.UUID` columns are `javaUUID()`.
- Transactions: `transaction(db) { ... }`; `newSuspendedTransaction`/`withSuspendTransaction` are deprecated, use `suspendTransaction` / `inTopLevelSuspendTransaction` (blocking JDBC) or R2DBC. The `ThreadLocal` handling was removed. `Transaction.id` is `transactionId`.
- Statements only build SQL; execution is via executables (`.toExecutable()`, `execQuery()` for raw `ResultSet`). `SqlExpressionBuilder` is deprecated: use top-level `eq`, `less`, ...; in `update { }` lambdas write `it[column] = value`.
- Upgrade from 0.61.0 first; the guide offers an optional `/migrate-to-1.0` Claude Code skill for the mechanical changes.

## Database rules
- **Schema changes only through migrations** (Flyway files, versioned, never edited after release); `SchemaUtils.create`/`createMissingTablesAndColumns` are for tests and prototypes, not production. Review the generated SQL; add indexes for real queries; unique constraints as the last defense.
- Short transactions around DB work only (no HTTP calls inside); bound query results; HikariCP pool sized to the database, with timeouts.
- Money as `DECIMAL` with explicit scale in Kotlin `BigDecimal`; timestamps as UTC `Instant`; ids as `Long`/UUID, never user-supplied sequence logic.
- Secrets and PII are not stored in clear; hash/encrypt as the design says, and do not log them.
- Test migrations on a real PostgreSQL (Testcontainers 2.x), including an upgrade from the previous release's schema.

## Testing
- Routes: `testApplication { application { module() } ; val response = client.get("/path") }` (`io.ktor:ktor-server-test-host`, `kotlin-test`); create a client with `createClient { install(ContentNegotiation) { json() } }` for JSON bodies; `externalServices { hosts(url) { ... } }` to fake third-party APIs; `environment { config = MapApplicationConfig(...) }` for config.
- Services and persistence: Testcontainers PostgreSQL, one container per test class or suite, Flyway applied before tests; use `runTest` for suspend code (`dynamia-kotlin:coroutines`).
- Don't mock Exposed; hit a real database. Keep fixtures small and explicit.

## Operations
Health endpoint public and cheap; Micrometer metrics with a Prometheus registry; structured JSON logs with request id; graceful shutdown (stop accepting, drain, close pool); config by environment variables; container image with the JDK matching the toolchain.

End with one line: Ktor/Exposed versions assumed, what ran (build, migrations, tests), what was not tested.
