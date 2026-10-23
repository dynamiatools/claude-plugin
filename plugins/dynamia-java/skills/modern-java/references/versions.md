# What is final where

Read on 2026-10-23 from openjdk.org (JDK 24 and 25 project pages); earlier releases from the JEPs. JDK 25 (released 2025-09-16) is an LTS release from most vendors.

| Feature | JEP | Status |
|---|---|---|
| Records | 395 | final in 16 |
| Text blocks | 378 | final in 15 |
| Sealed classes | 409 | final in 17 |
| Pattern matching for `instanceof` | 394 | final in 16 |
| Pattern matching for `switch`, record patterns | 441, 440 | final in 21 |
| Sequenced collections | 431 | final in 21 |
| Virtual threads | 444 | final in 21 |
| Unnamed variables and patterns (`_`) | 456 | final in 22 |
| Stream Gatherers | 485 | final in 24 |
| Class-File API | 484 | final in 24 |
| Synchronize virtual threads without pinning | 491 | final in 24 |
| Security Manager permanently disabled | 486 | final in 24 |
| Scoped Values | 506 | **final in 25** (preview 4th in 24) |
| Module import declarations (`import module java.base;`) | 511 | final in 25 |
| Compact source files and instance `main` methods | 512 | final in 25 |
| Flexible constructor bodies | 513 | final in 25 |
| Compact object headers | 519 | final in 25 (check the flag to enable it) |
| Generational Shenandoah | 521 | final in 25 |
| AOT command-line ergonomics, AOT method profiling | 514, 515 | final in 25 |
| JFR cooperative sampling, method timing and tracing | 518, 520 | final in 25 |
| Key Derivation Function API | 510 | final in 25 |
| Remove the 32-bit x86 port | 503 | final in 25 |
| Structured Concurrency (`StructuredTaskScope`) | 505 | **preview** (5th) in 25 |
| Primitive types in patterns, `instanceof` and `switch` | 507 | **preview** (3rd) in 25 |
| Stable Values | 502 | **preview** in 25 |
| PEM encodings of cryptographic objects | 470 | preview in 25 |
| Vector API | 508 | incubator (10th) in 25 |
| JFR CPU-time profiling | 509 | experimental in 25 |

## Notes
- Preview and incubator features need `--enable-preview` / `--add-modules` at compile and run time and can change or disappear: do not ship libraries that depend on them.
- Java 24 also removed the non-generational ZGC mode (JEP 490) and warns on `sun.misc.Unsafe` memory-access methods (JEP 498) and on JNI use (JEP 472): check libraries that use them before upgrading.
- Re-check this table when a new JDK appears: `https://openjdk.org/projects/jdk/<version>/`.
