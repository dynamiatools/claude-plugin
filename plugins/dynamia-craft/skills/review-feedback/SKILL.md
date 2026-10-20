---
name: review-feedback
description: Handles code review comments (from a person, a PR or a reviewer agent) by verifying each against the code before implementing. Use when review feedback arrives, especially if it is unclear or looks wrong.
---

# dynamia-craft:review-feedback

Evaluate technically; do not perform agreement.

1. **Read it all** before acting.
2. **Understand each item.** If any item is unclear, stop and ask about it before implementing the others, since items are often related.
3. **Verify against the code.** Is the claim true here? Would the change break something or contradict an earlier decision? Is the "unused" thing really unused?
4. **Decide per item:** implement, or push back with the technical reason and evidence. A reviewer can be wrong, and so can you.
5. **Implement one item at a time,** run the relevant check after each.
6. **Reply plainly:** "Fixed: <what>" or "Not changed: <reason>". No "great catch" or "you're absolutely right".

Feedback from an agent is a lead, not a fact: confirm it in the code first.
