---
name: modern-java
description: Writes and modernizes Java with current language features (records, sealed types, pattern matching, text blocks, sequenced collections, stream gatherers, scoped values, flexible constructor bodies) and knows what is final or preview in Java 21 to 25. Use when writing new Java, refactoring old Java to modern idioms, or deciding whether a language feature is safe to use.
argument-hint: "[file or feature]"
---

# dynamia-java:modern-java

Target the project's Java level (`<java.version>` or `maven.compiler.release` in the `pom.xml`; the Dynamia framework and ERP use Java 25). Before using a feature, check it is **final** at that level (`references/versions.md`); never use a preview feature without `--enable-preview` agreed with the user.

## Idioms to prefer
| Instead of | Use |
|---|---|
| Boilerplate data class (fields, getters, equals, hashCode, toString) | `record` for immutable data carriers; keep JPA entities as classes |
| `instanceof` + cast, long `if/else` on type | pattern matching `instanceof Foo f`, `switch` with type and record patterns |
| Class hierarchies closed by convention | `sealed interface` + records + exhaustive `switch` (no `default`, so adding a case breaks the build) |
| String concatenation of multi-line text | text blocks (`"""`) |
| Verbose locals | `var` where the type is obvious from the right side |
| `list.get(list.size() - 1)`, `iterator` tricks | `SequencedCollection`: `getFirst()`, `getLast()`, `reversed()` (Java 21) |
| Unused lambda or catch variable | unnamed variable `_` (Java 22) |
| `null` returns for "maybe" | `Optional` as a return type only (not fields, not parameters); empty collections instead of `null` |
| Mutable lists passed around | `List.of`, `Map.of`, `copyOf`, `Collectors.toUnmodifiableList`; `Stream.toList()` |
| Custom stateful stream collectors | Stream Gatherers (`windowFixed`, `windowSliding`, `fold`... Java 24) |
| `ThreadLocal` for request state | `ScopedValue` (final in Java 25), see `dynamia-java:concurrency` |
| Constructor that must validate before `super(...)` through static helpers | flexible constructor bodies: statements before `super(...)`/`this(...)` that do not touch `this` (final in 25) |
| `System.getProperty` / manual parsing of config | typed config in the framework you use |

## Rules
- Prefer **clarity over cleverness**: a plain loop beats a three-level stream. Streams for transformation pipelines, loops for side effects and early exits.
- `record` components are shallowly immutable: copy mutable components (`List.copyOf`) in the compact constructor.
- Exhaustive `switch` over sealed types and enums with no `default`; add `default` only for open types.
- Don't use `Optional.get()` without a check; use `orElseThrow()` with a message, `map`, `ifPresentOrElse`.
- Catch the narrowest exception; wrap with the cause; never swallow (`catch (Exception e) {}`) or log-and-rethrow.
- Equality: `equals`/`hashCode` together; for JPA entities see `dynamia-java:hibernate`.
- Time: `java.time` only (`Instant` for moments, `LocalDate` for dates, explicit `ZoneId`); never `Date`/`Calendar`/`SimpleDateFormat` in new code. Money: `BigDecimal` with explicit scale and rounding mode.
- Text: `String.formatted`, `StringBuilder` in loops, `strip()` over `trim()`, `isBlank()`.
- Resources: try-with-resources for anything `AutoCloseable`.

## Modernizing existing code
1. Pick one file or package; keep behavior identical; run its tests first.
2. Apply one idiom at a time (records, then patterns, then streams); commit each separately.
3. Do not mass-reformat; do not rewrite working code only for style.
4. Stop when the code reads better, not when every old construct is gone.

End with one line: the Java level assumed, what changed, what tests ran.
