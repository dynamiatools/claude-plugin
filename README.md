# Dynamia Tools: Claude Code plugins

The plugins we use every day at [Dynamia](https://dynamiasoluciones.com) to work with [Claude Code](https://claude.com/claude-code), free under MIT.

```
/plugin marketplace add dynamiatools/claude-plugins
/plugin install <plugin>@dynamia-tools
```

| Plugin | What it is | Install |
|---|---|---|
| [`dynamia`](plugins/dynamia) | Safe, token-cheap work across several repos: 19 skills, 4 helper agents, guard hooks, the `ms-workspace` tool and a dev-env panel | `/plugin install dynamia@dynamia-tools` |
| [`dynamia-craft`](plugins/dynamia-craft) | Working discipline: ask before building, find the root cause before fixing, plan in small steps, answer clearly. 6 skills, no hooks | `/plugin install dynamia-craft@dynamia-tools` |

From a terminal (for example in a Remote Control session, where `/plugin` does not run): `claude plugin marketplace add dynamiatools/claude-plugins` and `claude plugin install dynamia@dynamia-tools` (or `dynamia-craft@dynamia-tools`).

Each plugin lives in `plugins/<name>` with its own README, tests and version. The marketplace is `.claude-plugin/marketplace.json`.

## License

[MIT](LICENSE), Copyright (c) 2026 Dynamia Soluciones.
