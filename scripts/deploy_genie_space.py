# Databricks notebook source
# MAGIC %md
# MAGIC # Deploy Genie Space
# MAGIC Creates or updates a Genie Space backed by the gold and silver tables,
# MAGIC with instructions and sample questions aligned to Milacron's KPIs.
# MAGIC
# MAGIC Uses the `/api/2.0/data-rooms/` REST API per the ai-dev-kit reference:
# MAGIC https://github.com/databricks-solutions/ai-dev-kit

# COMMAND ----------

dbutils.widgets.text("catalog", "milacron_demo", "UC Catalog")
dbutils.widgets.text("schema", "fpa", "UC Schema")
dbutils.widgets.text("warehouse_id", "148ccb90800933a1", "SQL Warehouse ID")

catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
warehouse_id = dbutils.widgets.get("warehouse_id")

# COMMAND ----------

import json
import requests

host = spark.conf.get("spark.databricks.workspaceUrl")
token = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
base_url = f"https://{host}"

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
All tables are in catalog '{catalog}' and schema '{schema}'."""

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
# MAGIC ## Step 1: Check for existing Genie Space

# COMMAND ----------

existing_space_id = None

try:
    from databricks.sdk import WorkspaceClient
    w = WorkspaceClient()
    spaces_resp = w.genie.list_spaces()
    for space in (spaces_resp.spaces or []):
        title = space.title or ""
        if "milacron" in title.lower() and "fpa" in title.lower():
            existing_space_id = space.space_id
            print(f"Found existing Genie Space: {existing_space_id} — {title}")
            break
    if not existing_space_id:
        print("No existing Milacron FP&A Genie Space found.")
except Exception as e:
    print(f"SDK list failed, trying REST: {e}")
    try:
        resp = requests.get(f"{base_url}/api/2.0/data-rooms", headers=headers)
        if resp.ok:
            for space in resp.json().get("spaces", resp.json().get("data_rooms", [])):
                title = space.get("display_name", space.get("title", ""))
                if "milacron" in title.lower() and "fpa" in title.lower():
                    existing_space_id = space.get("space_id", space.get("id"))
                    print(f"Found existing Genie Space via REST: {existing_space_id} — {title}")
                    break
    except Exception as e2:
        print(f"REST list also failed: {e2}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Create or Update Genie Space via /api/2.0/data-rooms/

# COMMAND ----------

space_id = None

if existing_space_id:
    print(f"Updating existing Genie Space: {existing_space_id}")
    update_payload = {
        "id": existing_space_id,
        "display_name": "Milacron FP&A Analytics",
        "description": "Financial analytics assistant for Milacron's global plastics operations",
        "warehouse_id": warehouse_id,
        "table_identifiers": ALL_TABLES,
        "run_as_type": "VIEWER",
    }
    resp = requests.patch(
        f"{base_url}/api/2.0/data-rooms/{existing_space_id}",
        headers=headers,
        json=update_payload,
    )
    print(f"Update status: {resp.status_code}")
    if resp.ok:
        space_id = existing_space_id
        print(f"Updated Genie Space: {space_id}")
    else:
        print(f"Update failed: {resp.text[:2000]}")
        space_id = existing_space_id
else:
    print("Creating new Genie Space via /api/2.0/data-rooms/ ...")
    create_payload = {
        "display_name": "Milacron FP&A Analytics",
        "warehouse_id": warehouse_id,
        "table_identifiers": ALL_TABLES,
        "description": "Financial analytics assistant for Milacron's global plastics operations",
        "run_as_type": "VIEWER",
    }
    resp = requests.post(
        f"{base_url}/api/2.0/data-rooms/",
        headers=headers,
        json=create_payload,
    )
    print(f"Create status: {resp.status_code}")
    print(f"Create response: {resp.text[:2000]}")

    if resp.ok:
        result = resp.json()
        space_id = result.get("space_id", result.get("id"))
        print(f"Created Genie Space: {space_id}")
    else:
        print("REST create failed. Check response above for details.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Add sample questions via batch API

# COMMAND ----------

if space_id and space_id != "MANUAL_SETUP_REQUIRED":
    print(f"Adding {len(SAMPLE_QUESTIONS)} sample questions to space {space_id}...")

    actions = [
        {
            "action_type": "CREATE",
            "curated_question": {
                "data_room_id": space_id,
                "question_text": q,
                "question_type": "SAMPLE_QUESTION",
            },
        }
        for q in SAMPLE_QUESTIONS
    ]

    resp = requests.post(
        f"{base_url}/api/2.0/data-rooms/{space_id}/curated-questions/batch-actions",
        headers=headers,
        json={"actions": actions},
    )
    print(f"Sample questions status: {resp.status_code}")
    if resp.ok:
        print(f"Added {len(SAMPLE_QUESTIONS)} sample questions.")
    else:
        print(f"Sample questions failed: {resp.text[:1000]}")
else:
    print("Skipping sample questions — no space_id available.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Add general instruction

# COMMAND ----------

if space_id and space_id != "MANUAL_SETUP_REQUIRED":
    print("Adding general instruction to Genie Space...")
    instruction_payload = {
        "title": "Milacron Financial Definitions & Context",
        "content": GENIE_INSTRUCTIONS,
        "instruction_type": "TEXT_INSTRUCTION",
    }
    resp = requests.post(
        f"{base_url}/api/2.0/data-rooms/{space_id}/instructions",
        headers=headers,
        json=instruction_payload,
    )
    print(f"Instruction status: {resp.status_code}")
    if resp.ok:
        print("Added general instruction.")
    else:
        print(f"Instruction failed: {resp.text[:1000]}")
else:
    print("Skipping instructions — no space_id available.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Output

# COMMAND ----------

if space_id:
    print(f"\nGENIE_SPACE_ID={space_id}")
    print(f"URL: https://{host}/genie/rooms/{space_id}")

dbutils.notebook.exit(space_id or "NONE")
