# dynamia-test

Testing for JVM and web projects in Claude Code: five small skills, no hooks, no scripts. Tool versions and behavior were read from the official sources (JUnit 6 release notes, JaCoCo changelog, Vitest and Playwright docs) on 2026-10-23.

| Skill | Use it to |
|---|---|
| `strategy` | Decide what to test and at which level, write a test plan, review tests (determinism, mocks, smells) |
| `jvm` | JUnit 6, AssertJ, Mockito 5, Spring Boot 4 test slices, Testcontainers, Maven and Gradle test setup, Kotlin tests |
| `frontend` | Vitest and Playwright for Vue and TypeScript apps: selectors, mocking, auth, visual and accessibility checks |
| `triage` | Diagnose failing, flaky or slow tests: classify the cause, reproduce, isolate, fix |
| `quality` | JaCoCo coverage, mutation testing, CI gates, and reading the numbers honestly |

Pointers to `dynamia-craft` (TDD), `dynamia-platform` (testing Dynamia code), `dynamia-java`, `dynamia-kotlin`, `dynamia-ui` and `dynamia` (test-triage agent) are optional: they apply only if those plugins are installed; otherwise the skills suggest installing them once.

Install:

```
/plugin marketplace add dynamiatools/claude-plugins
/plugin install dynamia-test@dynamia-tools
```
