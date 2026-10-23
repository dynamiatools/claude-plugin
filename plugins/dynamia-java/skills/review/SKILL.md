---
name: review
description: Reviews Java code for correctness, API design, error handling, null-safety, resource management, concurrency, performance and security, and reports findings with file and line. Use when asked to review a Java change, class or module, before a commit or pull request, or to audit Java code for bugs and risks.
argument-hint: "[path or diff]"
---

# dynamia-java:review

Review the change the user names (a diff, files, a package); read the surrounding code and the callers of what changed before judging. Report only what you can point to. This complements the general `code-review` skill with Java specifics.

## What to check (in priority order)
1. **Correctness**: off-by-one, wrong operator, integer overflow (`int` money or sizes), `==` on strings or boxed values, `equals`/`hashCode` mismatch, mutating a collection while iterating, `BigDecimal` compared with `equals` (scale) instead of `compareTo`, floating point for money, time zones and `java.time` misuse, locale-sensitive `toUpperCase`/`format` (use `Locale.ROOT` for machine text).
2. **Null and optionals**: dereference of values that can be null (map gets, query results, `Optional.get()`), `Optional` in fields or parameters, returning `null` for collections.
3. **Errors**: swallowed exceptions, catch-all `Exception`, log-and-rethrow, losing the cause, exceptions for control flow, `finally` that returns, `InterruptedException` ignored.
4. **Resources**: streams, connections, readers not closed (try-with-resources), unbounded reads, temp files left behind.
5. **Concurrency**: shared mutable state, check-then-act, non-thread-safe classes shared (`SimpleDateFormat`, `HashMap`), context lost across threads, blocking calls without timeouts (`dynamia-java:concurrency`).
6. **Persistence**: N+1, lazy access after commit, entity equality/hash, long transactions, SQL by concatenation (`dynamia-java:hibernate`).
7. **Security**: injection (SQL/JPQL/command/LDAP), unsafe deserialization (`ObjectInputStream`, polymorphic JSON typing), XXE in XML parsers, path traversal, SSRF in outbound calls, secrets in code or logs, weak randomness (`Random` for tokens, use `SecureRandom`), missing authorization (only authentication), user data in log messages.
8. **API and design**: public surface minimal, immutability where possible, meaningful names, no boolean flag parameters that switch behavior, no god classes, packages cohesive, no leaking of internal types (entities in REST responses).
9. **Performance**: work inside loops (queries, regex compile, repeated string concatenation), unnecessary boxing in hot paths, loading everything to memory, streams that hide O(n²).
10. **Tests**: new behavior without a test; tests that assert nothing or only implementation; time and randomness not controlled.

## Report
Group by severity: **Bug / security** (will misbehave or be exploitable), **Risk** (works now, fails under conditions), **Improvement**. One line each: `file:line`, the problem, the fix. Then "Not verified" (what needs running, profiling or a real database) and, when asked, apply the fixes in small steps with tests. No praise filler, no restating the diff; if nothing is wrong, say so.

End with one line: what was reviewed, what was not run.
