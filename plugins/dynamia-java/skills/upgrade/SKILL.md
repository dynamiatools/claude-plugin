---
name: upgrade
description: Plans and runs upgrades of the Java version, Spring Boot, Hibernate and Maven dependencies in small, verifiable steps, and keeps Maven builds healthy (BOMs, dependency tree, enforcer, versions plugin, CI gates). Use when moving to a new JDK or Spring Boot major, bumping dependencies, fixing build or classpath conflicts, or auditing a pom.xml.
argument-hint: "[from] [to]"
---

# dynamia-java:upgrade

An upgrade is a series of small commits that each build and pass tests. Never mix an upgrade with a feature.

## Procedure
1. **Baseline**: record the current versions (`java -version`, `mvn -v`, `mvn -q help:evaluate -Dexpression=java.version -DforceStdout`, parent/BOM versions) and run the full build and tests. If they are red, stop: fix or record the known failures first.
2. **Read the official migration notes for every hop** (do not skip majors): Spring Boot wiki "Migration Guide" (`dynamia-java:spring-boot` `references/boot4.md`), Hibernate migration guide (`dynamia-java:hibernate` `references/hibernate7.md`), the JDK release notes and `--enable-preview` status of features (`dynamia-java:modern-java` `references/versions.md`). Hop one major at a time (Boot 3.x to latest 3.5.x first, then to 4.0).
3. **Make a list** of breaking items from those notes that apply to this code (grep the project for each: removed annotations, renamed properties, starters, packages like `com.fasterxml.jackson`, `@MockBean`, `javax.*`).
4. **Bump one thing**: the BOM/parent, or the JDK, or one library; build; fix; run tests; commit. Use bridges while migrating (`spring-boot-starter-classic`, `spring-boot-properties-migrator`) and remove them in their own commit.
5. **Check the runtime**, not only the build: start the application, hit the main endpoints, run the integration tests against the real database, read startup warnings (deprecations, JNI/Unsafe warnings on newer JDKs, "using default" messages).
6. **Performance and memory**: compare startup, memory and a representative request before/after; new JDKs change GC defaults and options.
7. **Document** in the PR: versions before/after, items changed, flags added, what was not tested.

## JDK upgrade checks
- `mvn -Dmaven.compiler.release=<n>` and fix removed or deprecated APIs; `jdeprscan` finds uses of deprecated-for-removal APIs and `jdeps` finds internal API use.
- Libraries that use `sun.misc.Unsafe`, JNI or bytecode agents may warn or fail on newer JDKs; upgrade them first. Java 24 removed the non-generational ZGC mode and permanently disabled the Security Manager.
- Container images: use a JDK image of the same vendor family for build and runtime; set memory flags explicitly if the defaults changed.

## Maven hygiene
- **One place for versions**: a parent or BOM `dependencyManagement` (import `spring-boot-dependencies` as in the Dynamia framework); child modules declare dependencies without versions. Properties for the few versions that need one.
- **Dependency tree**: `mvn dependency:tree -Dincludes=<groupId>` to find conflicts; exclude only with a comment saying why.
- **Enforcer**: `maven-enforcer-plugin` with `requireJavaVersion`, `requireMavenVersion`, `dependencyConvergence` (or `banDuplicatePomDependencyVersions`) to fail early.
- **Updates**: `mvn versions:display-dependency-updates` and `versions:display-plugin-updates` to list candidates; bump with intent, never `LATEST`/`RELEASE` or open ranges.
- **Reproducible builds**: pinned plugin versions, `project.build.outputTimestamp`, no `SNAPSHOT` in release builds.
- **Scopes**: `provided` for container APIs, `test` for test libs, `runtime` for drivers; no unused declared dependencies (`mvn dependency:analyze`).
- **Security**: scan dependencies (OWASP dependency-check or Dependabot, which the Dynamia framework uses for security updates only) and act on high severity items.
- **CI**: `mvn -B -ntp verify` on every PR; cache `~/.m2`; one JDK matrix entry for the target version; release jobs separate from snapshot jobs.
- Build commands from the project's docs beat this list; follow its `CLAUDE.md`/README first.

End with one line: versions before/after, commands run and their result, what was not tested.
