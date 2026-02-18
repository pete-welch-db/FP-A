# Milacron FP&A — Databricks Demo

Production-realistic presales demo showing how Databricks becomes Milacron's
financial analytics and planning backbone by ingesting OneStream-modeled data
into a governed Unity Catalog lakehouse with automated FP&A workflows.

## Architecture

```
OneStream CSVs → UC Volume → DLT (Bronze/Silver/Gold) → Streamlit App
                                                       → Genie Space
                                                       → AI/BI Dashboard
                                                       → UC Metric Views
                                        ML (LightGBM) → ml_revenue_forecast
```

## Quick Start

```bash
# 1. Copy and fill in environment variables
cp env.example .env

# 2. Validate the bundle
databricks bundle validate

# 3. Deploy to your workspace
databricks bundle deploy --force --var warehouse_id=<your_warehouse_id>

# 4. Run the full data pipeline
databricks bundle run data_pipeline

# 5. Capture Genie Space ID and Dashboard URL
./scripts/update_env_ids.sh dev

# 6. Redeploy with captured IDs
databricks bundle deploy --force
```

## Project Structure

```
├── databricks.yml              # DAB bundle configuration
├── env.example                 # Environment variable template
├── notebooks/
│   ├── 00_common_setup.py      # Create catalog, schema, volume
│   ├── 01_generate_bronze.py   # Faker-based synthetic data generation
│   ├── 02_silver_transforms.py # Reference (DLT handles silver)
│   ├── 03_ml_training.py       # LightGBM revenue forecast + MLflow
│   └── 04_gold_metrics.py      # UC Metric Views (8 views)
├── pipelines/
│   └── dlt_medallion.py        # Bronze → Silver → Gold DLT pipeline
├── app/
│   ├── app.py                  # Streamlit routing
│   ├── config.py               # Centralised env var reader
│   ├── app.yaml                # Databricks App manifest
│   ├── requirements.txt        # Python dependencies
│   ├── components/             # Reusable UI components
│   ├── views/                  # 7 app pages
│   └── data/mock_data.py       # Fallback mock data
├── resources/
│   └── dashboards/
│       └── milacron_fpa.lvdash.json  # AI/BI Dashboard
└── scripts/
    ├── deploy_genie_space.py   # Genie Space creation
    └── update_env_ids.sh       # Post-deploy ID capture
```

## KPIs Tracked

- Revenue growth by BU, region, end-market
- Adjusted EBITDA and EBITDA margin
- Free cash flow and FCF conversion
- Net leverage (Net Debt / EBITDA)
- Working capital: DSO, DPO, inventory turns
- Aftermarket revenue mix and service attach rate
- Order backlog and book-to-bill ratio
- ML-predicted revenue forecast (3-month forward)

## Deployment Targets

| Target  | Catalog              | Schema  |
|---------|----------------------|---------|
| dev     | milacron_demo_dev    | fpa_dev |
| staging | milacron_demo_staging| fpa     |
| prod    | milacron_demo        | fpa     |

## Compute

All workloads run on **serverless compute**: Jobs, DLT, SQL Warehouse, and
Databricks Apps. No classic clusters are provisioned.

## License

MIT
