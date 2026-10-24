# Measured results

> [!warning] Capture numbers in the moment
> Timings cannot be recreated faithfully weeks later. Measure, paste, commit -
> in that order, the same day. Everything below marked *not yet measured* is
> expected to be filled during the build, not afterwards.

## 1. Same business query: Silver path vs Gold path

Source: `notebooks/03_benchmark.py` (prints the row to paste here).
Question: *monthly revenue by year, excluding canceled orders.* Warm-up run
discarded, best of 3 runs.

| Path | Before (Silver) | After (Gold) | Speedup |
|---|---:|---:|---:|
| Monthly revenue | *not yet measured* | *not yet measured* | *not yet measured* |

Example of the framing this table should end with:
*"Silver-layer star join took 14 min - the Gold star answered the same question in 3 min 20 s."*

## 2. SQL tuning set

Source: `sql/*_before.sql` vs `sql/*_after.sql`. Method: Fabric SQL analytics
endpoint, run twice (first warms cache), median of 5 runs - see `sql/README.md`.

| Query | Question | Before | After | Speedup |
|---|---|---:|---:|---:|
| Q1 `01_monthly_revenue_*` | 2017 monthly revenue vs 2016 | *not yet measured* | *not yet measured* | |
| Q2 `02_top_customers_*` | Top 10 customers by 2017 revenue | *not yet measured* | *not yet measured* | |
| Q3 `03_late_orders_*` | Late deliveries per state | *not yet measured* | *not yet measured* | |
| Q4 `04_category_revenue_*` | Revenue per product category | *not yet measured* | *not yet measured* | |

## 3. Pipeline numbers

| Metric | Value |
|---|---|
| Raw rows ingested (Bronze) | *from `00_bronze_ingest.py` output* |
| `silver.orders` output rows + rows dropped per rule | *from `01_silver_pyspark.py` output* |
| Full Bronze → Silver → Gold build duration | *not yet measured* |
| DAX query time before/after (model sprint) | *not yet measured* |
| Capacity cost impact (if measurable on trial) | *not yet measured* |
