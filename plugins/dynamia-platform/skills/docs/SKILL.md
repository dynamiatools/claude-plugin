---
name: docs
description: Reads the official Dynamia Platform documentation and package READMEs straight from the public GitHub repo dynamiatools/framework, at the tag that matches the project's version, so answers are current. Use when a Dynamia API, extension or pattern is not covered by the other dynamia-platform skills, when a signature must be verified, or when the user asks what the docs say.
---

# dynamia-platform:docs

The framework repo is public: `dynamiatools/framework` (Apache-2.0), site <https://dynamia.tools>. Read it live instead of relying on memory or copies.

## 1. Pick the ref
1. Version of the project: `${CLAUDE_PLUGIN_ROOT}/bin/dp-detect --facts` (`version=`).
2. Does tag `v<version>` exist? `gh api repos/dynamiatools/framework/git/ref/tags/v26.10.2 --jq .ref` (404 means no such tag; maintenance versions may have none).
3. If not, use the newest tag of the same `YY.MM` (`gh api repos/dynamiatools/framework/tags --jq '.[].name'`), else `main`.
4. Use `main` when the project has no version, or the user asks for the latest. **Say which ref you read**, and warn when `main` is newer than the project's version.

## 2. Read
```bash
# one file
gh api "repos/dynamiatools/framework/contents/docs/backend/DEVELOPMENT_PATTERNS.md?ref=v26.10.2" --jq .content | base64 -d
# list a folder
gh api "repos/dynamiatools/framework/contents/docs/backend?ref=main" --jq '.[].name'
# search the repo (code and docs)
gh search code --repo dynamiatools/framework "InstallAction" --limit 10
```
Without `gh`: `https://raw.githubusercontent.com/dynamiatools/framework/<ref>/<path>` with WebFetch. Read the slice you need (`| head -150`, `sed -n`), not whole 30 KB files; delegate wide reads to a cheap agent when available.

## Where things are
| Topic | Path |
|---|---|
| Overview, modules, roadmap | `README.md` |
| Architecture, core modules, patterns, extensions, advanced topics, examples | `docs/backend/{ARCHITECTURE,CORE_MODULES,DEVELOPMENT_PATTERNS,EXTENSIONS,ADVANCED_TOPICS,EXAMPLES}.md` |
| Multi-tenancy, security and sessions, navigation session | `docs/backend/{SAAS_MULTITENANCY,WEB_SECURITY_SESSIONS,NAVIGATION_SESSION}.md` |
| Separating ZK from the backend | `docs/backend/MIGRATION_ZK_SEPARATION.md` |
| Frontend: API client rules, field components, ZK inline embed, extension SDK template | `docs/frontend/*.md` |
| Actions without UI, server-driven flows | `docs/design/*.md` |
| UI model and inventory | `docs/next/dynamia-ui*.md` |
| Releases, versions, where artifacts are published | `docs/RELEASING.md` |
| npm package READMEs | `platform/packages/{sdk,ui-core,vue,microfrontend-bridge,cli}/README.md`, `extensions/*/packages/*/README.md` |
| Working example apps | `examples/demo-zk-books`, `demo-vue-books`, `demo-client-books`, `dynamia-movies` |
| Source of any class | search with `gh search code`, then read the file at the same ref |

Maintenance versions (`YY.MM.N`, N > 0) are published to GitHub Packages, not Maven Central; downloading them needs a token with `read:packages` (`docs/RELEASING.md`).

## Use
Answer from what you read and cite the path and ref (`docs/backend/EXTENSIONS.md@v26.10.2`). If the docs and the project's code disagree, the code in the project wins; say so. If the docs do not answer it, say that instead of guessing.
