# Databricks notebook source
# MAGIC %md
# MAGIC # Deploy Genie Space
# MAGIC Creates or updates a Genie Space backed by the gold and silver tables,
# MAGIC with instructions and sample questions aligned to Nova Molding Systems's KPIs.
# MAGIC
# MAGIC Uses the `/api/2.0/data-rooms/` REST API per the ai-dev-kit reference:
# MAGIC https://github.com/databricks-solutions/ai-dev-kit

# COMMAND ----------

dbutils.widgets.text("catalog", "nova_molding_demo", "UC Catalog")
dbutils.widgets.text("schema", "fpa", "UC Schema")
dbutils.widgets.text("warehouse_id", "", "SQL Warehouse ID")
dbutils.widgets.text("genie_space_id", "", "Existing Genie Space ID (optional)")

catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
warehouse_id = dbutils.widgets.get("warehouse_id")
genie_space_id_override = dbutils.widgets.get("genie_space_id").strip()

if not warehouse_id:
    raise ValueError("warehouse_id is required. Pass it via bundle variable --var warehouse_id=<warehouse_id>.")

# COMMAND ----------

import json
import re
import requests

host = spark.conf.get("spark.databricks.workspaceUrl")
token = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
base_url = f"https://{host}"

# COMMAND ----------

GENIE_INSTRUCTIONS = f"""You are a financial analytics assistant for Nova Molding Systems, a global plastics processing equipment manufacturer.
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
Only use columns that exist in the registered tables. Do not assume fields like end_market, scenario_name in cash-flow summaries, or price/volume/cost bridge columns unless they are explicitly present."""

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
    f"{catalog}.{schema}.mv_revenue",
    f"{catalog}.{schema}.mv_ebitda",
    f"{catalog}.{schema}.mv_free_cash_flow",
    f"{catalog}.{schema}.mv_leverage",
    f"{catalog}.{schema}.mv_working_capital",
    f"{catalog}.{schema}.mv_aftermarket",
    f"{catalog}.{schema}.mv_order_backlog",
    f"{catalog}.{schema}.mv_forecast_accuracy",
]

SAMPLE_QUESTIONS = [
    "What was total revenue by business unit for Q4 2025 vs Q4 2024?",
    "Show me EBITDA margin trend by region for the last 8 quarters.",
    "What is the current net leverage ratio and interest coverage trend over the last 8 quarters?",
    "Which entities have the highest DSO in the most recent fiscal quarter?",
    "What is the aftermarket mix percentage by region in the latest quarter, and which regions are below 30%?",
    "Which plants have utilization below 70% in the latest fiscal quarter?",
    "What is the book-to-bill ratio by BU for the last 6 months?",
    "Which product families have the highest predicted revenue in the latest forecast month?",
]

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Check for existing Genie Space

# COMMAND ----------

existing_space_id = None


def normalize_title(value: str) -> str:
    # Normalize punctuation so "FP&A" and "fpa" match consistently.
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def is_target_space(title: str) -> bool:
    normalized = normalize_title(title)
    return "nova_molding" in normalized and "fpa" in normalized


def iter_spaces_via_sdk():
    from databricks.sdk import WorkspaceClient

    w = WorkspaceClient()
    next_page_token = None
    seen_tokens = set()

    while True:
        kwargs = {"page_size": 100}
        if next_page_token:
            kwargs["page_token"] = next_page_token

        spaces_resp = w.genie.list_spaces(**kwargs)
        for space in (spaces_resp.spaces or []):
            yield {"space_id": space.space_id, "title": space.title or ""}

        next_page_token = getattr(spaces_resp, "next_page_token", None)
        if not next_page_token or next_page_token in seen_tokens:
            break
        seen_tokens.add(next_page_token)


def iter_spaces_via_rest():
    next_page_token = None
    seen_tokens = set()

    while True:
        params = {"page_size": 100}
        if next_page_token:
            params["page_token"] = next_page_token

        resp = requests.get(f"{base_url}/api/2.0/data-rooms", headers=headers, params=params)
        if not resp.ok:
            break

        payload = resp.json()
        spaces = payload.get("spaces") or payload.get("data_rooms") or payload.get("dataRooms") or []

        for space in spaces:
            yield {
                "space_id": space.get("space_id", space.get("id")),
                "title": space.get("display_name", space.get("title", space.get("name", ""))),
            }

        next_page_token = (
            payload.get("next_page_token")
            or payload.get("nextPageToken")
            or payload.get("page_token")
        )
        if not next_page_token or next_page_token in seen_tokens:
            break
        seen_tokens.add(next_page_token)

