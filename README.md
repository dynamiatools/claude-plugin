# Dynamia Tools: Claude Code plugins

The plugins we use every day at [Dynamia](https://dynamiasoluciones.com) to work with [Claude Code](https://claude.com/claude-code), free under MIT. Each plugin is independent: install only the ones you need.

```
/plugin marketplace add dynamiatools/claude-plugins
/plugin install <plugin>@dynamia-tools
```

From a terminal (for example in a Remote Control session, where `/plugin` does not run):

```
claude plugin marketplace add dynamiatools/claude-plugins
claude plugin install <plugin>@dynamia-tools
```

## Plugins

| Plugin | What it is | Install |
|---|---|---|
| [`dynamia`](plugins/dynamia) | Safe, token-cheap work across several repos: batches, worktrees, tests, ship. 19 skills, 4 helper agents, guard hooks, the `ms-workspace` tool and a dev-env panel | `dynamia@dynamia-tools` |
| [`dynamia-craft`](plugins/dynamia-craft) | Working discipline: ask before building, find the root cause before fixing, plan in small steps, answer clearly. 6 skills, no hooks | `dynamia-craft@dynamia-tools` |
| [`dynamia-platform`](plugins/dynamia-platform) | Work on [Dynamia Platform](https://dynamia.tools) projects: backend patterns, ZK, Vue frontend, live docs from GitHub and the `dynamia` CLI. 6 skills, 2 light hooks | `dynamia-platform@dynamia-tools` |
| [`dynamia-ui`](plugins/dynamia-ui) | UI and UX: extract, improve or create a design system; review UX and mobile, SEO, offline, performance; stack advice; a `ds-scan` tool. 8 skills, 1 agent, no hooks | `dynamia-ui@dynamia-tools` |

They do not depend on each other. Together they cover the workflow (`dynamia`), the way of working (`dynamia-craft`), the framework (`dynamia-platform`) and the interface (`dynamia-ui`).

## Repository layout

```
.claude-plugin/marketplace.json   the catalog: one entry per plugin
plugins/<name>/                   one folder per plugin, with its own README, tests, LICENSE and version
CLAUDE.md                         how we create, update and manage plugins here (read it before contributing)
```

## Contributing

Work happens on a branch and goes to `master` through a pull request. The conventions, the checklist for a new plugin and the release steps are in [CLAUDE.md](CLAUDE.md).

## License

[MIT](LICENSE), Copyright (c) 2026 Dynamia Soluciones. A plugin that adapts third-party material says so in its own `NOTICE`.
