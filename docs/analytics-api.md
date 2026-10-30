# Dashboard analytics API

All endpoints are read-only and use the canonical `Ticket` records. They are available under `/api/analytics/`.

## Endpoints

- `GET /api/analytics/summary/` — executive KPIs and comparison with the latest two complete months.
- `GET /api/analytics/trends/` — monthly ticket volume/resolution rate and weekly ticket volume.
- `GET /api/analytics/breakdowns/` — subcategory, plant, channel, assignee and average resolution-time breakdowns.
- `GET /api/analytics/backlog/` — open-ticket attention list and age/overdue counts.
- `GET /api/analytics/tickets/` — paginated ticket drill-down.

## Shared filters

Optional query parameters:

| Parameter | Meaning |
|---|---|
| `month` | Created month, `YYYY-MM` |
| `date_from`, `date_to` | Inclusive created-date bounds, `YYYY-MM-DD` |
| `plant` | Exact plant code |
| `category` | IT, SAP, UNASSIGNED or OTHER |
| `subcategory` | Exact subcategory |
| `assignee` | Exact assignee |
| `status` | RESOLVED, IN_PROGRESS, ON_HOLD, OPEN or UNKNOWN |
| `channel` | WEBAPP, EMAIL, OTHER or UNKNOWN |

Filters are combined with AND. Invalid date formats, reversed date ranges, and unsupported choice values return HTTP 400.

The monthly trend intentionally ignores the `month` filter (but retains other filters), matching the reference dashboard's behavior: selecting a month filters KPIs and other views without collapsing the monthly history chart.

## KPI definitions and reference alignment

- Reporting window begins **1 April 2026**. Records created before that date are treated as legacy and excluded from operational KPIs and trends.
- Legacy tickets remain in the open backlog; absence from the operational reporting window does not imply closure.
- Total tickets raised = non-legacy tickets in the selected filter context.
- Resolution rate = resolved non-legacy tickets / total non-legacy tickets.
- Open backlog = all non-resolved tickets in the selected filter context, including legacy records.
- Average resolution days uses the imported `resolution_days`; if absent, it falls back to `resolved_at - created_at_source`. This supports mapping the source report's Updated At field to `resolved_at` when it is the available resolution-time proxy.
- Median resolution days uses the upper middle sorted observation for even-sized samples, matching the supplied HTML reference implementation.
- Resolved within one day = resolved tickets with resolution duration <= 1 day / resolved non-legacy tickets.
- Average tickets per week = non-legacy tickets / distinct ISO weeks represented in those tickets.
- Oldest open age is measured against the latest created date in the filtered data (the report's data-as-of date), not the server clock.
- Monthly comparisons use the latest complete month available in the dataset and the preceding month. If the dataset's latest month is the current calendar month, that current month is treated as partial.

The original HTML reference also contains derived labels and management narrative. Those narrative rules are not yet implemented as API output; this phase exposes the underlying aggregates for the frontend to render.

## Examples

```http
GET /api/analytics/summary/?plant=3001&category=SAP
GET /api/analytics/trends/?date_from=2026-04-01&date_to=2026-10-31
GET /api/analytics/breakdowns/?status=RESOLVED
GET /api/analytics/backlog/?limit=100
GET /api/analytics/tickets/?scope=within_one_day&page=1&page_size=50
```

Ticket list scopes: `all`, `operational`, `resolved`, `open`, `within_one_day`.
