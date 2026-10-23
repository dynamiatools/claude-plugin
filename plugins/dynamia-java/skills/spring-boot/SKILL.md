---
name: spring-boot
description: Spring Boot 4 and Spring Framework 7 practices and migration - configuration, injection, transactions, REST, Jackson 3, testing, virtual threads, observability - for building and upgrading applications. Use when writing or reviewing Spring Boot code, configuring an application, writing Spring tests, or moving from Boot 3 to Boot 4.
argument-hint: "[file or topic]"
---

# dynamia-java:spring-boot

Check the version first (`spring-boot-dependencies` / parent in the `pom.xml`; the Dynamia framework uses Boot 4.1.x, the ERP 4.0.x on Java 25). Boot 4 means Spring Framework 7, Spring Security 7, Jakarta EE 11 and Jackson 3; details in `references/boot4.md`.

## Practices
- **Constructor injection** (single constructor, no `@Autowired`); no field injection; depend on interfaces you own. `final` fields.
- **Configuration**: `@ConfigurationProperties` on a `record` with validation (`@Validated`, `jakarta.validation`), one prefix per area; secrets from the environment or a vault, never committed; profiles for environments, not for feature flags.
- **Layers**: controller (HTTP, validation, mapping) → service (business rules, transactions) → repository. No business logic in controllers or entities' setters; no entities in API responses (map to records/DTOs).
- **Transactions**: `@Transactional` on service methods (public, called from another bean); read-only for queries; know the pitfalls: self-invocation bypasses the proxy, checked exceptions do not roll back by default (`rollbackFor`), long transactions around remote calls, lazy loading after the transaction ends. See `dynamia-java:hibernate`.
- **REST**: `@RestController`, validation on request records, errors as RFC 9457 `ProblemDetail` through `@RestControllerAdvice`, proper status codes, pagination for lists, idempotent PUT/DELETE. HTTP clients: `RestClient` (blocking) or declarative `@HttpExchange` interfaces (auto-configured in Boot 4); set connect and read timeouts.
- **JSON**: Jackson 3 (`tools.jackson`) in Boot 4; define a `JsonMapper` bean/customizer, not an `ObjectMapper`.
- **Concurrency**: `spring.threads.virtual.enabled=true` for blocking workloads; async with explicit executors; see `dynamia-java:concurrency`.
- **Observability**: Actuator health (liveness/readiness probes are on by default in Boot 4), metrics, structured logs with correlation id; `spring-boot-starter-opentelemetry` for OTLP. Don't expose sensitive actuator endpoints publicly.
- **Security**: Spring Security 7 filter chains per audience, CSRF on for browser sessions, stateless for token APIs, method security for authorization, password hashing with the delegating encoder, no secrets in logs.
- **Startup and config hygiene**: `spring.jpa.open-in-view=false`, fail fast on missing required config, no `System.out`, no `@SuppressWarnings` to hide problems.

## Testing
- Unit tests without Spring wherever possible (plain JUnit 5 + Mockito).
- Slices: `@WebMvcTest`, `@DataJpaTest`; full context `@SpringBootTest` sparingly. Boot 4: `@MockitoBean`/`@MockitoSpyBean` replace `@MockBean`/`@SpyBean`; add `@AutoConfigureMockMvc` explicitly; `RestTestClient` is new; each technology has a `spring-boot-starter-<tech>-test`.
- Real databases with Testcontainers (2.x in Boot 4) for SQL that H2 does not reproduce.
- Assert behavior and HTTP contracts, not implementation.

## Optional pointers
For Dynamia Platform applications (OSIV off through `dynamia.app.open-persistence-in-view`, `CrudService`, tenants), see `/dynamia-platform:backend` if `dynamia-platform` is installed; otherwise suggest `/plugin install dynamia-platform@dynamia-tools`. For upgrades see `dynamia-java:upgrade`.

End with one line: Boot version assumed, what ran (build, tests), what was not verified.
