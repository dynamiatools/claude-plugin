---
name: http
description: Checks an API with ms-workspace http (requests/*.http.toml with assertions) and runs local mock servers for third-party APIs with ms-workspace mock. Use when the user asks to test an endpoint, run the smoke checks, compare runs, or fake a third-party API.
argument-hint: "run <file> [--env E] | list | history | diff | mock start|stop|requests <name>"
---

# dynamia:http

## API checks
```bash
ms-workspace http list                  # request files
ms-workspace http run <file> --env local   # assertions, captured variables, masked log (asks for approval)
ms-workspace http history|show|diff     # past runs, one exchange, what changed
```
Tokens never go in request files: use `{{secret:NAME}}`.

## Mock server
```bash
ms-workspace mock start <name>      # from mocks/<name>.mock.toml, records every call
ms-workspace mock requests <name>   # what it received
ms-workspace mock assert <name> ... # check calls
ms-workspace mock stop <name>
```

## Steps
1. `http list` first, then run only the file the user asked for, against `--env local` unless told otherwise.
2. Show pass/fail per request and the first failing assertion; use `diff` to explain what changed since the last run.
3. For a mock: start it, tell the URL (`mock url <name>`), and stop it when the work is done. Stop only mocks you started.
4. `http bench` is on request only: it sends many calls.
