"""Stage the local Olist CSVs into data/raw and optionally push them into Fabric.

Olist is never committed to Git (.gitignore blocks data/*). This script is the
reproducible path from "downloaded Olist" to "raw files in the Lakehouse Files area".

Usage:
    python scripts/seed_data.py                     # stage data/olist -> data/raw
    python scripts/seed_data.py --dry-run           # report what would change
    python scripts/seed_data.py --to-fabric --fabric-raw-path abfss://<ws>@onelake.dfs.fabric.microsoft.com/<lh>.Files/raw

Idempotent: a file is copied only when missing or when its sha256 changed.
A manifest (rows, bytes, sha256 per file) is written to data/raw/_manifest.json.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = REPO_ROOT / "data" / "olist"
DEFAULT_DEST = REPO_ROOT / "data" / "raw"
MANIFEST_NAME = "_manifest.json"

CORE_FILES = {
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "customers": "olist_customers_dataset.csv",
    "products": "olist_products_dataset.csv",
}
OPTIONAL_FILES = {
    "order_payments": "olist_order_payments_dataset.csv",
    "order_reviews": "olist_order_reviews_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def count_rows(path: Path) -> int:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return max(sum(1 for _ in csv.reader(handle)) - 1, 0)


def stage(source: Path, dest: Path, dry_run: bool) -> dict:
    missing = [name for name in CORE_FILES.values() if not (source / name).is_file()]
    if missing:
        sys.exit(
            f"Missing core Olist files in {source}: {', '.join(missing)}\n"
            "Download the dataset first - see data/README.md."
        )

    if not dry_run:
        dest.mkdir(parents=True, exist_ok=True)

    entries: list[dict] = []
    for label, filename in {**CORE_FILES, **OPTIONAL_FILES}.items():
        src = source / filename
        if not src.is_file():
            entries.append({"dataset": label, "file": filename, "status": "absent"})
            continue

        digest = sha256_of(src)
        target = dest / filename
        if target.is_file() and sha256_of(target) == digest:
            status = "unchanged"
        else:
            status = "updated" if target.is_file() else "copied"
            if not dry_run:
                shutil.copy2(src, target)

        entries.append(
            {
                "dataset": label,
                "file": filename,
                "status": status,
                "rows": count_rows(src),
                "bytes": src.stat().st_size,
                "sha256": digest,
            }
        )

    staged = [e for e in entries if e["status"] not in ("absent",)]
    if not staged:
        sys.exit("No files were staged.")

    manifest = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "source": str(source),
        "files": entries,
    }
    if not dry_run:
        (dest / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def push_to_fabric(dest: Path, raw_path: str, dry_run: bool) -> None:
    if shutil.which("fab") is None:
        sys.exit(
            "`fab` (Microsoft Fabric CLI) not found on PATH.\n"
            "Install it with `pip install fab`, or copy data/raw/* into the "
            "Lakehouse Files > raw folder from the Fabric UI instead."
        )
    target = raw_path.rstrip("/")
    for src in sorted(dest.glob("*.csv")):
        cmd = ["fab", "cp", str(src), f"{target}/{src.name}"]
        if dry_run:
            print("DRY RUN:", " ".join(cmd))
            continue
        print("Uploading", src.name)
        subprocess.run(cmd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="Local Olist folder")
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST, help="Staging folder")
    parser.add_argument("--dry-run", action="store_true", help="Report only, write nothing")
    parser.add_argument(
        "--to-fabric",
        action="store_true",
        help="Also upload staged files to the Lakehouse Files area via the fab CLI",
    )
    parser.add_argument(
        "--fabric-raw-path",
        default=os.environ.get("FABRIC_RAW_PATH", ""),
        help="abfss://... path to <lakehouse>.Files/raw (or set FABRIC_RAW_PATH)",
    )
    args = parser.parse_args()

    manifest = stage(args.source, args.dest, args.dry_run)
    for entry in manifest["files"]:
        rows = f"{entry['rows']:,} rows" if "rows" in entry else "-"
        print(f"{entry['status']:>10}  {entry['file']}  ({rows})")
    print(f"Manifest: {args.dest / MANIFEST_NAME}{' (dry run)' if args.dry_run else ''}")

    if args.to_fabric:
        if not args.fabric_raw_path:
            sys.exit("--to-fabric requires --fabric-raw-path or FABRIC_RAW_PATH.")
        push_to_fabric(args.dest, args.fabric_raw_path, args.dry_run)


if __name__ == "__main__":
    main()
