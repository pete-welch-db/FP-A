# Nova Molding Systems FP&A Demo (Databricks + DAB)

This repository contains a customer-ready FP&A demo built on Databricks:

- DLT medallion pipeline (bronze/silver/gold)
- Databricks SQL + AI/BI dashboard artifacts
- Genie space bootstrap script
- Streamlit lightweight app deployed with Databricks Apps

## Security and Configuration Model

Tracked files in this repo intentionally do **not** contain workspace endpoints, IDs, or tokens.

- Put all environment-specific values in local `.env` (gitignored).
- Keep `.env` out of version control.
- If you modify tracked manifests locally for deployment, do not commit those changes.

## Prerequisites

- Databricks CLI installed and authenticated (`databricks auth login`)
- Access to a Databricks workspace with permissions for:
  - Unity Catalog object creation/grants
  - Lakeflow Declarative Pipelines (DLT)
  - Jobs, Dashboards, and Apps
  - Genie
- A Serverless SQL Warehouse ID

## 1) Clone and Configure

```bash
git clone <your-fork-or-repo-url>
cd FP-A
cp env.example .env
```

Open `.env` and set at least:

- `DATABRICKS_HOST`
- `DATABRICKS_TOKEN` (or use profile auth for CLI operations)
- `DATABRICKS_HTTP_PATH`
- `DATABRICKS_CATALOG`
- `DATABRICKS_SCHEMA`
- `WAREHOUSE_ID`

## 2) Validate and Deploy with DAB

```bash
# Validate bundle config
databricks bundle validate --target dev

# Deploy bundle resources
databricks bundle deploy --target dev --force --var warehouse_id=<your_warehouse_id>
```

## 3) Run Pipeline + Provision Analytics Assets

```bash
databricks bundle run data_pipeline --target dev
```

This job performs setup/data generation, DLT, ML training, metrics creation, app permission grants, and Genie deployment.

## 4) Capture Runtime IDs into Local .env

```bash
./scripts/update_env_ids.sh dev
```

This writes `GENIE_SPACE_ID`, `DASHBOARD_EMBED_URL`, and `DASHBOARD_EMBED_URL_V2` to local `.env`.

## 5) Redeploy App (if runtime env changed)

```bash
databricks bundle deploy --target dev --force --var warehouse_id=<your_warehouse_id>
```

## 6) Verify

- Open the Databricks App from `databricks apps get <app-name>`
- Check:
  - Dashboard page loads with your embed URL
  - Genie page connects and answers sample questions

## Local Run (Optional)

```bash
cd app
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run app_lightweight.py --server.port 8501
```

The app reads local `.env` via `app/config.py`.

## Common Issues

- **`warehouse_id` missing**: pass `--var warehouse_id=<id>` on deploy.
- **Genie permission errors**: rerun `databricks bundle run data_pipeline --target dev` to re-apply app UC grants.
- **No dashboard embedded**: run `./scripts/update_env_ids.sh dev` and confirm `DASHBOARD_EMBED_URL*` in `.env`.

## Repository Layout

```text
databricks.yml                 # Databricks Asset Bundle config
env.example                    # Local configuration template
app/                           # Streamlit app and Databricks App manifest
notebooks/                     # Setup, bronze, ML, gold metrics
pipelines/                     # DLT pipeline code
resources/dashboards/          # Lakeview dashboard artifacts
scripts/                       # Genie deploy, app grant, env capture helpers
```

## License

MIT
