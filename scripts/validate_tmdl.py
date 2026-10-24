"""Parse every .tmdl file in the repo so model changes fail fast in CI.

Exits 0 with a skip message while the semantic model does not exist yet
(the Direct Lake model lands in a later sprint).
"""

from __future__ import annotations

import sys
from pathlib import Path

from tmdlparser import TMLDParser

REPO_ROOT = Path(__file__).resolve().parents[1]
SEARCH_ROOTS = [REPO_ROOT / "model", REPO_ROOT / "semantic"]


def find_tmdl_files() -> list[Path]:
    found: list[Path] = []
    for root in SEARCH_ROOTS:
        if root.is_dir():
            found.extend(sorted(root.rglob("*.tmdl")))
    return found


def main() -> None:
    files = find_tmdl_files()
    if not files:
        print("No .tmdl files under model/ or semantic/ yet - skipping (model lands later).")
        return

    parser = TMLDParser()
    failures: list[str] = []
    for path in files:
        try:
            objects = parser.parse_file(str(path))
        except Exception as exc:  # noqa: BLE001 - any parse error must fail the build
            failures.append(f"{path.relative_to(REPO_ROOT)}: {exc}")
            continue
        if not objects and path.stat().st_size > 0:
            failures.append(f"{path.relative_to(REPO_ROOT)}: parsed to zero objects")
            continue
        print(f"OK  {path.relative_to(REPO_ROOT)}  ({len(objects)} top-level objects)")

    if failures:
        print("\nTMDL validation failed:", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        sys.exit(1)
    print(f"Validated {len(files)} TMDL file(s).")


if __name__ == "__main__":
    main()
