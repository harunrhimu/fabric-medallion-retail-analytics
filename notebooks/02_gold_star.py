"""Gold layer: dimensional star schema.

  gold.fact_orders  - one row per order (grain asserted before the write)
  gold.dim_customer - customer attributes
  gold.dim_product  - product attributes
  gold.dim_date     - generated calendar table, deliberately separate from the
                      order data so time intelligence never depends on it

Run in a Fabric notebook attached to the Lakehouse (PySpark kernel).
Silver must be built first: notebooks/01_silver_pyspark.py
"""

from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F

SILVER_DB = "silver"
BRONZE_DB = "bronze"
GOLD_DB = "gold"


def write_gold(df, table: str) -> None:
    (
        df.write.format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(table)
    )


def build_dim_customer(spark: SparkSession):
    df = spark.table(f"{BRONZE_DB}.customers")
    for column in df.columns:
        df = df.withColumn(column, F.trim(F.col(column)))
    df = df.where(F.col("customer_id").isNotNull() & (F.col("customer_id") != ""))
    df = df.dropDuplicates(["customer_id"])
    df = df.withColumn("customer_key", F.row_number().over(Window.orderBy("customer_id")))
    return df.select(
        "customer_key",
        "customer_id",
        "customer_unique_id",
        F.col("customer_zip_code_prefix").alias("zip_code"),
        "customer_city",
        F.col("customer_state").alias("state"),
    )


def build_dim_product(spark: SparkSession):
    df = spark.table(f"{BRONZE_DB}.products")
    for column in df.columns:
        df = df.withColumn(column, F.trim(F.col(column)))
    df = df.where(F.col("product_id").isNotNull() & (F.col("product_id") != ""))
    df = df.dropDuplicates(["product_id"])
    df = df.withColumn("product_key", F.row_number().over(Window.orderBy("product_id")))
    for column in (
        "product_weight_g",
        "product_length_cm",
        "product_height_cm",
        "product_width_cm",
    ):
        if column in df.columns:
            df = df.withColumn(column, F.col(column).cast("double"))
    return df.select(
        "product_key",
        "product_id",
        F.col("product_category_name").alias("category_name"),
        "product_weight_g",
        "product_length_cm",
        "product_height_cm",
        "product_width_cm",
    )


def build_dim_date(spark: SparkSession, orders):
    bounds = orders.agg(
        F.min("order_purchase_timestamp").alias("lo"),
        F.max("order_purchase_timestamp").alias("hi"),
    ).first()
    if bounds["lo"] is None:
        raise ValueError(
            "silver.orders has no valid purchase timestamps - run 01_silver_pyspark.py first"
        )

    start = bounds["lo"].date()
    day_count = (bounds["hi"].date() - start).days + 1
    dates = spark.range(0, day_count).withColumn(
        "full_date", F.date_add(F.lit(start), F.col("id").cast("int"))
    )
    return dates.select(
        F.date_format("full_date", "yyyyMMdd").cast("int").alias("date_key"),
        "full_date",
        F.year("full_date").alias("calendar_year"),
        F.month("full_date").alias("calendar_month"),
        F.date_format("full_date", "MMMM").alias("month_name"),
        F.quarter("full_date").alias("calendar_quarter"),
        F.date_format("full_date", "EEEE").alias("day_name"),
        F.when(F.dayofweek("full_date").isin(1, 7), F.lit(1))
        .otherwise(F.lit(0))
        .alias("is_weekend"),
        F.weekofyear("full_date").alias("week_of_year"),
    )


def build_fact_orders(spark: SparkSession, dim_customer):
    orders = spark.table(f"{SILVER_DB}.orders")
    items = spark.table(f"{SILVER_DB}.order_items")

    item_aggregate = items.groupBy("order_id").agg(
        F.count(F.lit(1)).alias("item_count"),
        F.sum("price").alias("product_revenue"),
        F.sum("freight_value").alias("freight_total"),
    )

    fact = orders.join(item_aggregate, on="order_id", how="left")
    customer_keys = dim_customer.select("customer_key", "customer_id")
    fact = fact.join(customer_keys, on="customer_id", how="left")

    fact = fact.withColumn("item_count", F.coalesce(F.col("item_count"), F.lit(0)).cast("long"))
    fact = fact.withColumn(
        "product_revenue", F.round(F.coalesce(F.col("product_revenue"), F.lit(0.0)), 2)
    )
    fact = fact.withColumn(
        "freight_total", F.round(F.coalesce(F.col("freight_total"), F.lit(0.0)), 2)
    )
    fact = fact.withColumn(
        "order_total", F.round(F.col("product_revenue") + F.col("freight_total"), 2)
    )
    fact = fact.withColumn(
        "date_key", F.date_format("order_purchase_timestamp", "yyyyMMdd").cast("int")
    )
    fact = fact.withColumn(
        "days_to_deliver",
        F.datediff("order_delivered_customer_date", "order_purchase_timestamp"),
    )
    fact = fact.withColumn(
        "arrived_late",
        F.when(
            F.col("order_delivered_customer_date").isNull()
            | F.col("order_estimated_delivery_date").isNull(),
            F.lit(None).cast("int"),
        )
        .when(
            F.col("order_delivered_customer_date") > F.col("order_estimated_delivery_date"),
            F.lit(1),
        )
        .otherwise(F.lit(0)),
    )

    return fact.select(
        "order_id",
        "customer_key",
        "date_key",
        "order_status",
        F.col("order_purchase_timestamp").alias("purchase_ts"),
        F.col("order_delivered_customer_date").alias("delivered_ts"),
        F.col("order_estimated_delivery_date").alias("estimated_delivery_ts"),
        "days_to_deliver",
        "arrived_late",
        "item_count",
        "product_revenue",
        "freight_total",
        "order_total",
    )


def main() -> None:
    spark = SparkSession.builder.appName("gold_star").getOrCreate()
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {GOLD_DB}")

    orders = spark.table(f"{SILVER_DB}.orders")
    dim_customer = build_dim_customer(spark)
    dim_product = build_dim_product(spark)
    dim_date = build_dim_date(spark, orders)
    fact = build_fact_orders(spark, dim_customer)

    silver_rows = orders.count()
    fact_rows = fact.count()
    if fact_rows != silver_rows:
        raise ValueError(f"fact grain broken: silver.orders={silver_rows}, fact_orders={fact_rows}")

    orphan_customers = fact.where(F.col("customer_key").isNull()).count()
    if orphan_customers:
        raise ValueError(f"{orphan_customers} fact rows did not resolve to dim_customer")

    outside_calendar = fact.join(dim_date, on="date_key", how="left_anti").count()
    if outside_calendar:
        raise ValueError(f"{outside_calendar} fact rows fall outside dim_date")

    tables = {
        "fact_orders": fact,
        "dim_customer": dim_customer,
        "dim_product": dim_product,
        "dim_date": dim_date,
    }
    for name, df in tables.items():
        write_gold(df, f"{GOLD_DB}.{name}")

    print(f"{'table':<40}{'rows':>12}")
    for name, df in tables.items():
        print(f"{GOLD_DB + '.' + name:<40}{df.count():>12,}")


if __name__ == "__main__":
    main()
