---
name: idioms
description: Writes idiomatic Kotlin for JVM backends and handles Java interop - null safety, data and sealed classes, exhaustive when, extension and scope functions, collections, value classes, context parameters - and says which language features are stable in Kotlin 2.3 and 2.4. Use when writing, converting or reviewing Kotlin, translating Java to Kotlin, or choosing a Kotlin feature.
argument-hint: "[file or feature]"
---

# dynamia-kotlin:idioms

Check the project's Kotlin version first (`kotlin.version` in the `pom.xml`, `kotlin` in `gradle/libs.versions.toml`). The latest stable is 2.4.21 (2026-10-08); the projects here use 2.3.x. Feature status per version: `references/versions.md`.

## Idioms to prefer
| Instead of | Use |
|---|---|
| Nullable plumbing, `Optional` | Kotlin's null types: `T?`, `?.`, `?:`, `let`/`takeIf`; make the type non-null whenever the domain says so |
| Boilerplate value classes | `data class` (immutable `val` properties); `copy()` for changes; **not for JPA entities** |
| `enum` + `switch` with flags | `sealed interface` with `data class`/`object` subtypes and an exhaustive `when` expression (no `else`) |
| Static utility classes | top-level functions and extension functions (`fun String.toSlug()`), kept near their use |
| Builders with many optional args | default and named arguments; a small DSL only when it pays off |
| Verbose initialization | `val x = if (...) a else b`, `when` as an expression, `buildList`/`buildMap`/`buildString` |
| Loops that transform collections | `map`, `filter`, `groupBy`, `associate`, `fold`; `asSequence()` for large chains; a plain loop when it is clearer |
| Wrapper types for ids or units | `@JvmInline value class UserId(val value: Long)` (limited support in some frameworks: check binding and serialization) |
| `try`/`catch` returning flags | exceptions for exceptional cases; sealed result types for expected failures; `runCatching` only at boundaries (it also catches `CancellationException`) |
| Singletons with state | `object` only for stateless things; inject stateful services |
| Implicit dependencies | **context parameters** (stable in 2.4) for ambient dependencies such as a clock or a logger, sparingly |

## Rules
- **Avoid `!!`**. If you cannot prove non-null, return/throw with a message (`requireNotNull`, `checkNotNull`) or restructure.
- **Platform types** from Java (`String!`) are unchecked: annotate or convert at the boundary (`val name: String = javaCall() ?: error("...")`). JSpecify-annotated libraries (Spring) are enforced since Kotlin 2.1.
- `val` over `var`; immutable collections in public APIs (`List`, not `MutableList`); copy mutable inputs.
- Don't overuse scope functions: one per expression, nested `apply`/`also` hurts readability; name things.
- `lateinit` only for framework-injected or test-setup fields; never for domain state.
- Exhaustive `when` over sealed types and enums is the safety net: a new subtype breaks the build, which is the point.
- Public API: explicit return types; `internal` for module-private; small `Result`-style types instead of exceptions for expected outcomes.
- Strings: templates `"$name"`/`"${a + b}"`, raw strings `"""` with `trimIndent()`. Time: `java.time` or `kotlin.time` (`Clock`, `Instant` are stable since 2.3), never `Date`/`Calendar`. Money: `BigDecimal`.
- Equality: `==` is `equals`, `===` is identity; arrays in data classes compare by reference.
- Keep top-level functions and classes in files named for their content; one public class per file is not required but keep files focused.

## Java interop
- Calling Kotlin from Java: `@JvmStatic`, `@JvmOverloads`, `@JvmField`, `@Throws` for checked exceptions Java callers must see; top-level functions become `FileNameKt` (use `@file:JvmName`).
- Calling Java from Kotlin: SAM conversion for functional interfaces; nullability annotations decide nullability; Java getters appear as properties.
- Kotlin classes are `final` by default: frameworks that proxy (Spring, Hibernate) need the `kotlin-spring` / `kotlin-jpa` (all-open/no-arg) compiler plugins (`dynamia-kotlin:spring`).
- `data class` entities break JPA proxies and `equals`/`hashCode` semantics.

## Converting Java to Kotlin
1. Convert one class at a time with the IDE converter, then review: nullability, mutability, `lateinit`, getters turned into properties.
2. Keep behavior and tests green; replace patterns with idioms in a second pass.
3. Don't convert generated code or code that is about to change owner.

End with one line: Kotlin version assumed, what changed, what tests ran.
