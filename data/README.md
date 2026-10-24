# data/ - never committed

Everything under `data/` except this README is gitignored: the Olist extract is
~50 MB and is regenerated from a public source instead of versioned.

## Get the dataset

1. Download **Olist Brazilian E-commerce** from Kaggle:
   <https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce>
2. Extract it so the CSVs sit in `data/olist/`:

```
data/
└── olist/
    ├── olist_orders_dataset.csv
    ├── olist_order_items_dataset.csv
    ├── olist_customers_dataset.csv
    ├── olist_products_dataset.csv
    └── ... (payments, reviews, sellers, geolocation, category translation)
```

## Stage it

```
python scripts/seed_data.py            # copies into data/raw + writes _manifest.json
python scripts/seed_data.py --dry-run  # show what would change
```

`data/raw/` is what gets uploaded to the Lakehouse `Files/raw` folder (drag and
drop in the Fabric UI, or `scripts/seed_data.py --to-fabric` with the Fabric CLI
installed). The script is idempotent: re-runs only copy files whose sha256 changed.

Once staged, `pytest` automatically runs the extract-shape test
(`test_staged_extract_has_expected_shape`); on CI it skips because `data/raw` does not exist there.
