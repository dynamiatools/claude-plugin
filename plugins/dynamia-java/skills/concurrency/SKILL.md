---
name: concurrency
description: Guides concurrent Java on JDK 21 to 25 - virtual threads, scoped values versus ThreadLocal, executors, CompletableFuture, structured concurrency preview, shared state and thread-safety review. Use when code starts threads, uses executors or async calls, shares mutable state, passes request or tenant context to other threads, or has races, deadlocks or pinning problems.
argument-hint: "[file or problem]"
---

# dynamia-java:concurrency

## Choose the tool
| Need | Use |
|---|---|
| Many blocking I/O tasks (HTTP, JDBC) | **Virtual threads**: `Executors.newVirtualThreadPerTaskExecutor()` or `Thread.ofVirtual().start(..)`; in Spring Boot `spring.threads.virtual.enabled=true`. One thread per task; **do not pool** virtual threads |
| CPU-bound parallel work | a bounded platform-thread pool sized to the cores (`ForkJoinPool`, parallel streams only for pure, large, CPU work) |
| Per-request context (user, tenant, trace id) | **`ScopedValue`** (final in Java 25): immutable, bounded to a scope, cleaned up automatically, cheap with virtual threads |
| Wait for several subtasks as one unit | `StructuredTaskScope` (**preview** in 25, `--enable-preview`): subtasks share a lifetime and fail together; otherwise `CompletableFuture.allOf` with explicit timeouts |
| Shared counters, caches | `AtomicLong`/`LongAdder`, `ConcurrentHashMap` (`compute`/`merge`), immutable snapshots; locks only around invariants |
| Delayed or periodic work | `ScheduledExecutorService` or the framework scheduler; keep tasks short and idempotent |

## Rules
1. **Context does not follow threads.** A `ScopedValue` binding is not inherited by threads you start (only by `StructuredTaskScope` forks); `ThreadLocal` is not either. Capture what the task needs and re-bind it inside the task, or use the framework helper that does it.
2. **No `ThreadLocal` for new per-request state.** If it must stay, always `remove()` in `finally`; with virtual threads thousands of them mean thousands of copies.
3. **Pinning**: since Java 24 (JEP 491) a virtual thread no longer pins its carrier inside `synchronized`; native frames and some native calls still pin. Prefer `ReentrantLock` for long critical sections that block.
4. **Timeouts everywhere**: every future `get(timeout)`, every HTTP/JDBC call has a timeout; no unbounded waits.
5. **Interrupts**: never swallow `InterruptedException`: restore the flag (`Thread.currentThread().interrupt()`) or propagate.
6. **Visibility and atomicity**: shared mutable state needs `volatile` for a flag, atomics for counters, or a lock for compound invariants. Check-then-act on a shared collection is a race; use `computeIfAbsent`.
7. **Immutability first**: records and unmodifiable collections cross threads safely; mutable objects must be confined to one thread or guarded.
8. **Transactions and persistence contexts are thread-bound**: never hand an `EntityManager`, an open entity graph or a `@Transactional` context to another thread; pass ids and reload.
9. **Failure handling**: log exceptions inside tasks (an uncaught exception in an executor task is lost), propagate cancellation, and limit concurrency (semaphores) when calling external services.
10. **Don't parallelize what is already fast or ordered**; measure first.

## Reviewing thread-safety
For each shared field ask: who writes, who reads, on which threads, and what guarantees ordering? Look for: lazy singletons without `volatile`/holder, `HashMap` shared across threads, `SimpleDateFormat`, static mutable state, double-checked locking, `synchronized` on `this` that is also exposed, blocking inside `synchronized`, `parallelStream` doing I/O, and collections returned from getters without copy.

## Optional pointers
In Dynamia Platform projects the same ideas are available as helpers (`SchedulerUtil`, `ObjectsContext`, tenant propagation by `ContextCapturer`). If `dynamia-platform` is installed (skills listed as `/dynamia-platform:*`), see its `backend` references `utilities.md`, `integration.md` and `saas-tenancy.md`; otherwise suggest `/plugin install dynamia-platform@dynamia-tools` when the project uses it.

End with one line: what runs on which threads, what was not tested under load, any remaining race risk.
