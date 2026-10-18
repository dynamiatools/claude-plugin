---
name: ms-sys
description: Compact view of the machine with ms-workspace sys (OS, CPU, memory, disk, network) plus ps ports and ps leftovers. Read-only. Use when the user asks about server load, free disk or memory, who holds a port, or what was left running.
argument-hint: "[sys | ports [--port N] | leftovers]"
---

# ms-sys

```bash
ms-workspace sys [--tools] [--json]
ms-workspace ps ports [--port N]     # who holds a port, and which batch it runs in
ms-workspace ps leftovers            # old or orphaned dev processes
ms-workspace ps [--top N] [--by cpu|mem]
```

## Steps
1. Pick the one command that answers the question; run it and give the answer plus any hint the tool printed.
2. Only the current user's processes can be acted on. Killing (`ps kill`) is not part of this skill: show the plan and let the user approve it.
3. Never kill or stop processes that you did not start.
