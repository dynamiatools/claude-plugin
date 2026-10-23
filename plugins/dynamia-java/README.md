# dynamia-java

Modern Java 25 and Spring Boot 4 for Claude Code. Six small skills, no hooks, no scripts. Versions and migration facts were read from the official sources (openjdk.org, the Spring Boot wiki, the Hibernate 7 migration guide) on 2026-10-23.

| Skill | Use it to |
|---|---|
| `modern-java` | Write and modernize Java with records, sealed types, pattern matching, scoped values; know what is final or preview in Java 21 to 25 |
| `concurrency` | Virtual threads, scoped values vs `ThreadLocal`, executors, thread-safety review, context across threads |
| `spring-boot` | Spring Boot 4 practices, Jackson 3, testing (`@MockitoBean`, slices), virtual threads, observability, Boot 3 to 4 notes |
| `hibernate` | JPA and Hibernate 7: mapping, fetching and N+1, transactions, `LazyInitializationException`, `@TenantId`, 6 to 7 migration |
| `upgrade` | Upgrade the JDK, Boot, Hibernate and dependencies in small verified steps; Maven hygiene |
| `review` | Java code review checklist: correctness, errors, resources, concurrency, persistence, security |

Pointers to `dynamia-platform` (Dynamia-specific helpers) are optional: they apply only if that plugin is installed, otherwise the skills suggest installing it once.

Install:

```
/plugin marketplace add dynamiatools/claude-plugins
/plugin install dynamia-java@dynamia-tools
```
