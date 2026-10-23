# Charts

Adapted from ui-ux-pro-max chart guidance (MIT), see NOTICE.

## Choose the chart from the question
| Question | Use | Avoid |
|---|---|---|
| Trend over time | line (area if one series and volume matters) | pie, 3D |
| Compare categories | horizontal or vertical bars, sorted | many-slice pie |
| Part of a whole (2 to 5 parts) | stacked bar, or a single bar; pie or donut only for 2 or 3 slices | pies with similar slices |
| Distribution | histogram, box plot | averages alone |
| Relationship of two measures | scatter | dual axes that mislead |
| One number | big number with delta and sparkline | gauge dials |
| Exact lookup | table | chart |

## Rules
- Title says the finding or the metric and period. Axes labeled with units. Bars start at zero; lines may not.
- Direct labels beat legends. If there is a legend, keep it next to the data and in the same order.
- Color: 5 or fewer series; palette safe for color blindness; never color alone (add shape, pattern, label or position). Use one hue for one meaning across the product. Contrast 3:1 against the background, in dark mode too.
- Tooltips on hover and on tap and focus (keyboard), showing exact values; do not hide essential values in tooltips.
- Accessibility: a text summary or a data table alternative, `role="img"` with an `aria-label` on the chart, keyboard reachable data points when interactive.
- States: loading skeleton, empty ("no data for this period"), error with retry. Never an empty axis box.
- Mobile: simplify (fewer ticks, horizontal bars, 44px touch targets for interactive points), rotate or scroll only as a last resort.
- Large data: aggregate or sample before drawing; load the chart library on demand (`dynamia-ui:perf-review`).
- Dashboards: the most important number top-left, one message per card, consistent time range and filters.
