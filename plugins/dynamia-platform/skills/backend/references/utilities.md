# Utility classes

Before writing a helper, look here. Names were read from the framework 26.10 sources; check the exact signature in the project's version before use.

## Where they live
| Class | Package / module | What it is for |
|---|---|---|
| `DateTimeUtils` | `commons` | dates and times: convert, add, compare, ranges, format (see `dynamia-platform:dates`) |
| `LocalDateRange`, `LocalDateTimeRange`, `DateRange` | `commons` | date ranges (`DateRange` is the legacy `Date` one) |
| `StringUtils` | `commons` | `hasText`, `hasLength`, `isBlank`, `isNumber`, `isDate`, `startsWithIgnoreCase`, `endsWithIgnoreCase`, `pathEquals`, `containsWhitespace` ... |
| `BigDecimalUtils` | `commons` | money math: `safe`, `sum`, `isZero`, `isPositive`, `isNegative`, `gt`/`gte`/`lt`/`lte`, `addPercent`, `computePercent`, `evaluate(expression, vars)`, `rate` |
| `ObjectOperations` | `commons` | beans by property name: `transform`, `transformAll`, `filterByProperty`, `findByProperty`, `groupBy`, `countByProperty`, `sumProperty`, `getComparator`, `getComparatorDesc`, `getInstanceName`, `invokeGetMethod`, `getValuesMaps` |
| `BeanMap`, `MapBuilder` | `commons` | maps: bean as map (`bean-map-dto.md`); `MapBuilder.put(key, value, ...)`, `of`, `copy`, `empty`, `serializable` |
| `Streams` | `commons` | `collectIf`, `findFirstIf`, `findFirstElseNull`, `forEachIf`, `mapAndSum`, `mapToBigDecimal` |
| `Lambdas` | `commons` | function helpers: `chain`, `filter`, `nullSafe`, `unchecked`, `memoize`, `lazy`, `retry`, `safeCall`, `orElse`, `orElseGet` |
| `CollectionsUtils` | `commons.collect` | `findFirst`, `group`, `groupBy`, `iteratorToList`; also `PagedList`, multi-maps |
| `Formatters` | `commons` | `formatDate`, `formatDateTime` (also with pattern, locale, zone), `formatCurrency` |
| `Randoms` | `commons.math` | test data: `nextInt`, `nextDate`, `nextPastDate`, `nextFutureDate`, `chooseRandom` |
| `StopWatch`, `SimpleTemplateEngine`, `StringSimplifier` | `commons` | exist in `commons`; read their source before use |
| `BeanTransformer`, `ObjectCloner`, `BeanValidator` | `commons.ops` | DTO transform and copy, cloning, validation helpers |
| `DomainUtils` | `domain` | entities: `isEntity`, `findEntityId`, `unproxy`, `autoDataTransferObject`, `lookupCrudService`, `sum`, `substract`, `simpleRound` |
| `JpaUtils` | `domain-jpa` | `initializeEntity`, `entityEquals`/`entityHashCode`, paginator config |
| `SchedulerUtil` | `integration.scheduling` | background and scheduled work (below) |
| `HttpUtils`, `IOUtils`, `ImageUtil` | various modules | HTTP, IO and image helpers; find them with `grep -rl 'class HttpUtils'` |

Prefer these over a new `Utils` class or an extra dependency (Apache Commons, Guava) when they cover the case. If you need something general and missing, add it to the module where the rest lives, with a test.

## SchedulerUtil: processes, background work, cron
`tools.dynamia.integration.scheduling.SchedulerUtil`. Static methods; no instance needed.

**Run now, in the background** (virtual threads):
```java
SchedulerUtil.run(() -> sendReport(id));                       // CompletableFuture<Void>
SchedulerUtil.run(this::step1, this::step2);                   // run one after another, waits for the chain
SchedulerUtil.runAndWait(() -> rebuildIndex(), Duration.ofMinutes(2));
CompletableFuture<Report> f = SchedulerUtil.runWithResult(() -> buildReport());   // Supplier or TaskWithResult
```
**Schedule**:
```java
SchedulerUtil.schedule(CronMaker.daily(6, 30), () -> nightlySync());         // cron, server time zone
SchedulerUtil.schedule(cron, TimeZone.getTimeZone("America/Bogota"), task);  // explicit zone
SchedulerUtil.schedule(LocalDateTime.now().plusHours(1), ZoneId.systemDefault(), task);
SchedulerUtil.scheduleAtFixedRate(Duration.ofMinutes(5), task);              // returns ScheduledFuture<?>
```
`CronMaker` builds cron strings: `minutes(n)`, `hourly(n)`, `daily(h, m)`, `dailyWeekDay(h, m)`, `weekly(h, m, days...)`, `generate(...)`.

**Rules**
- Check `SchedulerUtil.isSchedulingEnabled()` (property `schedulingEnabled`, default true) before registering schedules in code that also runs in tests or on replicas; keep the returned `ScheduledFuture` if you must cancel it.
- A scheduled or background task runs outside the request. Request-bound state (a `ScopedValue` binding such as `NavigationManagerSession`, the current user, the tenant) is **not there**. Wrap the runnable with `SchedulerUtil.getWithContext(runnable)` to carry the captured `ObjectsContext`, and bind tenant/account explicitly (`AccountServiceAPI.runAsAccount`, `AccountTenants.runAs` in SaaS apps).
- Tasks must be idempotent and safe to run twice (restart, several nodes). In a cluster, guard with a lock or run on one node.
- Long work reports progress with a `ProgressMonitor`, not by polling a field; actions that start it return right away (headless actions see `headless-actions.md` and `UIProgress`).
- Catch and log inside the task; an exception in a scheduled task is otherwise silent.
- Prefer the `java.time` overloads (`schedule(LocalDateTime, ...)`) to the `Date` one. Note `schedule(cron, task)` uses `TimeZone.getDefault()`, while `DateTimeUtils` uses `Messages.getDefaultTimeZone()`: pass the zone explicitly when they can differ.
- Daily periodic hooks: register `PeriodicTaskExecutor` as a bean (disabled by default) and implement `MorningTask` (6:00), `MiddayTask` (12:00), `AfternoonTask` (18:00) or `MidnightTask` (23:59), server local time zone.
- `SchedulerUtil.sleep(Duration)` re-interrupts the thread on `InterruptedException`; do not wrap `Thread.sleep` yourself.
