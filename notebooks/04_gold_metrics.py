# Databricks notebook source
# MAGIC %md
# MAGIC # Nova Molding Systems FP&A — UC Metric Views
# MAGIC Creates 8 governed metric views in Unity Catalog using the
# MAGIC `CREATE VIEW … WITH METRICS` syntax.  These metric views provide a
# MAGIC single source of truth for KPI definitions consumed by Genie, AI/BI
# MAGIC Dashboards, and the Streamlit App.

# COMMAND ----------

dbutils.widgets.text("catalog", "nova_molding_demo", "UC Catalog")
dbutils.widgets.text("schema", "fpa", "UC Schema")

catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")

spark.sql(f"USE CATALOG {catalog}")
spark.sql(f"USE SCHEMA {schema}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## mv_revenue — Revenue by BU, Region, End-Market

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE VIEW {catalog}.{schema}.mv_revenue
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  source: {catalog}.{schema}.gold_revenue_summary
  dimensions:
    - name: Business Unit
      expr: business_unit
    - name: Region
      expr: region
    - name: Fiscal Year
      expr: fiscal_year
    - name: Fiscal Quarter
      expr: fiscal_quarter
    - name: Fiscal Month
      expr: fiscal_month
    - name: Scenario
      expr: scenario_name
  measures:
    - name: Revenue
      expr: SUM(revenue_usd)
    - name: YoY Growth Pct
      expr: AVG(yoy_growth_pct)
    - name: Budget Variance Pct
      expr: AVG(budget_variance_pct)
$$
""")
print("Created mv_revenue")

# COMMAND ----------

# MAGIC %md
# MAGIC ## mv_ebitda — EBITDA and Margin by BU, Region

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE VIEW {catalog}.{schema}.mv_ebitda
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  source: {catalog}.{schema}.gold_ebitda_bridge
  dimensions:
    - name: Business Unit
      expr: business_unit
    - name: Region
      expr: region
    - name: Fiscal Year
      expr: fiscal_year
    - name: Fiscal Quarter
      expr: fiscal_quarter
    - name: Scenario
      expr: scenario_name
  measures:
    - name: Revenue
      expr: SUM(revenue)
    - name: COGS
      expr: SUM(cogs)
    - name: Gross Profit
      expr: SUM(gross_profit)
    - name: OpEx
      expr: SUM(opex)
    - name: EBITDA
      expr: SUM(ebitda)
    - name: EBITDA Margin
      expr: SUM(ebitda) / NULLIF(SUM(revenue), 0)
$$
""")
print("Created mv_ebitda")

# COMMAND ----------

# MAGIC %md
# MAGIC ## mv_free_cash_flow — FCF and Conversion

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE VIEW {catalog}.{schema}.mv_free_cash_flow
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  source: {catalog}.{schema}.gold_cash_flow_summary
  dimensions:
    - name: Entity
      expr: entity_name
    - name: Region
      expr: region
    - name: Fiscal Year
      expr: fiscal_year
    - name: Fiscal Quarter
      expr: fiscal_quarter
  measures:
    - name: Operating Cash Flow
      expr: SUM(operating_cf)
    - name: CapEx
      expr: SUM(capex)
    - name: Free Cash Flow
      expr: SUM(fcf)
    - name: FCF Conversion Pct
      expr: SUM(fcf) / NULLIF(SUM(operating_cf), 0) * 100
$$
""")
print("Created mv_free_cash_flow")

# COMMAND ----------

# MAGIC %md
# MAGIC ## mv_leverage — Net Leverage and Interest Coverage

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE VIEW {catalog}.{schema}.mv_leverage
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  source: {catalog}.{schema}.gold_leverage_metrics
  dimensions:
    - name: Entity
      expr: entity_id
    - name: Fiscal Year
      expr: fiscal_year
    - name: Fiscal Quarter
      expr: fiscal_quarter
  measures:
    - name: Net Debt
      expr: SUM(net_debt)
    - name: Net Leverage Ratio
      expr: SUM(net_debt) / NULLIF(SUM(ltm_ebitda), 0)
    - name: Interest Coverage Ratio
      expr: SUM(ltm_ebitda) / NULLIF(SUM(total_interest), 0)
$$
""")
print("Created mv_leverage")

