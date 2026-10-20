---
name: debugging
description: Finds the root cause of a bug, failing test, build error or unexpected behavior before proposing a fix. Use at the start of any debugging, especially when the cause seems obvious or a first fix already failed.
---

# dynamia-craft:debugging

No fix without a root cause. A symptom fix is a failure that comes back later.

1. **Read the evidence.** The whole error and stack trace: file, line, code. Do not skim.
2. **Reproduce.** Find the exact steps or command. If it is not reproducible, gather more data; do not guess.
3. **Check what changed.** `git diff`, recent commits, dependencies, config, environment.
4. **Trace to the source.** Follow the bad value backwards through the callers until you find where it first goes wrong. In a multi-component flow (CI, build, service, database) log what enters and leaves each boundary once, then see where it breaks.
5. **Compare with working code.** Find a similar case that works and list every difference.
6. **State one hypothesis** ("X is the cause because Y") and test it with the smallest change. One variable at a time.
7. **Fix at the source,** add a test that fails without the fix, and run the original reproduction.

If three fixes failed, stop: the model of the problem is wrong, or the design is. Tell the user what you learned and ask.

Report: cause, evidence, fix, and the command that proves it.
