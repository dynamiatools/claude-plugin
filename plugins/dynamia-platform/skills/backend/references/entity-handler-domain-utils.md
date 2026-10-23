# EntityHandler and DomainUtils

Checked against framework 26.10 (`tools.dynamia.domain.EntityHandler`, `tools.dynamia.domain.util.DomainUtils`).

## EntityHandler: a typed CrudService for one entity
A thin wrapper that fixes the entity class so you do not repeat `Type.class` on every call. It is not a repository and keeps no state.
```java
var handler = EntityHandler.handle(Customer.class);                 // uses DomainUtils.lookupCrudService()
var other   = EntityHandler.handle(Customer.class, crudService);    // explicit service (tests, special instances)
Customer c  = handler.findSingle(QueryParameters.with("code", QueryConditions.eq("C-01")));
List<Customer> list = handler.find(QueryParameters.with("active", true).orderBy("name"));
```
- `handle(Class)` throws `IllegalArgumentException` if the class is not an entity (`DomainUtils.isEntity`).
- Methods: `findSingle(params)`, `find(params)`, `findAll()`, `findAll(orderBy)`, `findById(id)`, `findFirst()`, `count()`, `count(params)`, `create`, `update`, `save`, `delete`, `deleteAll()`, `batchUpdate(field, value, params)`, `batchUpdate(Map, params)`.
- Every call goes to `CrudService`, so the rules in `crud-service.md` apply (a `String` value is a `LIKE`, `findSingle` is the first match, reads outside a transaction return detached entities).
- **Where it is used in practice**: small static finders on the entity or its module, where no service can be injected:
```java
public static Customer findByCode(String code) {
    return EntityHandler.handle(Customer.class)
            .findSingle(QueryParameters.with("code", QueryConditions.eq(code)));
}
```
Keep that to one-line lookups. Logic, transactions and anything that needs several queries belong in a service with an injected `CrudService`; do not grow an entity into a service (anti-pattern in `SKILL.md`).
- In services, inject `CrudService` and call it directly; `EntityHandler` adds nothing there.

## DomainUtils: what is there
`tools.dynamia.domain.util.DomainUtils` is static helpers around entities and the domain layer. Look here before writing a helper.

| Area | Methods |
|---|---|
| Services | `lookupCrudService()`, `lookupCrudService(Class)`, `lookupGraphCrudService()` |
| Entity identity | `isEntity(Object|Class)`, `findEntityId(entity)`, `getEntityClass(entity)`, `isPersitable(Field)` (sic) |
| Proxies | `unproxy(entity)`, `initializeEntity(entity)` (use before the entity leaves the persistence context, see `loading-collections.md`) |
| DTOs | `autoDataTransferObject(target, DtoClass)` (see `bean-map-dto.md`) |
| Validation | `validate(obj)` runs the bean validators and throws `ValidationError` |
| Entity references | `getEntityReference(alias, id)`, `getEntityReferenceName(alias, id[, default])`, `getEntityReferenceRepository(Class|name)`, `getEntityReferenceRepositoryByAlias(alias)`: names and lookups by alias, the mechanism behind entity pickers |
| Counters | `findNextCounterValue(entity, "counterName")` returns the next number and increments the stored counter (invoice numbers) |
| Search text | `buildSearcheableString(text)` makes the `%a%b%` LIKE pattern used by `QueryParameters` (see `crud-service.md`) |
| Text | `cleanString(text[, onlyNumbers])` (upper case, strips special characters), `formatNumberWithZeroes(5, 1000)` gives `0005`, `isLong`, `isInteger` |
| Numbers | `sum(BigDecimal...)`, `substract(BigDecimal...)` (sic), `sumField(collection, Class, "field")`, `simpleRound(n[, zeros])`, `getZeroIfNull(n)` |
| Queries | `configureSorter(queryText, sorter)` appends an `ORDER BY` from a `BeanSorter` |
| Money | `getCurrencyExchangeProvider()` |
| Params | `getDefaultParameterClass()` |
Related, in other classes: `BigDecimalUtils` (commons), `JpaUtils` (`initializeEntity`, `entityEquals`), `ObjectOperations` (property access), see `utilities.md`.

## Rules
- Use `isEntity` and `findEntityId` instead of reflection on `@Id`; they handle proxies.
- `unproxy` before comparing classes or serializing a possibly-proxied entity.
- Do not use `findNextCounterValue` for gap-free legal numbering without checking concurrency in your database and tenant (it is a counter increment, not a sequence guarantee). Not verified here.
- Keep `lookupCrudService()` for code that cannot receive the service by constructor.
