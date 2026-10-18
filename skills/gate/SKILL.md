---
name: gate
description: Scans what would be sent for secrets, merge markers, huge files and debug leftovers with ms-workspace gate. Read-only. Use when the user asks to check, scan or review a batch or repo before shipping, or whether something leaks a secret.
argument-hint: "[batch]"
---

# dynamia:gate

```bash
ms-workspace gate [batch] [--json]
```

Without a batch it scans the current repo. Works in a plain repo too.

## Steps
1. Run the command and show the findings grouped as blocking (secrets, merge markers, oversized files) and warnings (debug leftovers).
2. For each blocking finding give file, line and what to do (remove, rotate the secret, move to `env_files`). Evidence is already masked: never print a full secret.
3. A deliberate false positive is silenced with `ms-gate: allow` on the line or `[gate] allow` / `ignore_paths` in `workspace.toml`; suggest it, do not apply it without asking.
4. Never bypass with `ship --skip-gate` on your own.
