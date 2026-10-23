# CrudService, QueryParameters and QueryConditions

Checked against framework 26.10 (`CrudService`, `JpaCrudService`, `QueryParameters`, `QueryBuilder.fromParameters`, `QueryConditions`, `AbstractQueryCondition`, `LikeEquals`, `DomainUtils.buildSearcheableString`). Patterns marked "in practice" were seen in a large Dynamia ERP codebase; entity names here are neutral.

## Get it
Constructor injection, or `DomainUtils.lookupCrudService()` / `Containers.get().findObject(CrudService.class)` where injection does not reach (entities, static code, view models). Never use `EntityManager` or loose JPQL in services.

## Which method for which task
| Task | Method |
|---|---|
| One by id | `find(Type.class, id)`; `load(Type.class, id, "paths"...)` to also load collections (`loading-collections.md`) |
| First match of a filter | `findSingle(Type.class, params)` (limit 1, the first row, not an error when several match), `findSingle(Type.class, "prop", value)` |
| List with filters, order, paging | `find(Type.class, params)`; `findAll(Type.class[, orderBy])` |
| List by one property | `find(Type.class, "prop", value)` (same as `find` with `QueryParameters.with`) |
| Count | `count(Type.class, params)`, `count(Type.class)` |
| Search a text in several fields | `findByFields(Type.class, text, params, "name", "code")` |
| Distinct values of a property | `getPropertyValues(Type.class, "prop"[, params])` |
| Null property | `findIfNull(Type.class, "prop")` |
| Query with joins, projections, group by | `QueryBuilder` + `executeQuery(qb)` (`query-builder.md`), `executeProjection(Class, qb)` for a single value (count, sum, max, avg) |
| Update/delete by condition | `batchUpdate(Type.class, "field", value, params)` or `batchUpdate(Type.class, Map, params)`; `execute(qb)` |
| Change one field or a counter | `updateField(entity, "f", v)`, `increaseCounter(entity, "n")`, `deacreaseCounter` (sic) |
| Create / update / save / delete | `create`, `update`, `save` (create or update), `delete(entity)`, `delete(Type.class, id)`, `deleteAll(Type.class)` |
| Reload an entity | `reload(entity, "paths"...)` |
| Read-only list | `findReadOnly(Type.class, params)` (sets `params.setReadOnly(true)` and calls `find`) |
| Named or native query | `findWithNamedQuery`, `findByNativeQuery(sql, Type.class)` (native SQL is not tenant-filtered, `saas-tenancy.md`) |
| By an example object | `findByExample(example[, params])` |
| Own transaction | `executeWithinTransaction(callback)` (always `REQUIRES_NEW`), `saveWithinTransaction(entity)` |

`find`, `findSingle` and the other reads are not necessarily transactional: with no transaction active the result is **detached** (see `loading-collections.md`). Inside your own `@Transactional` service they stay attached.

## QueryParameters
A `Map<String, Object>` of property to value or `QueryCondition`, plus paging, order and hints. Keys may be nested paths (`"category.name"`, `"customer.id"`).
```java
var params = QueryParameters.with("active", true)                       // property = value
        .add("category", category)                                      // entity: by equality
        .add("price", QueryConditions.between(10, 50))                  // a condition
        .add("name", "ann")                                             // String: LIKE, see below
        .orderBy("name")                                                // orderBy("name", false) = desc
        .paginate(20);                                                  // DataPaginator(20); params.getPaginator() after the call
params.setMaxResults(50);                                               // cap without a paginator
List<Product> page = crudService.find(Product.class, params);
long total = crudService.count(Product.class, params);
```
- `with(...)` starts one; `add(...)` chains. Typed adders: `addString`, `addInteger`, `addLong`, `addBoolean`, `addDouble`, `addFloat`, `addDate`, `addLocalDate`, `addLocalDateTime`, `addLocalTime`, and `add(key, Class, value)`.
- A `null` value adds **no condition** to the generated query (`QueryBuilder` skips it), so a filter whose value is null silently disappears. Use `QueryConditions.isNull()` / `isNotNull()` for explicit null tests, and build the params conditionally (`if (x != null) params.add(...)`) so the intent is visible.
- A key `id` or ending in `.id` has a numeric string converted to `Long`.
- Keys starting with `#` are ignored when binding (internal markers).
- Other options: `sort(BeanSorter)`, `setHint(name, value)`, `setDepth(n)`, `setReadOnly(true)`, `mapWith(EntityMapper)` (`bean-map-dto.md`), `setType(Class)`, `clone()`.
- With a paginator, `find` returns a `PagedList` that loads its pages on demand; with `setMaxResults` and no paginator it is a plain capped list.

## Text search: the default is LIKE
**A plain `String` value in `QueryParameters` is turned into a `like`**, not `=`. `QueryBuilder.fromParameters` renders `property like :param`, and the value is passed through `DomainUtils.buildSearcheableString`: every character that is not a letter or digit becomes `%`, and the result starts and ends with `%` (`*` also becomes `%`). So `"john smith"` searches `%john%smith%`, and `"A-12"` searches `%A%12%`. This is on by default (`autocreateSearcheableStrings = true`).
- The method's Javadoc shows `%J%o%h%n%...`; the code does not put a `%` between letters. Trust the code, and check with a test if the exact pattern matters.
- **Exact match instead**: `QueryConditions.eq("x")` for one property; `params.setAutocreateSearcheableStrings(false)` for the whole object; or the shortcut `findSingle(Type.class, "prop", value)`, which already turns it off. `find(Type.class, "prop", value)` does **not**: it keeps the LIKE default for strings, so use `eq` when you mean equality (codes, emails, ids as text).
- **Other text conditions**: `like(value)` (same as the default, explicit), `like(value, false)` (the value is used as the pattern you wrote, so add your own `%`), `startsWith(text)`, `endsWith(text)`, `notEq(text)`.
- Case: `like` is as case-sensitive as the database collation; the framework adds no `lower()` on this path. Check your database (not verified here).
- Non-text values (numbers, enums, entities, booleans, dates) are compared with `=`.
- In practice, codes, identifiers and unique names are looked up with `eq`; free-text boxes use the default or `like`.

