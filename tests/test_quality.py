"""Data-quality checks.

The rules are written once, proven against fixtures (clean passes, seeded
issues fail), and are the same rules the Silver notebook applies in Spark
against the real Lakehouse tables.

CI runs only the fixture tests: data/raw is gitignored and absent on runners.
The staged-extract test activates automatically once Olist is downloaded
locally (see data/README.md).
"""

from pathlib import Path

import pandas as pd
import pytest

FIXTURES = Path(__file__).parent / "fixtures"
REPO_ROOT = Path(__file__).parent.parent
RAW_ORDERS = REPO_ROOT / "data" / "raw" / "olist_orders_dataset.csv"
RAW_ITEMS = REPO_ROOT / "data" / "raw" / "olist_order_items_dataset.csv"

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
MIN_TIMESTAMP = pd.Timestamp("2016-01-01")
MAX_TIMESTAMP = pd.Timestamp("2019-01-01")


def load_fixture(name: str) -> pd.DataFrame:
    return pd.read_csv(FIXTURES / name, dtype=str, keep_default_na=False)


def check_no_orphan_items(orders: pd.DataFrame, items: pd.DataFrame) -> list[str]:
    known = set(orders["order_id"])
    orphans = sorted(set(items["order_id"]) - known)
    return [f"order_items.order_id '{oid}' has no matching order" for oid in orphans]


def check_no_negative_amounts(items: pd.DataFrame) -> list[str]:
    issues = []
    for column in ("price", "freight_value"):
        numeric = pd.to_numeric(items[column], errors="coerce")
        for oid, value in items.loc[numeric < 0, ["order_id", column]].itertuples(index=False):
            issues.append(f"{column} is negative ({value}) for order '{oid}'")
    return issues


def check_timestamps_within_bounds(orders: pd.DataFrame) -> list[str]:
    raw = orders["order_purchase_timestamp"]
    parsed = pd.to_datetime(raw, format=TIMESTAMP_FORMAT, errors="coerce")
    issues = []
    for idx in orders.index[parsed.isna()]:
        issues.append(
            f"order '{orders.loc[idx, 'order_id']}' has unparseable timestamp '{raw.loc[idx]}'"
        )
    out_of_bounds = (parsed.notna()) & ((parsed < MIN_TIMESTAMP) | (parsed > MAX_TIMESTAMP))
    for idx in orders.index[out_of_bounds]:
        issues.append(
            f"order '{orders.loc[idx, 'order_id']}' timestamp {raw.loc[idx]} is outside "
            f"{MIN_TIMESTAMP.date()}..{MAX_TIMESTAMP.date()}"
        )
    return issues


def check_no_duplicate_order_ids(orders: pd.DataFrame) -> list[str]:
    duplicated = orders.loc[orders["order_id"].duplicated(keep=False), "order_id"].unique()
    return [f"order_id '{oid}' appears more than once" for oid in sorted(duplicated)]


def check_no_blank_keys(orders: pd.DataFrame) -> list[str]:
    blank = orders["order_id"].str.strip() == ""
    return [f"row {idx} has a blank order_id" for idx in orders.index[blank]]


def check_row_count_between(count: int, lower: int, upper: int) -> list[str]:
    if lower <= count <= upper:
        return []
    return [f"row count {count:,} outside the expected range {lower:,}..{upper:,}"]


def assert_all_clean(issues_by_check: dict) -> None:
    failures = [f"{name}: {msg}" for name, issues in issues_by_check.items() for msg in issues]
    assert not failures, "\n".join(failures)


def run_all_checks(orders: pd.DataFrame, items: pd.DataFrame) -> dict:
    return {
        "orphan_items": check_no_orphan_items(orders, items),
        "negative_amounts": check_no_negative_amounts(items),
        "timestamp_bounds": check_timestamps_within_bounds(orders),
        "duplicate_order_ids": check_no_duplicate_order_ids(orders),
        "blank_keys": check_no_blank_keys(orders),
    }


def test_clean_fixture_passes_every_check():
    orders = load_fixture("orders_clean.csv")
    items = load_fixture("order_items_clean.csv")
    assert_all_clean(run_all_checks(orders, items))
    assert not check_row_count_between(len(orders), 1, 100)


def test_orphan_item_is_detected():
    issues = check_no_orphan_items(
        load_fixture("orders_seeded_issues.csv"),
        load_fixture("order_items_seeded_issues.csv"),
    )
    assert any("o_9999" in issue for issue in issues)


def test_negative_price_and_freight_are_detected():
    issues = check_no_negative_amounts(load_fixture("order_items_seeded_issues.csv"))
    assert any("price is negative" in issue for issue in issues)
    assert any("freight_value is negative" in issue for issue in issues)


def test_bad_timestamps_are_detected():
    issues = check_timestamps_within_bounds(load_fixture("orders_seeded_issues.csv"))
    assert any("unparseable" in issue for issue in issues)
    assert any("outside" in issue for issue in issues)


def test_duplicate_and_blank_keys_are_detected():
    orders = load_fixture("orders_seeded_issues.csv")
    assert any("o_0001" in issue for issue in check_no_duplicate_order_ids(orders))
    assert check_no_blank_keys(orders)


def test_row_count_bounds():
    assert not check_row_count_between(99_441, 90_000, 110_000)
    assert check_row_count_between(12, 90_000, 110_000)


@pytest.mark.skipif(
    not RAW_ORDERS.exists() or not RAW_ITEMS.exists(),
    reason="Olist not staged locally - data/raw is gitignored (see data/README.md)",
)
def test_staged_extract_has_expected_shape():
    orders = pd.read_csv(RAW_ORDERS, dtype=str, keep_default_na=False)
    items = pd.read_csv(RAW_ITEMS, dtype=str, keep_default_na=False)

    expected_order_columns = {"order_id", "customer_id", "order_status", "order_purchase_timestamp"}
    expected_item_columns = {"order_id", "order_item_id", "product_id", "price", "freight_value"}
    assert expected_order_columns <= set(orders.columns)
    assert expected_item_columns <= set(items.columns)
    assert not check_row_count_between(len(orders), 90_000, 110_000)
    assert not check_row_count_between(len(items), 100_000, 125_000)