if genie_space_id_override:
    existing_space_id = genie_space_id_override
    print(f"Using provided Genie Space ID override: {existing_space_id}")
else:
    try:
        for space in iter_spaces_via_sdk():
            title = space.get("title", "")
            if is_target_space(title):
                existing_space_id = space.get("space_id")
                print(f"Found existing Genie Space: {existing_space_id} — {title}")
                break
        if not existing_space_id:
            print("No existing Nova Molding Systems FP&A Genie Space found via SDK.")
    except Exception as e:
        print(f"SDK list failed, trying REST: {e}")

    if not existing_space_id:
        try:
            for space in iter_spaces_via_rest():
                title = space.get("title", "")
                if is_target_space(title):
                    existing_space_id = space.get("space_id")
                    print(f"Found existing Genie Space via REST: {existing_space_id} — {title}")
                    break
            if not existing_space_id:
                print("No existing Nova Molding Systems FP&A Genie Space found via REST.")
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
        "display_name": "Nova Molding Systems FP&A Analytics",
        "description": "Financial analytics assistant for Nova Molding Systems's global plastics operations",
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
        "display_name": "Nova Molding Systems FP&A Analytics",
        "warehouse_id": warehouse_id,
        "table_identifiers": ALL_TABLES,
        "description": "Financial analytics assistant for Nova Molding Systems's global plastics operations",
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
    print(f"Checking existing sample questions in space {space_id}...")
    existing_questions = set()
    try:
        existing_resp = requests.get(
            f"{base_url}/api/2.0/data-rooms/{space_id}/curated-questions",
            headers=headers,
        )
        if existing_resp.ok:
            payload = existing_resp.json()
            existing_items = (
                payload.get("curated_questions")
                or payload.get("questions")
                or payload.get("items")
                or []
            )
            for item in existing_items:
                question_text = item.get("question_text", item.get("text", ""))
                if question_text:
                    existing_questions.add(question_text.strip())
    except Exception as e:
        print(f"Could not read existing sample questions: {e}")

    questions_to_add = [q for q in SAMPLE_QUESTIONS if q.strip() not in existing_questions]
    print(f"Adding {len(questions_to_add)} new sample questions to space {space_id}...")

    actions = [
        {
            "action_type": "CREATE",
            "curated_question": {
                "data_room_id": space_id,
                "question_text": q,
                "question_type": "SAMPLE_QUESTION",
            },
        }
        for q in questions_to_add
    ]

    if not actions:
        print("No new sample questions to add.")
    else:
        resp = requests.post(
            f"{base_url}/api/2.0/data-rooms/{space_id}/curated-questions/batch-actions",
            headers=headers,
            json={"actions": actions},
        )
        print(f"Sample questions status: {resp.status_code}")
        if resp.ok:
            print(f"Added {len(questions_to_add)} sample questions.")
        else:
            print(f"Sample questions failed: {resp.text[:1000]}")
else:
    print("Skipping sample questions — no space_id available.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Add general instruction

# COMMAND ----------

if space_id and space_id != "MANUAL_SETUP_REQUIRED":
    instruction_title = "Nova Molding Systems Financial Definitions & Context"
    print("Checking existing instructions in Genie Space...")
    existing_instruction_titles = set()
    try:
        existing_resp = requests.get(
            f"{base_url}/api/2.0/data-rooms/{space_id}/instructions",
            headers=headers,
        )
        if existing_resp.ok:
            payload = existing_resp.json()
            existing_items = payload.get("instructions") or payload.get("items") or []
            for item in existing_items:
                title = item.get("title", "")
                if title:
                    existing_instruction_titles.add(title.strip())
    except Exception as e:
        print(f"Could not read existing instructions: {e}")

    if instruction_title in existing_instruction_titles:
        print(f"Instruction '{instruction_title}' already exists. Skipping create.")
    else:
        print("Adding general instruction to Genie Space...")
        instruction_payload = {
            "title": instruction_title,
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
