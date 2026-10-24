# ADR-002: Separate generated dim_date instead of dates-as-columns

**Status:** accepted · 2026-10-24

## Context

Every retail question in this repo is time-shaped (monthly revenue, YoY,
seasonality). Dates could be derived on the fly from `purchase_ts` inside each
query - that is how the `*_before.sql` files are written.

## Decision

Generate `gold.dim_date` as a full calendar span (min..max purchase date) with
`date_key` (`yyyyMMdd` integer) and build `fact_orders.date_key` during the
Gold build. Time filters and groupings always go through the date dimension.

## Consequences

- Queries filter an integer key instead of applying `YEAR()`/`MONTH()` to a
  timestamp per row (`sql/01_monthly_revenue_*` measures the difference).
- The calendar carries attributes no timestamp expression can (month name,
  quarter, weekend flag, ISO week) so time intelligence in DAX needs no
  calculation columns.
- The dimension is rebuilt whenever the order span grows - one notebook run,
  asserted against the fact table before write.

## Alternatives rejected

- **Derived dates in each query:** flexible, but every query re-implements the
  calendar and pays the row-wise function cost (see Q1/Q2 before files).
- **Only the dates that appear in the data:** collapses weekends/holidays that
  have zero orders, which breaks running totals and period-over-period DAX.
