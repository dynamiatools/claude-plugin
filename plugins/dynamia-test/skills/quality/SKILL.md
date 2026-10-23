---
name: quality
description: Measures and improves test quality - JaCoCo line and branch coverage, mutation testing, coverage gates in CI, test pyramid balance, flaky-test tracking and suite speed - and interprets the numbers honestly. Use when asked about code coverage, mutation testing, quality gates, whether tests are good enough, or how to set up coverage reports in Maven, Gradle or Vitest.
argument-hint: "[module or report]"
---

# dynamia-test:quality

Coverage tells you what code **ran**, not what was **checked**. Use it to find untested areas, never as a target to game. Mutation testing tells you whether tests would notice a change.

## Coverage on the JVM (JaCoCo)
- Use a JaCoCo version that supports the JDK: **0.8.14 supports Java 25**, 0.8.15 supports Java 26 (JaCoCo changelog, read 2026-10-23); older versions fail or ignore class files of newer Java.
- Maven: `jacoco-maven-plugin` with `prepare-agent` and `report` (and `check` for rules); Gradle: the `jacoco` plugin and `jacocoTestReport`. Merge unit and integration coverage deliberately; report per module and aggregate.
- Kotlin: JaCoCo has filters for Kotlin-generated code (inline functions, `when` on enums/strings, safe-call chains, suspending lambdas, serialization methods); use a recent version so those do not distort the numbers.
- Exclude only generated code, DTOs without logic and the application main; justify each exclusion in the build file.

## Coverage on the web
Vitest `--coverage` (choose the provider the project sets); Playwright e2e is not a coverage source; report statements and branches for logic-heavy modules only.

## Reading the numbers
- Look at **branch** coverage of business rules, not the overall percentage. Open the report on the files that changed.
- A high percentage with weak assertions is false comfort: check for tests that call code without asserting.
- Set gates on **new code** (diff coverage) and on critical modules (money, taxes, security, tenancy), for example "no drop below the current level" and a higher bar for those modules; avoid a single global percentage as a fix-all.
- Never lower a gate to merge without saying so in the PR.

## Mutation testing
Run it on critical, well-tested modules (pricing, tax calculation, authorization): a tool changes the code (flips a condition, removes a call) and checks that some test fails. For the JVM the common tool is **PIT (pitest)** with its JUnit 5 plugin; check pitest.org for the version that supports your JDK and JUnit 6 before adopting. Interpret survivors: each surviving mutant is a missing assertion or an equivalent mutant. It is slow: run on changed classes or nightly, not on every commit.

## Other signals
- **Flaky rate**: count tests that failed then passed on retry; keep a list, fix the top offenders (`dynamia-test:triage`).
- **Suite time**: total and per stage; fail the build on a budget for the unit stage.
- **Test levels**: ratio of unit to integration to e2e; a growing e2e share with a shrinking unit share predicts slow, flaky pipelines.
- **Escaped defects**: for each production bug, was there a test at the right level? Add it (`dynamia-test:strategy`).

## CI gates (suggested order)
1. Compile and static checks. 2. Unit tests + coverage on new code. 3. Integration tests (containers). 4. Contract tests. 5. A small e2e smoke. 6. Nightly: mutation testing on critical modules, longer e2e, dependency scans. Fail fast, publish reports as artifacts.

## Report
Numbers with their meaning (which modules, which metric, which version of the tool), the files that matter, concrete next tests to write, and what was not measured.

End with one line: tool versions, commands run, what was not measured.
