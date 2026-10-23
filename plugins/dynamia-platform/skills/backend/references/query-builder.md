# QueryBuilder

`tools.dynamia.domain.util.QueryBuilder` builds a JPQL string (select, update, delete) with a chainable API and holds the `QueryParameters` for binding. Checked against framework 26.10 (`QueryBuilder`, `QueryConditions`, `CrudService`).

## Choose
| Case | Use |
|---|---|
| Filter an entity by fields, paging, sorting | `crudService.find(Type.class, QueryParameters...)`, no builder |
| Projection of a few columns, joins, group by, update/delete by condition, conditions assembled at runtime | `QueryBuilder` |
| Fixed query reused in many places | `@NamedQuery` + `findWithNamedQuery` |

## Build and run
```java
QueryBuilder qb = QueryBuilder.select(Person.class, "p", "name", "email")   // type, var, fields
        .where("p.age > 18")
        .orderBy("name");
List<Object[]> rows = crudService.executeQuery(qb);      // <T> List<T> executeQuery(QueryBuilder)

// whole entity, conditions as bound parameters
QueryBuilder q = QueryBuilder.select().from(Person.class, "p")
        .where("name", QueryConditions.like("ann"))
        .and("age", QueryConditions.geqt(18))
        .and("created", QueryConditions.between(LocalDateRange.currentMonth()))
        .orderBy("name");
q.getQueryParameters().paginate(20);
List<Person> page = crudService.executeQuery(q);
```
- `select(Class type, String var, String... fields)`, `select(Class entity, Class resultType, var, fields)`, `select()` + `from(entity, var)`, `fromParameters(type, var, QueryParameters)`.
- Conditions: `where`, `and`, `or` take either a raw string or `(field, QueryCondition)`. Also `orderBy`, `groupBy`, `having`, `innerJoin`, `leftJoin`, `rightJoin`, `join`, `customSelect`, `customFrom`, `resultType`, `clone`.
- `QueryConditions`: `eq`, `like`, `startsWith`, `endsWith`, `gt`, `geqt`, `lt`, `leqt` (numbers, `Date`, `LocalDate`, `LocalDateTime`), `between` (values, `DateRange`, `LocalDateRange`, `LocalDateTimeRange`), `in`, and more; most take an optional `BooleanOp`.
- Field names get the variable prepended automatically (`appendVarNames`); write `p.age` yourself only in raw strings.
- `toString()` returns the JPQL: print it when debugging.

## Update and delete
```java
QueryBuilder up = QueryBuilder.update(Person.class, "p")
        .set(Map.of("status", "ACTIVE", "updated", LocalDateTime.now()))
        .where("id", QueryConditions.eq(7L));
int rows = crudService.execute(up);          // execute(QueryBuilder) -> execute(text, params)
```
`QueryBuilder.delete(Class, var)` works the same. `crudService.batchUpdate(type, field, value, params)` covers the simple "set one field" case.

## Rules
- **Raw strings go into the JPQL as written.** Never concatenate user input into them; pass values through `QueryConditions` / `QueryParameters`, which bind them.
- Use `java.time` values in conditions and parameters (`gt(LocalDate)`, `addLocalDate`, `LocalDateRange`), not `Date`.
- Paginate with `getQueryParameters().paginate(size)`; the paginator is filled by the executor (`getPaginator()`).
- A projection returns `Object[]` unless you set a `resultType`; the entity is returned as is, so OSIV-off rules apply (`loading-collections.md`). Use `QueryParameters.mapWith` to return `BeanMap` rows.
- Multi-tenant apps: check in the project that tenant filtering still applies to queries built with `customFrom`/`customSelect` before using them in SaaS code (not verified here).
- Write one test with an in-memory DB for each non-trivial builder; compare `toString()` for the shape and the result for the data.
