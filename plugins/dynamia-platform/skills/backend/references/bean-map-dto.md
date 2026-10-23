# BeanMap and automatic DTOs

Checked against framework 26.10: `commons/BeanMap`, `domain/query/BeanMapEntityMapper`, `EntityMapper`, `QueryParameters.mapWith`, `DomainUtils.autoDataTransferObject`, `ObjectOperations.transform`, `BeanTransformer`.

## Pick the tool
| You need | Use |
|---|---|
| Rows for a list/table/REST response that must survive **after** the transaction, no DTO class | `BeanMapEntityMapper` with `QueryParameters.mapWith(...)` |
| Any bean as a dynamic map (JSON, XML, generic code) | `BeanMap` |
| A typed DTO class, copy matching properties | `ObjectOperations.transform` / `BeanTransformer` |
| A typed DTO where entity references become a name and an id | `DomainUtils.autoDataTransferObject` |
| Same DTO with different property names per consumer | `@Alias` + `AliasBeanMapper` |

## BeanMap
A `HashMap<String, Object>` that also carries metadata: `id`, `name` (class simple name), `beanClass`, `stringRepresentation` (the bean's `@InstanceName` member, else `toString()`), `fields`. Implements `Serializable`, `Jsonable` (`toJson()`) and `Xmlable` (`toXml()`).
```java
BeanMap map = new BeanMap();
map.load(myBean);                 // Mappable.toMap() if implemented, else ObjectOperations.getValuesMaps
Object v = map.get("name");       // generic: <T> T get(String)
map.set("other", 123);
```
Not thread-safe. Mark the member that identifies an instance with `@InstanceName` (it replaces `toString` in `BeanMap` and in `BeanMapEntityMapper`).

## BeanMapEntityMapper: the automatic DTO
`EntityMapper<R>` is `R map(Object entity)`. `BeanMapEntityMapper(String... properties)` maps an entity to a `BeanMap`:
- **Flat keys for nested paths**: `"category.name"` is stored under the key `category.name`.
- Related entities are kept as already-loaded objects (proxies resolved with `DomainUtils.unproxy`); collections, maps and sets are copied to plain collections; `@Transient` values are included.
- Sets `beanClass`, `name`, `stringRepresentation`, `fields` and `id`.
- Treat the result as **read-only**.

Use it in your own queries; `JpaCrudService` applies the mapper **inside the transaction**, to every page of a `PagedList` (a `PagedList` is never flattened):
```java
var params = QueryParameters.with("active", true)
        .mapWith(new BeanMapEntityMapper("name", "category.name", "price"));
List rows = crudService.find(Product.class, params);   // elements are BeanMap
```
Ask only for the properties you will read: each one is read inside the transaction (nested paths load their relations).

## In the CRUD views (OSIV off)
With `dynamia.app.open-persistence-in-view=false`, `CrudController.query()` attaches a `BeanMapEntityMapper` built from the properties of the table/list descriptor (`ViewDescriptorProperties`, which also reads `params.bindings` and `bind` paths). A mapper you set explicitly is never replaced.
- Table rows, entity pickers, `DynamicListItemRenderer` and combobox/radiogroup automodel handle `BeanMap` rows.
- `delete()` and `newEntity()` accept `BeanMap` rows. An action that needs the entity **reloads it by id** (`CrudView.buildActionEvent` already does, with the form's collections). Use `EntityMapperSupport.toEntity` when you have only a row.
- Anything the view reads that is not a descriptor field (for example `row.getX().getY()` in a customizer) is not on a `BeanMap`: add the path to the descriptor or reload the entity.

## Typed DTOs
```java
PersonDTO dto = ObjectOperations.transform(person, PersonDTO.class);
List<PersonDTO> dtos = ObjectOperations.transformAll(persons, PersonDTO.class);
Map<String, Object> data = BeanTransformer.mapToMap(person, "name", "email");

OrderDTO dto = DomainUtils.autoDataTransferObject(order, OrderDTO.class);
```
`autoDataTransferObject` copies the common properties and handles entity references: a `String customer` in the DTO gets the customer's string form, a `Long customerId` gets its id, both can coexist. The DTO must be a POJO with getters and setters. Do the conversion where the entity is still attached (inside the service, with the references initialized, see `loading-collections.md`).

## Do not
- Return entities from REST endpoints when OSIV is off: map to `BeanMap` or a DTO inside the service.
- Mutate a `BeanMap` row and expect it to persist.
- Build `BeanMap`s for huge pages with `all` collections; list only the columns the view needs.
