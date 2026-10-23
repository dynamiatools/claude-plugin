# dashboard

Dashboards made of widgets, from a `dashboard` view descriptor. Checked against `extensions/dashboard` (README, `core` API, ZK implementation) in framework 26.10. Modules: `dashboard.core` (UI-agnostic API, no ZK: `DashboardWidgetDefinition`, `WidgetContext`, `DashboardAction`, `UserInfoProvider`) and `dashboard` (ZK: `Dashboard`, `DashboardWidget`, `ChartjsDashboardWidget`, `ViewerDashboardWidget`, renderer). Vue: `@dynamia-tools/dashboard-sdk` and `dashboard-vue`.

## Declare the dashboard (YAML)
```yaml
view: dashboard
id: mainDashboard
fields:
  totalSales:                    # a slot; the key is the field name the REST call uses
    params:
      widget: total-sales        # the widget id
      range: lastMonth           # any custom parameter the widget reads
  newProducts:
    params:
      widget: products-table
      type: NEW
```
Layout (`columns`, `span`, `span-sm`, `span-xs`) lives in the descriptor. Install the page with a `ViewerPage(pageId, name, dashboardId)` in a `ModuleProvider` (ZK), or let the Vue shell render the descriptor.

## Write a widget
Implement `DashboardWidget`, or extend `AbstractDashboardWidget<View>`, and annotate with `@InstallDashboardWidget`:
```java
@InstallDashboardWidget
public class TotalSalesWidget extends AbstractDashboardWidget<Infobox> {
    public TotalSalesWidget() { setTitle("Total Sales"); }
    @Override public String getId() { return "total-sales"; }              // the id used in the descriptor
    @Override public void init(DashboardContext ctx) {                      // called on (re)initialization
        var range = (String) ctx.getField().getParam("range");             // params of the descriptor field
        ...
    }
    @Override public Infobox getView() { ... }                              // called on each render (ZK)
}
```
An instance lives as long as the dashboard page is open. `init` runs again when widgets are reinitialized; `getView` on each render.

## Serve it to a JS front end
`GET /apps/api/dashboard/{descriptorId}/widgets/{field}?param=value` returns a `DashboardWidgetResponse` (`field`, `widget`, `type`, `title`, flags, `data`). Only widgets declared as a field of the descriptor can be loaded; query parameters reach `DashboardWidget.update(params)`. A widget says how a JS client draws it with `getType()` (`DashboardWidgetTypes`: `chart`, `viewer`, `kpi`, `html`, `custom`) and `getData(WidgetContext)`:
- `ChartjsDashboardWidget` serves `ChartWidgetData` (Chart.js `type` and `data`) automatically.
- `ViewerDashboardWidget` serves `ViewerWidgetData` (descriptor id, view type, value).
- Others override `getType()` and `getData(...)`; `KpiWidgetData` exists for indicators.
Over REST, ZK widgets are initialized with a **headless** `DashboardContext`: they must not call `getDashboard()` or `getWindow()`. Widgets are authorized per request (a fix in 26.09 added the check), and the endpoints are not cached.

## Reports in dashboards
`widget: report` is provided by the reports extension (`dynamia-platform:extensions` `references/reports.md`).

## Do / don't
- Keep `init` cheap and cache heavy results; a dashboard renders many widgets.
- Read the tenant/account from the context, never from a static.
- One widget id per purpose; document its params next to the widget.
- Don't put ZK components in widgets you plan to serve to Vue: use `getData`.
