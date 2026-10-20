---
name: plans
description: Turns a clear spec into an implementation plan of small steps, each with a checkable result. Use for multi-step or multi-file work after the goal is agreed, before editing code.
---

# dynamia-craft:plans

Use after the goal is clear (`dynamia-craft:brainstorming` if it is not). Keep the plan short enough to read in a minute.

## Write
1. **Goal** in one sentence, and what is out of scope.
2. **Files**: which ones change or get created and what each is responsible for. Follow the patterns already in the repo.
3. **Steps**: the smallest units that end in something testable. Each step names the files, the names and signatures you decided, and the command that proves it (test, build, the command itself).
4. **Order** so that every step leaves the repo working, and each can be committed alone.
5. **Risks and open questions** at the end. If one blocks the work, ask now.

Do not plan what the code already has (search first), and do not add features nobody asked for.

## Then
Show the plan and wait for approval. Execute step by step, run each step's check, and tick it off. If reality contradicts the plan, stop and say so before deviating.
