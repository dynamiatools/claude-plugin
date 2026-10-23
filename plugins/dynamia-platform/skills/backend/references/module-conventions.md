# ModuleProvider conventions

Observed in `examples/` and `extensions/` of framework 26.10, plus the rules the navigation code enforces (`ModuleContainer`). **Follow the project's own naming first.**

## Shape
```java
@Provider
public class CatalogModuleProvider implements ModuleProvider {
    @Override
    public Module getModule() {
        return new Module("catalog", "Catalog")
                .icon("film")
                .position(1)
                .addPage(
                        new CrudPage("movies", "Movies", Movie.class).icon("film"),
                        new CrudPage("genres", "Genres", Genre.class).icon("tags"),
                        new ConfigPage("settings", "Settings", "MoviesSettingsCFG").icon("settings"));
    }
}
```
`ModuleProvider` is a functional interface (`Module getModule()`). The provider is a bean: annotate it with `@Provider` (the convention; `@Component` also works, SaaS uses it).

## Naming
| Thing | Convention |
|---|---|
| Class | `<Area>ModuleProvider`, one per module; `<Area>ProfileModuleProvider` etc. when one module is fed from several places |
| Package | `providers` in an application, `ui` (or the module's `ui` package) in an extension |
| Module id | short, lower case, one word (`catalog`, `library`, `setup`, `system`, `saas`) |
| Group id | lower case (`security`, `examples`) |
| Page id | camelCase, plural for CRUD (`movies`, `accountPayments`), unique inside the whole container |
| Name (label) | Title Case English in code (`"Payments Methods"`); localized labels go through the navigation labels, check the project's version |
| Icon | one short word in the icon set the theme uses (`settings`, `users`, `film`) |
| Config page | `ConfigPage(id, name, "<ParametersGroup>")`; the examples name the group `...CFG` or `...Cfg`, follow the project |

## Rules enforced by the navigation code
- **Ids make URLs.** `getVirtualPath()` is `module/group/page` (for example `crm/sales/orders`), and navigation paths and restrictions are based on it. Choose ids once; renaming one breaks links and permissions.
- **Same module id = merge.** Two providers that return a module with the same id are merged by `ModuleContainer` (page groups merge recursively). That is how an extension adds pages to `system`. Use it deliberately.
- **Duplicate page ids fail** at install with a "page already exists" error, even across providers of the same module.
- Order: `position(double)`, lower first; negative puts a module before the rest (SaaS uses `-1`). Pages and groups also take `position`.
- `featured()` / `featured(int priority)` marks pages for the home/dashboard; keep it to a few.
- `CrudPage(id, name, Class)` is the usual form; `CrudPage(Class)` and `CrudPage(id, name, Class, crudServiceName)` (custom `CrudService`) also exist.
- `new Page(id, name, path)` where the path is `classpath:/pages/x.zul`, a web path, or use `ExternalPage` for outside URLs.
- Alternative fluent form: `Module.builder("id", "Name", "icon", position)` (`JavaModuleBuilder`). Do not mix styles inside one provider.

## Do
- Keep providers declarative: no queries, no service calls, no conditions on the current user. Per-user visibility belongs to navigation restrictions (`NavigationRestriction`), not to the provider.
- One provider per cohesive area; put the module and its entities in the same package family.
- Make a new module's pages reachable from the home with the fewest levels (module, optional group, page).

## Don't
- Don't create a module per entity.
- Don't reuse a page id in another module to "share" a screen.
- Don't build `Module` objects as a side effect elsewhere and also register them from a provider.

## Checklist for a new area
1. Entity extends `BaseEntity`, has its `{Entity}Form.yml` / `{Entity}Table.yml` descriptors.
2. Provider class named `<Area>ModuleProvider` with `@Provider`.
3. Module id and page ids chosen, checked against existing ones (`grep -rn 'new Module(' src`).
4. Start the app and open `<module>/<page>`; check the left menu and the REST metadata `GET /apps/api/metadata/navigation`.
