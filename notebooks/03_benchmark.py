"""Benchmark: the same business question answered from Silver vs from Gold.

Question: "monthly revenue by year, excluding canceled orders".

Silver path joins the flat cleansed tables on every run; Gold path hits the
pre-aggregated star with an integer date key. Warm-up run discarded, then the
best of RUNS timed runs is reported as markdown you paste into docs/results.md.

Run in a Fabric notebook attached to the Lakehouse after 01 and 02 succeeded.
"""

import time

from pyspark.sql import SparkSession

RUNS = 3

QUERIES = {
    "Silver (flat join path)": """
        SELECT
            YEAR(o.order_purchase_timestamp) AS sale_year,
            MONTH(o.order_purchase_timestamp) AS sale_month,
            SUM(i.price + i.freight_value) AS revenue
        FROM silver.orders AS o
        INNER JOIN silver.order_items AS i ON i.order_id = o.order_id
        WHERE o.order_status <> 'canceled'
        GROUP BY YEAR(o.order_purchase_timestamp), MONTH(o.order_purchase_timestamp)
    """,
    "Gold (star join path)": """
        SELECT
            d.calendar_year AS sale_year,
            d.calendar_month AS sale_month,
            SUM(f.order_total) AS revenue
        FROM gold.fact_orders AS f
        INNER JOIN gold.dim_date AS d ON d.date_key = f.date_key
        WHERE f.order_status <> 'canceled'
        GROUP BY d.calendar_year, d.calendar_month
    """,
}


def time_query(spark: SparkSession, query: str) -> float:
    spark.sql(query).collect()
    best = float("inf")
    for _ in range(RUNS):
        started = time.perf_counter()
        spark.sql(query).collect()
        best = min(best, (time.perf_counter() - started) * 1000)
    return best


def main() -> None:
    spark = SparkSession.builder.appName("benchmark").getOrCreate()

    timings = {}
    for label, query in QUERIES.items():
        timings[label] = time_query(spark, query)
        print(f"{label:<30}{timings[label]:>10,.0f} ms")

    before = timings["Silver (flat join path)"]
    after = timings["Gold (star join path)"]
    print("\nPaste this row into docs/results.md:\n")
    print("| Path | Before (Silver) | After (Gold) | Speedup |")
    print("|---|---:|---:|---:|")
    row = f"| Monthly revenue, best of {RUNS} runs | {before:,.0f} ms | {after:,.0f} ms |"
    row += f" {before / after:,.1f}x |"
    print(row)


if __name__ == "__main__":
    main()
