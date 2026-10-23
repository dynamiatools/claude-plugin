---
name: build
description: Gradle Kotlin DSL and Maven setups for Kotlin on the JVM and Kotlin version upgrades - version catalogs, JVM toolchains, compiler options and opt-ins, plugin compatibility, mixed Java and Kotlin, and moving between Kotlin 2.2, 2.3 and 2.4. Use when creating or fixing a Kotlin build, bumping Kotlin, Gradle or JDK versions, or debugging compiler plugin or classpath problems.
argument-hint: "[from] [to]"
---

# dynamia-kotlin:build

## Gradle (Kotlin DSL)
- **Version catalog** `gradle/libs.versions.toml` for every version (Kotlin, coroutines, serialization, Ktor, Exposed, test libs) and plugin aliases; subprojects use `libs.*` and declare no literal versions.
- **Toolchain**: `kotlin { jvmToolchain(25) }` (Kotlin 2.3 can emit Java 25 bytecode; 2.4 also Java 26); the same JDK in CI and in the container image.
- **Shared conventions** in the root or a convention plugin: group/version, `repositories`, `useJUnitPlatform()` on `Test` tasks, one place for compiler options (`optIn`, `allWarningsAsErrors` when the build is clean, `-Xannotation-default-target=param-property` for Spring).
- **Plugins**: `kotlin("jvm")`, `kotlin("plugin.serialization")` for kotlinx.serialization, `kotlin("plugin.spring")` and `kotlin("plugin.jpa")` for Spring/JPA, KSP/kapt only when a processor needs it (kapt ignores Maven toolchains, KT-79897).
- Compatibility: Kotlin 2.3 works with Gradle 7.6.3 to 9.0.0; Kotlin 2.4 with 7.6.3 to 9.5.0 (newer Gradle works with warnings). Use the Gradle wrapper and commit it.
- Speed: configuration cache, build cache, parallel, `kotlin.incremental=true`; don't disable them to hide a bug.
- Don't mix `kotlin-dsl` with `kotlin("jvm")` in the same project without checking the compatibility warning.

## Maven
- Parent/BOM `spring-boot-dependencies` manages the Kotlin version through `kotlin.version`; set that property once in the parent (as Dynamia's Maven projects do).
- `kotlin-maven-plugin` with `<sourceDirectory>src/main/kotlin</sourceDirectory>` and `<testSourceDirectory>src/test/kotlin</testSourceDirectory>`; compiler plugins `spring`/`jpa`/`kotlinx-serialization`; flags under `<args>` (for example `<arg>-Xannotation-default-target=param-property</arg>`).
- Kotlin 2.4: with `<extensions>true</extensions>` the plugin takes `jvmTarget` from `maven.compiler.release`, and supports Maven Toolchains.
- Order matters in mixed projects: Kotlin compiles before Java so Java sees Kotlin classes; Kotlin sees Java sources too.

## Upgrading Kotlin (follow `dynamia-java:upgrade` for the general procedure if installed)
1. Read the "What's new" and the compatibility guide of every hop (`idioms/references/versions.md` has the 2.3 and 2.4 highlights). Hop one language release at a time (2.2 to 2.3 to 2.4).
2. Bump Kotlin only (and its Gradle/Maven plugin); build; fix; run tests; commit. Then bump libraries that need it (Exposed 1.0 needs Kotlin 2.2+, Spring Boot 4 needs 2.2+, kotlinx-datetime needs stdlib 2.1.20+).
3. **2.4 breaking items**: K1 compiler removed (`-language-version=1.9` unsupported); `KotlinScriptMojo` removed; default module names changed; check compiler plugins and annotation processors for 2.4 builds.
4. **2.3 items**: Ant removed; language versions older than 2.0 unsupported except 1.9 on the JVM.
5. New experimental flags (`-Xreturn-value-checker`, `-Xexplicit-context-arguments`, `-Xcollection-literals`) only on purpose and documented; they can change or produce pre-release binaries.
6. Revisit old opt-ins and workarounds after the bump (for example `kotlin.time` opt-ins now that `Clock`/`Instant` are stable in 2.3) and remove what the build no longer needs.

## Checks before saying a build works
`./gradlew build` (or `mvn -B -ntp verify`) from a clean checkout, tests green, the application starts, warnings reviewed. Say which of these ran.

End with one line: versions before/after, commands run and their result, what was not tested.