# COMMAND ----------

# MAGIC %md
# MAGIC ## mv_working_capital — DSO, DPO, Inventory Turns

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE VIEW {catalog}.{schema}.mv_working_capital
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  source: {catalog}.{schema}.gold_working_capital
  dimensions:
    - name: Entity
      expr: entity_name
    - name: Business Unit
      expr: business_unit
    - name: Region
      expr: region
    - name: Fiscal Year
      expr: fiscal_year
    - name: Fiscal Quarter
      expr: fiscal_quarter
  measures:
    - name: DSO
      expr: AVG(dso)
    - name: DPO
      expr: AVG(dpo)
    - name: Inventory Turns
      expr: AVG(inventory_turns)
    - name: Cash Conversion Cycle
      expr: AVG(cash_conversion_cycle)
$$
""")
print("Created mv_working_capital")

# COMMAND ----------

# MAGIC %md
# MAGIC ## mv_aftermarket — Aftermarket Revenue Mix and Service Attach

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE VIEW {catalog}.{schema}.mv_aftermarket
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  source: {catalog}.{schema}.gold_aftermarket_mix
  dimensions:
    - name: Business Unit
      expr: business_unit
    - name: Region
      expr: region
    - name: Fiscal Year
      expr: fiscal_year
    - name: Fiscal Quarter
      expr: fiscal_quarter
  measures:
    - name: Aftermarket Revenue
      expr: SUM(aftermarket_revenue)
    - name: Total Revenue
      expr: SUM(total_revenue)
    - name: Aftermarket Mix Pct
      expr: SUM(aftermarket_revenue) / NULLIF(SUM(total_revenue), 0) * 100
    - name: Service Attach Rate
      expr: AVG(service_attach_rate)
$$
""")
print("Created mv_aftermarket")

# COMMAND ----------

# MAGIC %md
# MAGIC ## mv_order_backlog — Order Intake, Backlog, Book-to-Bill

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE VIEW {catalog}.{schema}.mv_order_backlog
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  source: {catalog}.{schema}.gold_order_backlog
  dimensions:
    - name: Business Unit
      expr: business_unit
    - name: Region
      expr: region
    - name: Fiscal Year
      expr: fiscal_year
    - name: Fiscal Month
      expr: fiscal_month
  measures:
    - name: Order Intake
      expr: SUM(order_intake)
    - name: Backlog Value
      expr: SUM(backlog_value)
    - name: Book-to-Bill Ratio
      expr: SUM(order_intake) / NULLIF(SUM(shipped_revenue), 0)
$$
""")
print("Created mv_order_backlog")

# COMMAND ----------

# MAGIC %md
# MAGIC ## mv_forecast_accuracy — ML Predicted vs Actual

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE VIEW {catalog}.{schema}.mv_forecast_accuracy
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  source: >
    SELECT
      f.entity_id,
      e.business_unit,
      e.region,
      f.forecast_month,
      f.predicted_revenue,
      r.revenue_usd AS actual_revenue
    FROM {catalog}.{schema}.ml_revenue_forecast f
    JOIN {catalog}.{schema}.silver_dim_entity e ON f.entity_id = e.entity_id
    LEFT JOIN {catalog}.{schema}.gold_revenue_summary r
      ON e.business_unit = r.business_unit
      AND e.region = r.region
      AND f.forecast_month = CONCAT(r.fiscal_year, '-', LPAD(r.fiscal_month, 2, '0'))
      AND r.scenario_name = 'Actual'
  dimensions:
    - name: Business Unit
      expr: business_unit
    - name: Region
      expr: region
    - name: Forecast Month
      expr: forecast_month
  measures:
    - name: Predicted Revenue
      expr: SUM(predicted_revenue)
    - name: Actual Revenue
      expr: SUM(actual_revenue)
    - name: MAPE
      expr: AVG(ABS(predicted_revenue - actual_revenue) / NULLIF(actual_revenue, 0)) * 100
$$
""")
print("Created mv_forecast_accuracy")

# COMMAND ----------

print("=" * 60)
print(f"All 8 metric views created in {catalog}.{schema}")
print("=" * 60)
