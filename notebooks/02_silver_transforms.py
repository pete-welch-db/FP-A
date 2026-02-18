# Databricks notebook source
# MAGIC %md
# MAGIC # Milacron FP&A — Silver Transforms (Reference)
# MAGIC
# MAGIC **This notebook is for reference only.**
# MAGIC
# MAGIC Silver transforms are handled by the DLT pipeline (`pipelines/dlt_medallion.py`).
# MAGIC This notebook documents the transformation logic for manual inspection or
# MAGIC ad-hoc execution outside of DLT.

# COMMAND ----------

dbutils.widgets.text("catalog", "milacron_demo", "UC Catalog")
dbutils.widgets.text("schema", "fpa", "UC Schema")

catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")

spark.sql(f"USE CATALOG {catalog}")
spark.sql(f"USE SCHEMA {schema}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Silver Layer Logic Summary
# MAGIC
# MAGIC The DLT pipeline applies the following transformations for every table:
# MAGIC
# MAGIC 1. **Deduplication** — `ROW_NUMBER() OVER (PARTITION BY {natural_key} ORDER BY _ingested_at DESC)`
# MAGIC    keeping only the latest ingested record per natural key.
# MAGIC 2. **Type casting** — Dates → `DATE`, amounts → `DECIMAL(18,2)`, rates → `DECIMAL(12,6)`,
# MAGIC    booleans → `BOOLEAN`, integers → `INT`.
# MAGIC 3. **Expectations** — Null checks on primary keys, FK existence checks,
# MAGIC    range validations on numeric fields.
# MAGIC 4. **Metadata removal** — `_ingested_at` and `_source_file` columns dropped
# MAGIC    after dedup window.

# COMMAND ----------

# MAGIC %md
# MAGIC ### Quick Validation Queries

# COMMAND ----------

tables = [
    "silver_dim_entity", "silver_dim_account", "silver_dim_scenario",
    "silver_dim_time", "silver_dim_product", "silver_dim_customer",
    "silver_dim_currency", "silver_dim_cost_center",
    "silver_fact_gl_journal", "silver_fact_orders", "silver_fact_production",
    "silver_fact_service", "silver_fact_working_capital",
    "silver_fact_debt_schedule", "silver_fact_fx_rates", "silver_fact_capex",
]

for t in tables:
    try:
        count = spark.sql(f"SELECT COUNT(*) AS cnt FROM {catalog}.{schema}.{t}").collect()[0]["cnt"]
        print(f"  {t:40s} → {count:>10,} rows")
    except Exception as e:
        print(f"  {t:40s} → NOT FOUND ({e})")
