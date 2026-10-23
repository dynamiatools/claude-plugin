# Kotlin versions and what is stable

Read on 2026-10-23 from kotlinlang.org (releases, What's new in 2.3 and 2.4).

## Releases
2.4.21 (bug fix, 2026-10-08) is the latest; the 2.4 line is supported until 2027-12-03. 2.3.21 (2026-04-23) is the latest of 2.3. Cadence since 2.0: a language release (2.x.0) about every six months, a tooling release (2.x.20) about three months later, then bug-fix releases. 2.5.0 is planned for December 2026 and 2.5.20 for March 2027.

## Kotlin 2.3 (JVM backend relevant)
- Stable: nested type aliases; data-flow-based exhaustiveness checks for `when`; `return` in expression bodies with explicit return types is on by default.
- **Stable standard library: `kotlin.time.Clock` and `kotlin.time.Instant`.**
- Experimental: unused return value checker (`-Xreturn-value-checker=check|full`, `@MustUseReturnValues`, `@IgnorableReturnValue`, `val _ = ...`); explicit backing fields (`-Xexplicit-backing-fields`); UUID API (`@OptIn(ExperimentalUuidApi::class)`, `Uuid.generateV4()`, `generateV7()`).
- JVM: the compiler can generate **Java 25** bytecode.
- Gradle 7.6.3 to 9.0.0; Maven compiler flags go in `kotlin-maven-plugin` `<args>`. Ant support removed; `-language-version=1.8` dropped.

## Kotlin 2.4
- **Stable language features**: context parameters (except context arguments and callable references); explicit backing fields; `@all` meta-target for properties; new use-site annotation target defaults.
- Experimental: explicit context arguments (`-Xexplicit-context-arguments`), collection literals (`-Xcollection-literals`), intrinsic constant evaluation, `returnsResultOf()` contract, `@IntroducedAt`, map fallback functions.
- Stdlib: `kotlin.uuid.Uuid` stable (V4/V7 generation still experimental); sorted-order checks stable.
- JVM: Java 26 bytecode; annotations in metadata by default.
- **K1 compiler removed** (`-language-version=1.9` unsupported); `KotlinScriptMojo` Maven plugin removed.
- Gradle 7.6.3 to 9.5.0; default module names changed to `{group}:{project_name}` (set `moduleName` to keep the old JVM name).
- Maven: with `<extensions>true</extensions>` the plugin derives `jvmTarget` from `maven.compiler.release`; Maven Toolchains supported (kapt ignores them, KT-79897).

## Spring Boot 4 and Kotlin
Boot 4 needs Kotlin 2.2 or later and manages the Kotlin version (Maven property `kotlin.version`; Gradle plugin alignment). Recommended compiler flag: `-Xannotation-default-target=param-property`.

## Practical notes
- A project-wide `-opt-in=kotlin.time.ExperimentalTime` set while `Instant`/`Clock` were experimental may no longer be needed on 2.3 or later; remove it only if the build stays clean, and keep any opt-in a library still demands in **one** place (the compiler options), not as annotations spread across files.
