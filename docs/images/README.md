# Screenshots

Screenshots live here (committed - they are small PNGs, not datasets).
Checklist mapped to the build; name them as listed so README links stay stable.

| File | What it shows | Captured |
|---|---|---|
| `01-workspace.png` | Fabric workspace: Lakehouse with `bronze`/`silver`/`gold` tables | ☐ |
| `02-lineage.png` | Lineage view Bronze → Silver → Gold | ☐ |
| `03-ci-green.png` | GitHub Actions run, all steps green, badge visible | ☐ |
| `04-silver-cleansing.png` | `01_silver_pyspark.py` output: rows dropped per rule | ☐ |
| `05-model-view.png` | Power BI model view: star + separate `dim_date` | ☐ |
| `06-results.png` | `docs/results.md` table with real numbers filled in | ☐ |

Rules of the pass: capture in two sprints (after Silver/Gold lands, after the
model lands), crop to the relevant panel, blur nothing that is not already
public, keep each file under ~500 KB.
