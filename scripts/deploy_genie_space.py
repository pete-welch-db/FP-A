# Databricks notebook source
# MAGIC %md
# MAGIC # Deploy Genie Space
# MAGIC Creates or updates a Genie Space backed by the gold and silver tables,
# MAGIC with instructions and sample questions aligned to Milacron's KPIs.

# COMMAND ----------

dbutils.widgets.text("catalog", "milacron_demo", "UC Catalog")
dbutils.widgets.text("schema", "fpa", "UC Schema")
dbutils.widgets.text("warehouse_id", "148ccb90800933a1", "SQL Warehouse ID")

catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
warehouse_id = dbutils.widgets.get("warehouse_id")

# COMMAND ----------

# MAGIC %pip install --upgrade databricks-sdk
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import json

catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
warehouse_id = dbutils.widgets.get("warehouse_id")

# COMMAND ----------

GENIE_INSTRUCTIONS = f"""You are a financial analytics assistant for Milacron, a global plastics processing equipment manufacturer.
You have access to consolidated financial data across four business units (Injection Molding, Extrusion, Hot Runners, Aftermarket & Service) and four regions (Americas, Europe, Asia, India).

Key definitions:
- EBITDA = Revenue - COGS - Operating Expenses (before D&A, interest, tax)
- EBITDA Margin = EBITDA / Revenue
- Free Cash Flow = Operating Cash Flow - Capital Expenditures
- FCF Conversion = Free Cash Flow / EBITDA
- Net Leverage = Net Debt / LTM EBITDA
- DSO = (Accounts Receivable / Revenue) * Days in Period
- DPO = (Accounts Payable / COGS) * Days in Period
- Aftermarket Mix = Aftermarket Revenue / Total Revenue
- Service Attach Rate = Customers with Active Service Contracts / Total Active Equipment Customers
- Book-to-Bill = Order Intake / Revenue

When comparing scenarios, "Actual" is reported results, "Budget" is the annual operating plan, "Forecast" is the latest estimate.
Always express currency in USD. When asked about trends, default to trailing 12 months unless specified.
All tables are in catalog '{catalog}' and schema '{schema}'.
"""

ALL_TABLES = [
    f"{catalog}.{schema}.gold_revenue_summary",
    f"{catalog}.{schema}.gold_ebitda_bridge",
    f"{catalog}.{schema}.gold_cash_flow_summary",
    f"{catalog}.{schema}.gold_leverage_metrics",
    f"{catalog}.{schema}.gold_working_capital",
    f"{catalog}.{schema}.gold_aftermarket_mix",
    f"{catalog}.{schema}.gold_order_backlog",
    f"{catalog}.{schema}.gold_plant_performance",
    f"{catalog}.{schema}.ml_revenue_forecast",
    f"{catalog}.{schema}.silver_dim_entity",
    f"{catalog}.{schema}.silver_dim_account",
    f"{catalog}.{schema}.silver_dim_product",
    f"{catalog}.{schema}.silver_dim_time",
]

SAMPLE_QUESTIONS = [
    "What was total revenue by business unit for Q4 2025 vs Q4 2024?",
    "Show me EBITDA margin trend by region for the last 8 quarters.",
    "Which end-markets had the highest revenue growth year-over-year?",
    "What is our current net leverage ratio and how has it trended?",
    "Compare free cash flow conversion between Actual and Budget for FY2025.",
    "What are the top 5 entities by DSO, and how does that compare to last quarter?",
    "What is the aftermarket revenue mix by region, and which regions are below 30%?",
    "Show the service attach rate trend for Injection Molding over the past 12 months.",
    "What does the ML model predict for Americas Injection Molding revenue next quarter vs budget?",
    "Which plants have utilization below 70% this quarter?",
    "What is the book-to-bill ratio by BU for the last 6 months?",
    "Break down the EBITDA variance between price, volume, and cost for Extrusion in Europe.",
]

# COMMAND ----------

# MAGIC %md
# MAGIC ## Check existing Genie Spaces

# COMMAND ----------

from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

existing_space_id = None
try:
    spaces_resp = w.genie.list_spaces()
    for space in (spaces_resp.spaces or []):
        title = space.title or ""
        if "milacron" in title.lower() and "fpa" in title.lower():
            existing_space_id = space.space_id
            print(f"Found existing Genie Space: {existing_space_id} — {title}")
            break
except Exception as e:
    print(f"Could not list Genie Spaces: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Inspect SDK to determine correct create method

# COMMAND ----------

import inspect

sig = inspect.signature(w.genie.create_space)
print(f"create_space signature: {sig}")
print(f"Parameters: {list(sig.parameters.keys())}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create or Update Genie Space

# COMMAND ----------

space_id = None

if existing_space_id:
    print(f"Existing Genie Space found: {existing_space_id}")
    space_id = existing_space_id
else:
    print("Creating new Genie Space via SDK...")

    table_identifiers = [{"table_name": t} for t in ALL_TABLES]

    serialized_config = json.dumps({
        "table_identifiers": table_identifiers,
        "instructions": GENIE_INSTRUCTIONS,
        "sample_questions": [{"question": q} for q in SAMPLE_QUESTIONS],
    })

    try:
        result = w.genie.create_space(
            warehouse_id=warehouse_id,
            serialized_space=serialized_config,
            title="Milacron FP&A Analytics",
            description="Financial analytics assistant for Milacron's global plastics operations",
        )
        space_id = result.space_id
        print(f"Created via SDK: {space_id}")
    except Exception as e:
        print(f"SDK create_space failed: {e}")
        print("Trying REST API with direct body format...")

        import requests
        host = spark.conf.get("spark.databricks.workspaceUrl")
        token = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        api_url = f"https://{host}/api/2.0/genie/spaces"

        payload = {
            "title": "Milacron FP&A Analytics",
            "description": "Financial analytics assistant for Milacron's global plastics operations",
            "warehouse_id": warehouse_id,
            "table_configs": table_identifiers,
            "instructions": GENIE_INSTRUCTIONS,
            "sample_questions": SAMPLE_QUESTIONS,
        }

        resp = requests.post(api_url, headers=headers, json=payload)
        print(f"REST status: {resp.status_code}")
        print(f"REST response: {resp.text[:2000]}")

        if resp.ok:
            result = resp.json()
            space_id = result.get("space_id", result.get("id"))
            print(f"Created via REST: {space_id}")
        else:
            print("Both SDK and REST failed. Printing setup for manual creation.")
            print(f"\nWarehouse ID: {warehouse_id}")
            print(f"Tables to add ({len(ALL_TABLES)}):")
            for t in ALL_TABLES:
                print(f"  - {t}")
            space_id = "MANUAL_SETUP_REQUIRED"

if space_id:
    print(f"\nGENIE_SPACE_ID={space_id}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Output for downstream capture

# COMMAND ----------

dbutils.notebook.exit(space_id or "NONE")