## QueryConditions catalog
`tools.dynamia.domain.query.QueryConditions` (static factories). Most take an optional `BooleanOp` as last argument.
| Group | Factories |
|---|---|
| equality | `eq(v)`, `notEq(v)` |
| text | `like(v)`, `like(v, searcheable)`, `startsWith`, `endsWith` |
| comparison | `gt`, `geqt`, `lt`, `leqt` for `Number`, `Date`, `LocalDate`, `LocalDateTime` |
| range | `between(lo, hi)`, `between(DateRange)`, `between(LocalDateRange)`, `between(LocalDateTimeRange)` |
| lists | `in(values...)`, `in(List)`, `in("subquery")`, `in("subquery", paramsMap)`, `notIn(...)` same forms |
| null | `isNull()`, `isNotNull()` |
| composition | `group(cond...)`, `group(BooleanOp, cond...)` (several conditions on the same property) |
In practice the most used are `eq`, `in`, `isNotNull`, `between`, `isNull`, `notEq`; `like` and the comparisons are rare because defaults and ranges cover them. Prefer `LocalDateRange` and `java.time` values (`dynamia-platform:dates`).

## OR needs a group
Each condition carries a `BooleanOp` (default `AND`). A condition with `BooleanOp.OR` is chained with **everything before it in the same `QueryParameters`**, including unrelated filters, which can cancel a security or tenant filter. Put the OR terms in their own `QueryParameters` and add it with `addGroup`, which wraps it in parentheses:
```java
var params = QueryParameters.with("active", true);
params.addGroup(QueryParameters.with("name", QueryConditions.like(text, true, BooleanOp.OR))
        .add("code", QueryConditions.like(text, true, BooleanOp.OR))
        .add("reference", QueryConditions.like(text, true, BooleanOp.OR)), BooleanOp.AND);
params.setMaxResults(20);
```
The result is `active = :active and (name like :name or code like :code or reference like :reference)`. `findByFields(Type.class, text, params, "name", "code", "reference")` does exactly this and picks the condition by field type (text uses LIKE, enums and numbers use `eq`, booleans are skipped). Use it for "search box over several columns".

## Create a new condition
Three levels, simplest first.
1. **A raw JPQL fragment** with `CustomQueryCondition(text)` or `CustomQueryCondition(text, query -> query.setParameter(...))`: `render` returns your text as is, and the lambda binds your parameters. The key you add it under only names the entry.
```java
params.add("id", new CustomQueryCondition(
        "id in (select distinct d.order.id from OrderLine d where d.name like :line)",
        query -> query.setParameter("line", DomainUtils.buildSearcheableString(text))));
```
Use it for sub-selects and anything the factories cannot say. Bind every value with `setParameter`; never concatenate user input into the text. In practice this is how filter customizers translate one filter box into a sub-select on a child table.
2. **A reusable class**: extend `AbstractQueryCondition<T>`. It renders `property <operator> :property` and binds the value for you; you give the operator. Override `render` or `apply` only for other shapes.
```java
public class NotStartsWith extends AbstractQueryCondition<String> {
    public NotStartsWith(String prefix) { super(prefix + "%"); }
    public NotStartsWith(String prefix, BooleanOp op) { super(prefix + "%", op); }
    @Override protected String getOperator() { return "not like"; }
}
// params.add("code", new NotStartsWith("TMP-"));
```
`QueryCondition<T>` has `render(property)` (the JPQL text), `apply(property, query)` (bind parameters), `getBooleanOperator()`, `getValue()` and an optional `match(other)` for in-memory evaluation (the default throws `UnsupportedOperationException`).
3. **A factory** so callers read well: a small final class with static methods (`MyConditions.notStartsWith(...)`) returning the condition, next to the entity or module. Do not edit `QueryConditions` itself.

Rules: the bound parameter name is the property with dots, spaces and punctuation removed (`QueryConditionUtils.cleanProperty`), so two conditions on the same property in one query collide: wrap them in `QueryConditions.group(...)` or use `between`; always accept a `BooleanOp` overload; test `render` output and one real query.

## Listeners and events
`find`, `findSingle` and the create/update/delete methods fire `CrudServiceListener` events (`BEFORE_CREATE`/`AFTER_CREATE`, `BEFORE_UPDATE`/`AFTER_UPDATE`, `BEFORE_DELETE`/`AFTER_DELETE`, `BEFORE_QUERY`/`AFTER_QUERY`); `findReadOnly` goes through the same `find`. `AccountAwareCrudServiceListener` adds the account filter to `QueryParameters` for entities without `@TenantId`. See "Validators and listeners" in `SKILL.md`.

## Do / don't
- Do build `QueryParameters` conditionally; keep one place per query that knows the filters.
- Do use `findSingle` only when "the first match" is what you want; for "must be unique" check `count` or catch duplicates at save with a validator.
- Do cap searches (`setMaxResults`) for pickers and autocomplete.
- Don't use the String default for codes, emails or usernames: it matches substrings (`%a%b%`), which finds the wrong row.
- Don't mix `OR` conditions with other filters in the same `QueryParameters`.
- Don't loop `find` per row; query once with `in(ids)` and group in memory.
- Don't call `crudService.find` in a UI loop on every keystroke without a max result and a minimum length.
