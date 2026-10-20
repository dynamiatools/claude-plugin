---
name: tdd
description: Test-first workflow, only when the user asks for TDD or for a bugfix that needs a regression test. Write a failing test, watch it fail, write the minimum code to pass.
---

# dynamia-craft:tdd

Opt-in. For code with branches, parsers, money or security, or when the user asks. Skip for config, throwaway scripts and generated code.

1. **Red.** Write one test for one behavior, with a clear name, using real code (mocks only if unavoidable).
2. **Watch it fail.** Run it. It must fail for the right reason (feature missing), not by a typo or error. If it passes, you are testing existing behavior; fix the test.
3. **Green.** Write the smallest code that passes. No options or features the test does not need.
4. **Run everything** related; all must pass.
5. **Refactor** only while green.

For a bugfix, the test reproduces the bug first. Proof that it works: it fails without the fix and passes with it.
If you wrote the code before the test, say so, then write the test and revert the fix once to see it fail.
