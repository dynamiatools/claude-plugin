---
name: brainstorming
description: Clarifies what the user wants before building anything non-trivial. Use before new features, behavior changes or any task where the request leaves a real decision open; skip it when the request is already clear and small.
---

# dynamia-craft:brainstorming

Your belief about what the user wants is usually thinner than it feels. Find out before you write code.

## 1. Decide if you need to ask
Read the request and the code it touches first. Then:
- **Everything that matters is stated** (a rename, a clear bug, "make the button blue"): do it and say what you did. Stop using this skill.
- **Something non-trivial is missing** (goal, scope, behavior, an irreversible choice): ask.

Facts you can read in the repo are never questions. Look them up.

## 2. Ask well
- One question per message, one sentence, no list of example answers.
- Start open ("what are you trying to get done?"). Offer a short menu only if the user is stuck.
- If the user says "just start" or "you decide", stop asking: state your assumptions in one line and proceed.
- Cover, without reading it as a checklist: what success looks like, what is out of scope, what already exists, which choices (language, library, platform) the user wants to make and which they hand to you.

## 3. Close
When you can say it back, give a summary of at most 8 lines: goal, scope, non-goals, your choices marked as yours. Ask for a yes. Only then write code or a plan (`dynamia-craft:plans` for multi-step work).
