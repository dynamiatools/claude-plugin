# View descriptors (YAML)

Read from the descriptor reader and factory (`YamlViewDescriptorReader`, `AbstractViewDescriptorFactory`) and `docs/frontend/FIELD_COMPONENTS.md` in framework 26.10. The same descriptor drives ZK and the Vue front end (served as JSON from `/apps/api/metadata/views/{id}`). `docs/backend/CORE_MODULES.md` shows a descriptor with `label:`, `required:` and `reference:` that does not match the reader: follow the keys below.

## Where and how found
- Files: `src/main/resources/META-INF/descriptors/**` (location `classpath*:META-INF/descriptors/**/*.*`). By convention `{Entity}{Form|Table|Tree|Json|Crud|Filters}.yml`; the real identity is `view:` + `beanClass:` (+ optional `device`), not the file name.
- `ViewDescriptorFactory.getDescriptor(beanClass, viewType)` finds it; a descriptor by `id:` is found with `getDescriptor(id)`.
- **No descriptor found: a default one is generated** (with all fields) and only a warning is logged. A missing or misspelled file looks like "all fields appear". Check the log.
- `extends: parent` merges with the descriptor of the superclass; `extends: <descriptor id>` merges with that descriptor; a descriptor with `autofields: true` also merges with its parent. Your fields override the inherited ones.
- Autoreload mode re-reads changed files in development.

## View level keys
| Key | Meaning |
|---|---|
| `view` | type: `form`, `table`, `tree`, `crud`, `json`, `entityfilters`, `dashboard`, `report`, or a custom type |
| `id` | optional id to reference it by name |
| `beanClass` | fully qualified entity (or DTO) class |
| `autofields` | `true` exposes every property, **including internal ones**; prefer `false` and list the fields |
| `fields` | map of field name to its settings (below); a bare `name:` is allowed |
| `hidden` | list of fields to hide when inheriting or using autofields |
| `groups` | map of group name to `label`, `icon`, `description`, `index`, `collapse`, `fields: [..]`, `params` |
| `layout` | free map handed to the renderer (`columns: 4`...) |
| `params` | view parameters (`orderBy`, `conditions`, paging, `crud` options...) |
| `customizer` | class name of a `ViewCustomizer` (no annotation needed) |
| `renderer` | class of a custom view renderer |
| `extends`, `device`, `messages` | inheritance, device variant, message bundle for labels |
| `actions` | map of action id to `label`, `description`, `icon`, `type`, `width`, `visible`, `attributes` |
| `sortFields` | list that fixes the field order |
| `debug` | extra logging for this descriptor |

## Field keys
| Key | Meaning |
|---|---|
| `label`, `description`, `icon`, `showIconOnly` | texts and icon (labels also come from message bundles by field name) |
| `component` | component id, see below; `componentClass` for a Java class; `componentCustomizer` for a `ComponentCustomizer` |
| `params` | component parameters (map) |
| `visible`, `required`, `optional` | flags (`required` also from `@NotNull`); `optional` for fields that may be absent |
| `index` | order |
| `class` / `fieldClass`, `type` | override the detected field class (`string`, `int`, `long`, `double`, `float`, `boolean`, `bigdecimal`, `date`, `localdate`, `localdatetime`, `localtime`, or a class name) |
| `path`, `variable` | nested path and variable name for virtual or bound fields |
| `attributes` | raw attributes for the rendered component |
| `action` | an action bound to the field (buttons/links) |

## Typical shapes
```yaml
view: form
beanClass: com.acme.app.domain.Order
autofields: false
customizer: com.acme.app.customizers.OrderFormCustomizer
fields:
  number:
    params: { span: 2 }
  customer:                      # @ManyToOne: combo or picker
    params: { entityAlias: customer }   # Vue/ZK entity picker needs the alias
  issueDate:
    component: dateselector
  total:
    params: { format: $###,###, constraint: "min 0" }
  lines:
    component: crudview          # embedded sub-CRUD for a @OneToMany
    params: { inplace: true, height: 400px }
groups:
  details: { label: Details, fields: [ total, lines ] }
layout: { columns: 4 }
```
```yaml
view: table
beanClass: com.acme.app.domain.Order
fields:
  number:
  total:
    params: { converter: converters.Currency, header: { align: right }, footer: { function: sum } }
  status:
    component: enumlabel
params: { orderBy: number desc }
```
- `crud`: `view: crud`, `beanClass`, optional `controller:` (a `CrudController` class) and `params`.
- `entityfilters`: the filter panel, same `fields` syntax. `tree`: hierarchies. `json`: projection for REST/autocomplete (`parent.id` dot paths, `params.conditions`).
- Converters seen: `converters.Date`, `converters.LocalDateTime`, `converters.Currency`.
- Virtual columns use `params.bindings` (paths read from the row; with `BeanMap` rows they are copied, see `bean-map-dto.md`).

## Components (ids you can set in `component:`)
Inputs and display: `textbox`, `intbox`, `combobox`, `checkbox`, `datebox`, `dateselector`, `label`, `link`, `coollabel`, `enumlabel`, `entityreflabel`, `entityrefpicker`, `entityrefmultipicker`, `crudview`; also `timebox`, `listbox`, `colorpicker`, `htmleditor`, `sliderbox`, `numberrangebox`, `imagebox`, `entityfileimage`, `enumiconimage`, `printercombobox`, `providermultipickerbox` (the Vue UI draws the one of the field's type for those it does not implement). Themes can register more (`rating`, `badge`, `status`, `moneyinput`, `quantityinput`, `colorpicker`; see `dynamia-platform:vue-frontend`). ZK-specific hints (`component:`, `controller:`, `customizer:`, `customView:`) are tolerated, but a descriptor that names a ZK class stays in a ZK module (design rule for the Vue/headless future).

## Customizing in code
- `ViewCustomizer<FormView<T>>` (reactive logic YAML cannot express: show/hide on change, load a combo), referenced by `customizer:`.
- `FieldCustomizer` / `ComponentCustomizer` for a field's component; `ViewDescriptorInterceptor` (`getTarget()`, `intercepted(descriptor)`) to adjust descriptors of many views at load; `ViewDescriptorReaderCustomizer` to affect the reading.
- Build a descriptor in code with `ViewDescriptorBuilder` when YAML is not enough (rare).

## Rules
- Keep `autofields: false` for any view shown to users; auto fields expose audit and internal columns.
- Fully qualified `beanClass` must match the entity; renaming a package breaks descriptors silently (default descriptor appears).
- Descriptors are metadata: do not put secrets or class paths a client should not see in `params` (they are served as JSON; `navigation-metadata.md`).
- Check a new key against the reader (`YamlViewDescriptorReader`) in the project's framework version; unknown keys are ignored without error.
- After editing a descriptor, open the screen: a CRUD that compiles can still fail on a bad descriptor.
