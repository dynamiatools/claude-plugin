# dynamia-docs

Documentation for software projects in Claude Code: seven small skills, no hooks, no scripts. Standards were read from their sources on 2026-10-23: Keep a Changelog 1.1.0, Semantic Versioning 2.0.0, Conventional Commits 1.0.0, MADR 4.0.0, OpenAPI 3.2.1, Diátaxis, KDoc and Mermaid.

| Skill | Use it to |
|---|---|
| `readme` | Write or refresh a README and a docs layout (tutorial, how-to, reference, explanation) with verified commands |
| `adr` | Record architecture decisions with MADR and short design docs |
| `api-docs` | Javadoc, KDoc, TSDoc and OpenAPI documentation that says what and why |
| `changelog` | Changelogs, release notes, next version (SemVer) and commit messages (Conventional Commits) |
| `runbook` | Runbooks, deployment and rollback docs, troubleshooting, onboarding and blameless postmortems |
| `diagrams` | Mermaid diagrams: choose the type, keep them small and true |
| `audit` | Check docs against the code, keep CLAUDE.md and AGENTS.md short and accurate |

Pointers to `dynamia-craft`, `dynamia` and `dynamia-platform` are optional: they apply only if those plugins are installed; otherwise the skills suggest installing them once.

Install:

```
/plugin marketplace add dynamiatools/claude-plugins
/plugin install dynamia-docs@dynamia-tools
```
