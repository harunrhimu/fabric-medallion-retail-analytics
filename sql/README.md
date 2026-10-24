# SQL tuning set

Four business queries, each written twice: the version you first reach for
(`*_before.sql`) and the version you ship (`*_after.sql`). Both must return
identical rows - only the cost differs.

| Files | Business question | Anti-pattern removed |
|---|---|---|
| `01_monthly_revenue_*` | 2017 monthly revenue vs 2016 | `YEAR()`/`MONTH()` on the timestamp column + two full aggregation passes instead of one scan on `date_key` + `LAG` |
| `02_top_customers_*` | Top 10 customers by 2017 revenue with AOV | Correlated `CROSS APPLY` evaluated for every customer instead of one pre-aggregated CTE |
| `03_late_orders_*` | Late deliveries per state + share | Per-row `DATEDIFF` + redundant `OR` instead of the `arrived_late` flag computed once in Gold |
| `04_category_revenue_*` | Revenue per product category | One correlated subquery per category instead of a single join + `GROUP BY` |

## How to measure (this is the part that must not be skipped)

1. Open the **Fabric SQL analytics endpoint** (or SSMS / Azure Data Studio) on the Lakehouse.
2. Run each query **twice** - the first run warms the cache and is discarded.
3. Capture the client-reported duration of run 2, then repeat 5 times and keep the **median**.
4. Paste the numbers into [`docs/results.md`](../docs/results.md) in the moment you measure them.

Queries are written in T-SQL (the dialect the Fabric SQL analytics endpoint serves)
and are linted in CI with `sqlfluff` (`dialect = tsql` in `.sqlfluff`).
