# dynamia-kotlin

Kotlin for backend work: six small skills, no hooks, no scripts. Written from the Kotlin, Spring Boot, Exposed and Ktor official documentation (read on 2026-10-23) and from how Dynamia's own Kotlin code is built (Kotlin 2.3.x, JDK 25 toolchain, Gradle Kotlin DSL or Maven, Spring Boot 4 or Ktor).

| Skill | Use it to |
|---|---|
| `idioms` | Write idiomatic Kotlin, handle Java interop, know what is stable in Kotlin 2.3 and 2.4 |
| `coroutines` | Structured concurrency, dispatchers, cancellation, Flow, testing; coroutines vs virtual threads |
| `spring` | Kotlin with Spring Boot 4: compiler plugins, config properties, JPA entities, Jackson, tests |
| `ktor-exposed` | Ktor 3 services with Exposed 1.0, Flyway migrations, kotlinx.serialization, `testApplication`, Testcontainers |
| `build` | Gradle Kotlin DSL and Maven setups, toolchains, opt-ins, and Kotlin version upgrades |
| `review` | Kotlin review checklist: null-safety, coroutines, errors, interop, persistence, security |

Pointers to `dynamia-java` and `dynamia-platform` are optional: they apply only if those plugins are installed, otherwise the skills suggest installing them once.

Install:

```
/plugin marketplace add dynamiatools/claude-plugins
/plugin install dynamia-kotlin@dynamia-tools
```
