"""Bronze layer: land every staged raw CSV as a Delta table, untransformed.

Run in a Fabric notebook (PySpark kernel) attached to the Lakehouse.
Prereq: scripts/seed_data.py staged the Olist extract into <lakehouse>/Files/raw.

Ingest is idempotent: every table is rebuilt from the raw files on each run.
Only lineage metadata (source_file, ingested_at) is added - no business logic.
"""

from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

RAW_DIR = "/lakehouse/Files/raw"
BRONZE_DB = "bronze"


def table_name(filename: str) -> str:
    stem = Path(filename).stem
    if stem.startswith("olist_"):
        stem = stem[len("olist_") :]
    if stem.endswith("_dataset"):
        stem = stem[: -len("_dataset")]
    return stem


def ingest(spark: SparkSession, path: Path) -> int:
    df = spark.read.option("header", True).option("mode", "PERMISSIVE").csv(str(path))
    df = df.withColumn("source_file", F.lit(path.name))
    df = df.withColumn("ingested_at", F.current_timestamp())
    row_count = df.count()
    (
        df.write.format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(f"{BRONZE_DB}.{table_name(path.name)}")
    )
    return row_count


def main() -> None:
    spark = SparkSession.builder.appName("bronze_ingest").getOrCreate()
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {BRONZE_DB}")

    files = sorted(Path(RAW_DIR).glob("*.csv"))
    if not files:
        raise FileNotFoundError(
            f"No CSVs under {RAW_DIR}. Run scripts/seed_data.py and upload data/raw "
            "into the Lakehouse Files area first."
        )

    print(f"{'table':<45}{'rows':>12}")
    total = 0
    for path in files:
        rows = ingest(spark, path)
        total += rows
        print(f"{BRONZE_DB + '.' + table_name(path.name):<45}{rows:>12,}")
    print(f"{'TOTAL':<45}{total:>12,}")


if __name__ == "__main__":
    main()
