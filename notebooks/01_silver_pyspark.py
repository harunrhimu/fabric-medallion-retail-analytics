"""Silver layer: dedupe, null handling and type coercion for orders + order_items.

Each rule answers a defect that exists in the raw Olist extract:
  * exact duplicate rows / repeated order keys -> one row per business key
  * blank or null order_id / customer_id       -> row dropped (count reported)
  * unparseable or out-of-range timestamps     -> NULL, rows without a purchase
                                                 timestamp are dropped (count reported)
  * negative price / freight values            -> NULL; items without a usable
                                                 price are dropped (count reported)

Run in a Fabric notebook attached to the Lakehouse (PySpark kernel).
"""

from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F
from pyspark.sql.types import StringType

BRONZE_DB = "bronze"
SILVER_DB = "silver"
TS_FORMAT = "yyyy-MM-dd HH:mm:ss"
TS_MIN = "2016-01-01 00:00:00"
TS_MAX = "2019-01-01 00:00:00"

ORDER_TIMESTAMP_COLUMNS = (
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
)
ITEM_TIMESTAMP_COLUMNS = ("shipping_limit_date",)


def trim_strings(df):
    for field in df.schema.fields:
        if isinstance(field.dataType, StringType):
            df = df.withColumn(field.name, F.trim(F.col(field.name)))
    return df


def require_columns(df, required: set[str], table: str):
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"{table} is missing columns {missing} - schema drift in the raw extract")
    return df


def coerce_timestamps(df, columns):
    lower = F.lit(TS_MIN).cast("timestamp")
    upper = F.lit(TS_MAX).cast("timestamp")
    for name in columns:
        if name in df.columns:
            parsed = F.to_timestamp(F.col(name), TS_FORMAT)
            df = df.withColumn(name, F.when(parsed.between(lower, upper), parsed))
    return df


def write_silver(df, table: str) -> None:
    (
        df.write.format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(table)
    )


def build_silver_orders(spark: SparkSession) -> dict:
    df = trim_strings(spark.table(f"{BRONZE_DB}.orders"))
    df = require_columns(
        df, {"order_id", "customer_id", "order_status", "order_purchase_timestamp"}, "bronze.orders"
    )
    input_rows = df.count()

    df = df.dropDuplicates()
    after_exact = df.count()

    window = Window.partitionBy("order_id").orderBy(
        F.col("order_purchase_timestamp").desc_nulls_last()
    )
    df = df.withColumn("_rn", F.row_number().over(window)).where(F.col("_rn") == 1).drop("_rn")
    after_key_dedupe = df.count()

    blank_key = df.where(
        F.col("order_id").isNull()
        | (F.col("order_id") == "")
        | F.col("customer_id").isNull()
        | (F.col("customer_id") == "")
    ).count()
    df = df.where(
        F.col("order_id").isNotNull()
        & (F.col("order_id") != "")
        & F.col("customer_id").isNotNull()
        & (F.col("customer_id") != "")
    )

    df = coerce_timestamps(df, ORDER_TIMESTAMP_COLUMNS)
    null_purchase = df.where(F.col("order_purchase_timestamp").isNull()).count()
    df = df.where(F.col("order_purchase_timestamp").isNotNull())
    output_rows = df.count()

    write_silver(df, f"{SILVER_DB}.orders")
    return {
        "input_rows": input_rows,
        "exact_duplicates_removed": input_rows - after_exact,
        "repeated_order_keys_removed": after_exact - after_key_dedupe,
        "blank_order_or_customer_dropped": blank_key,
        "invalid_purchase_ts_dropped": null_purchase,
        "output_rows": output_rows,
    }


def build_silver_order_items(spark: SparkSession) -> dict:
    df = trim_strings(spark.table(f"{BRONZE_DB}.order_items"))
    df = require_columns(
        df,
        {"order_id", "order_item_id", "product_id", "price", "freight_value"},
        "bronze.order_items",
    )
    input_rows = df.count()

    df = df.dropDuplicates()
    after_exact = df.count()

    window = Window.partitionBy("order_id", "order_item_id").orderBy(
        F.col("price").desc_nulls_last()
    )
    df = df.withColumn("_rn", F.row_number().over(window)).where(F.col("_rn") == 1).drop("_rn")

    blank_key = df.where(F.col("order_id").isNull() | (F.col("order_id") == "")).count()
    df = df.where(F.col("order_id").isNotNull() & (F.col("order_id") != ""))

    for name in ("price", "freight_value"):
        casted = F.col(name).cast("double")
        negative_null = F.when(casted < 0, F.lit(None).cast("double")).otherwise(casted)
        df = df.withColumn(name, negative_null)

    invalid_price = df.where(F.col("price").isNull()).count()
    df = df.where(F.col("price").isNotNull())

    df = coerce_timestamps(df, ITEM_TIMESTAMP_COLUMNS)
    output_rows = df.count()

    write_silver(df, f"{SILVER_DB}.order_items")
    return {
        "input_rows": input_rows,
        "exact_duplicates_removed": input_rows - after_exact,
        "blank_order_id_dropped": blank_key,
        "negative_or_unparseable_price_dropped": invalid_price,
        "output_rows": output_rows,
    }


def main() -> None:
    spark = SparkSession.builder.appName("silver_cleansing").getOrCreate()
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {SILVER_DB}")

    for table, summary in (
        ("orders", build_silver_orders(spark)),
        ("order_items", build_silver_order_items(spark)),
    ):
        print(f"\nsilver.{table}")
        for label, value in summary.items():
            print(f"  {label:<36}{value:>12,}")


if __name__ == "__main__":
    main()
