# Loading collections without OSIV

Checked against `docs/backend/ARCHITECTURE.md` ("Running Without Open Persistence In View") in framework 26.10.

## The problem
By default a ZK request keeps one `EntityManager` open while views render (`dynamia.app.open-persistence-in-view`, default `true`), so views lazy-load. With it `false` (and always for REST/JSON), an entity returned by `find`, `load`, `reload` or `findSingle` is **detached** when the call returns: touching a lazy collection throws `LazyInitializationException`. `spring.jpa.open-in-view` does not affect this; it only configures Spring MVC.

## The rule
`CrudService` initializes the associations an entity needs **before it leaves the persistence context**. It does this only when the call is the **outermost** one (no transaction active, or this call started it). Inside a service that already runs in a transaction nothing extra is loaded, because the entity stays attached.

## 1. Declare the plan on the entity
```java
@Entity
@InitializeOnLoad({"detalles", "impuestos", "detalles.subdetalles"})
public class Venta { ... }
```
Paths walk through collections. `@InitializeOnLoad(allCollections = true, depth = 2)` initializes every to-many association.

On a field or getter (reads better; `value` is relative to that property; class and field declarations, also from superclasses, add up):
```java
@InitializeOnLoad("subdetalles")            // detalles and detalles.subdetalles
@OneToMany(mappedBy = "venta") private List<DetalleVenta> detalles;

@InitializeOnLoad                            // impuestos
@OneToMany(mappedBy = "venta") private List<ImpuestoVenta> impuestos;
```
`@ElementCollection` counts as a collection.

## 2. Ask at the call site
Adds to the declared plan and is honored in every mode:
```java
var venta = crudService.load(Venta.class, id, "detalles", "pago.detalles");
venta = crudService.reload(venta, "retenciones");     // entity that reached you detached
var plan = crudService.load(Venta.class, id, LoadPlan.of("detalles"));
```
An entity that is already detached **cannot** be repaired (Hibernate 7 has no re-attach): reload it with the paths. `JpaUtils.initializeEntity(entity, LoadPlan)` is the low-level form; it returns the un-proxied entity.

## 3. The CRUD view does it for you
`CrudController.doEdit`, `reloadEntity` and `CrudView.buildActionEvent` load the entity with the collection fields of the **form descriptor** (`ViewDescriptorProperties.collectionsOf`). A form with a child table, `afterEdit()` and the actions launched from the view receive those collections initialized.

## Global mode: `dynamia.crud.load-collections`
| Value | Effect |
|---|---|
| `annotated` (default) | Applies `@InitializeOnLoad`; entities without it behave as before |
| `all` | Also initializes every to-many association up to `dynamia.crud.load-depth` (default 1). Good to discover what an app depends on; can be expensive |
| `none` | Ignores `@InitializeOnLoad`; explicit paths still work |

List queries (`find(type, params)`, `executeQuery`) do **not** load collections.

## Safety net (off by default)
`dynamia.app.lazy-load-no-trans=true` (Spring Boot: `spring.jpa.properties.hibernate.enable_lazy_load_no_trans=true`) lets Hibernate load a touched lazy association in a temporary session. Each collection opens its own session and connection (N+1) and hides the problem: a temporary bridge, not a design.

## Do not
- Touch `.size()` or iterate just to force a load.
- Keep an `EntityManager` open outside a transaction to get the old behavior back: `REQUIRES_NEW` (`executeWithinTransaction`, `AccountTenants.runAs`) reuses it and it keeps the tenant it was opened with.
- Compare entities with a hand-written `equals` on the proxy class: `SimpleEntity` and `SimpleEntityUuid` use `JpaUtils.entityEquals` / `entityHashCode`, which are safe with Hibernate proxies and do not initialize them.

## Checklist when a screen throws LazyInitializationException
1. Is the app running with OSIV off? Check `dynamia.app.open-persistence-in-view`.
2. Which collection? Put `@InitializeOnLoad` on its field, or pass the path in `load`/`reload`.
3. Is the call inside a transaction of yours? Then the entity is attached; the problem is later, after the transaction ends: load there or return a `BeanMap` (see `bean-map-dto.md`).
4. Add a test with OSIV off (the framework's domain-jpa and zk tests run with and without it).
