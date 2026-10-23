# Spring Boot 4.0 (read 2026-10-23 from the official release notes and migration guide on the Spring Boot wiki)

## Baseline
Java 17 minimum (projects here run Java 25). Spring Framework 7.0, Spring Security 7.0, Jakarta EE 11 (Servlet 6.1, Persistence 3.2, Validation 3.1), Tomcat 11, Jetty 12.1, Hibernate 7.2, Jackson 3. Kotlin 2.2+ and GraalVM native-image 25+ if used.

## Upgrade path
1. Move to the latest 3.5.x first and remove calls to deprecated APIs (Boot 4 deletes them).
2. Compare dependency versions between 3.5.x and 4.0.x.
3. Add `spring-boot-properties-migrator` temporarily to find renamed properties; remove it afterwards.
4. Use `spring-boot-starter-classic` and `spring-boot-starter-test-classic` as a bridge to restore the old classpath while fixing imports.

## Breaking changes that bite most
- **Modular starters**: modules are `spring-boot-<tech>` with packages `org.springframework.boot.<tech>`. `spring-boot-starter-web` is now `spring-boot-starter-webmvc`; `-aop` is `-aspectj`; Flyway and Liquibase need `spring-boot-starter-flyway` / `-liquibase`. Each tech has a `-test` starter (for example `spring-boot-starter-security-test` for `@WithMockUser`).
- **Jackson 3**: group and packages move from `com.fasterxml.jackson` to `tools.jackson` (`jackson-annotations` keeps the old one). `@JsonComponent` is `@JacksonComponent`, `@JsonMixin` is `@JacksonMixin`, `Jackson2ObjectMapperBuilderCustomizer` is `JsonMapperBuilderCustomizer`. Properties `spring.jackson.read/write.*` moved under `spring.jackson.json.read/write.*`. Define a `JsonMapper` (or `XmlMapper`) bean: an `ObjectMapper` bean no longer replaces the auto-configured mapper. Jackson 2 still works but is deprecated (`spring.jackson.use-jackson2-defaults=true`, the deprecated `spring-boot-jackson2` module).
- **Removed**: Undertow (no Servlet 6.1 support yet; use Tomcat or Jetty), Spring Retry version management (add a version or use Spring Framework's retry), `@MockBean`/`@SpyBean`, Spock integration, classic uber-jar loader, embedded executable launch scripts.
- **Testing**: `@MockitoBean`/`@MockitoSpyBean`; `@SpringBootTest` no longer configures MockMvc (add `@AutoConfigureMockMvc`); `TestRestTemplate` needs `@AutoConfigureTestRestTemplate` and `spring-boot-resttestclient`; new `RestTestClient`; the Mockito test listener is gone (use `MockitoExtension`).
- **Properties**: `spring.session.redis.*` is `spring.session.data.redis.*`; `spring.data.mongodb.*` connection settings are `spring.mongodb.*`; `management.tracing.enabled` is `management.tracing.export.enabled`; `spring.dao.exceptiontranslation.enabled` is `spring.persistence.exceptiontranslation.enabled`; liveness and readiness probes are enabled by default; DevTools live reload is off by default.
- **Persistence**: `hibernate-jpamodelgen` is replaced by `hibernate-processor`; `@EntityScan` moved to `org.springframework.boot.persistence.autoconfigure`.
- **HTTP**: `HttpMessageConverters` is deprecated in favor of `ClientHttpMessageConvertersCustomizer` and `ServerHttpMessageConvertersCustomizer`; declarative `@HttpExchange` clients are auto-configured; JDK `HttpClient`-based clients use virtual threads when `spring.threads.virtual.enabled=true`.
- **Observability**: new `spring-boot-starter-opentelemetry` for OTLP.

## Not covered here
Spring Security 7 behavior changes (read its migration notes), Spring Framework 7 details beyond the above, and null-safety with JSpecify: look them up before relying on them.
