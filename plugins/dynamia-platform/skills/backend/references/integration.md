# Integration module: Containers, ObjectsContext, messaging, search, progress, reactive

`tools.dynamia.integration` (platform/core/integration), read from framework 26.10. `SchedulerUtil` is in `utilities.md`; `@Provider` and the stereotypes are in `SKILL.md`.

## Containers: find beans without injection
`Containers.get()` is the facade over the installed object containers (Spring is one; tests install their own).
```java
CrudService crud = Containers.get().findObject(CrudService.class);
Collection<Validator> all = Containers.get().findObjects(Validator.class);
var named = Containers.get().findObject("beanName", MyService.class);
Containers.get().findObject(Type.class, matcher);        // ObjectMatcher: pick one of several
```
Also `installObjectContainer`, `removeContainer`, `getContainer(name)` (tests and special setups). `ObjectContainer` is the SPI (`getName`, `getObject(name, type)`, `getObject(type)`, `getObjects(type)`).
- Use constructor injection first. `Containers` is for code that cannot be injected (entities, static helpers, framework callbacks, `DomainUtils.lookupCrudService()`).
- `findObject` returns `null` when there is none: check it, as `AccountServiceAPI.get()` callers do. In plain unit tests no container exists unless you install one (`testing.md`).
- A request or session scoped bean found this way fails outside a request.

## ObjectsContext: the "current" objects of the running code
Facade for context variables such as the current user, branch, account or cash register, stored in a `ScopedValue` (no `set`/`clear`; scopes only).
```java
ObjectsContext.with(branch).run(() -> {
    ObjectsContext.with(cashbox).run(() -> {
        Branch b = ObjectsContext.get(Branch.class);           // outer scope still visible
        Cashbox c = ObjectsContext.require(Cashbox.class);     // throws if none
    });
});
```
- Read: `get(type)`, `get(name, type)`, `find(type)` (Optional), `require(type)`, `getAll(type)`. Lookup order: bound with `with(...)` (or by `SchedulerUtil`), the legacy thread-local container, then Spring.
- Bind: `with(objects...)` returns a `Scope`; `.add(name, object)`, then `.run(Runnable)`, `.get(Supplier)` or `.call(op)`. Scopes add up (inner wins for the same type) and disappear when the code ends, also on exceptions.
- **Threads**: a scoped value is not inherited. `ObjectsContext.capture()` takes a `Snapshot` (including what `ContextCapturer` beans contribute); `snapshot.wrap(runnable)` re-applies it inside a task, and `ObjectsContext.wrap(executor)` wraps every task of an executor. `SchedulerUtil` does this for you.
- **`ContextCapturer`** (a bean): `Binding capture()` returns what must travel to other threads (or `null`) and how to re-bind it. The SaaS tenant (`AccountTenantContextCapturer`) and the security context (`SecurityContextCapturer`) are examples. Write one for your own request-bound state.
- `legacyThreadLocalBridge(true)` keeps reading old thread-local values while migrating. Prefer `ScopedValue` for new per-request state; never store request state in a static field.

## Messaging (`ms`)
A small in-process publish/subscribe: `MessageService.createChannel(name)`, `publish(channel, message)` (a `Message`, `String` as `TextMessage`, `Map` as `MapMessage`, or any `Serializable`), subscribe with a `MessageListener`/`MessageChannelSubscription`. Message types: `TextMessage`, `MapMessage`, `NumberMessage`, `ObjectMessage`, `ByteArrayMessage`. Implementations: `SimpleMessageService`, `TransactionalSimpleMessageService` (the same, with each publish running in a Spring transaction), `SpringApplicationEventsMessageService`. Use it to decouple modules inside one JVM; it is not a broker (no persistence, no cross-node delivery). Check which implementation the app wires.

## Search (`search`)
`SearchResultProvider` (beans): `getId()`, `getName()`, `search(query)` returns `SearchResult`s; `SearchService` controls the application's global search over the registered providers. Register one per searchable area; return few, relevant results fast; `SearchResultCommandExecutor` runs the chosen result.

## ProgressMonitor
`ProgressMonitor` carries `max`, `current`, `message`, `messages`, `stop()`/`isStopped()`, and a listener (`onProgressChanged`). Pass one to long jobs, update it, and let the UI or the headless `UIProgress` follow. Check `isStopped()` inside loops so users can cancel (file-importer works this way). Combine with `SchedulerUtil.run(...)`.

## Reactive (`reactive`)
A small React/Vue-style system for Java UIs: `Reactive.ref(value)` (`Ref`, `set`/`get`), `Reactive.computed(() -> ...)` (lazy derived value), `Reactive.effect(() -> ...)` (re-runs when the refs it read change). `Signal` is the internal subscriber tracker. Dependencies are tracked automatically. Use it in view models and component logic, not in services.

## Rules
- Prefer injection; use `Containers` at the edges and `ObjectsContext` for per-request "current" objects.
- Don't keep `Containers.get()` results in static fields (tests and reloads change containers).
- Everything handed to another thread needs its context re-bound (`capture`/`wrap`, or `SchedulerUtil`).
- `@Provider` beans are discovered by component scanning: put them under the app's `basePackage`.
