# Databricks notebook source
# MAGIC %md
# MAGIC # Milacron FP&A Demo — Generate Synthetic Bronze Data
# MAGIC Produces OneStream-aligned CSV files and lands them in the UC Volume
# MAGIC `/Volumes/{catalog}/{schema}/raw_landing/` so the DLT pipeline can
# MAGIC ingest them through Auto Loader.
# MAGIC
# MAGIC **Reproducibility**: All random generators are seeded.

# COMMAND ----------

dbutils.widgets.text("catalog", "milacron_demo", "UC Catalog")
dbutils.widgets.text("schema", "fpa", "UC Schema")

catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")

spark.sql(f"USE CATALOG {catalog}")
spark.sql(f"USE SCHEMA {schema}")

VOLUME_PATH = f"/Volumes/{catalog}/{schema}/raw_landing"

# COMMAND ----------

# MAGIC %pip install faker numpy pandas
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import os, csv, io, random, itertools, uuid
from datetime import date, timedelta
from decimal import Decimal

import numpy as np
import pandas as pd
from faker import Faker

SEED = 42
random.seed(SEED)
np.random.seed(SEED)
fake = Faker()
Faker.seed(SEED)

catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
VOLUME_PATH = f"/Volumes/{catalog}/{schema}/raw_landing"

# COMMAND ----------

# MAGIC %md
# MAGIC ## Helper Utilities

# COMMAND ----------

def write_csv(df: pd.DataFrame, filename: str):
    """Write a pandas DataFrame to the UC Volume as a single CSV file."""
    path = f"{VOLUME_PATH}/{filename}"
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    dbutils.fs.put(path, csv_bytes.decode("utf-8"), overwrite=True)
    print(f"  ✓ {path} ({len(df):,} rows)")


def seasonal_factor(month: int) -> float:
    """Milacron-style seasonality: Q1 ramp, Q2/Q3 peak, Q4 budget flush."""
    factors = {
        1: 0.85, 2: 0.90, 3: 0.95, 4: 1.05, 5: 1.10, 6: 1.12,
        7: 1.08, 8: 1.05, 9: 1.02, 10: 0.98, 11: 0.92, 12: 0.88,
    }
    return factors[month]


def region_multiplier(region: str) -> float:
    """Revenue weight by region — Americas dominates."""
    weights = {"Americas": 1.0, "Europe": 0.70, "Asia": 0.45, "India": 0.25}
    return weights.get(region, 0.5)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1 — Dimension Tables

# COMMAND ----------

# ── dim_entity ──────────────────────────────────────────────────────────
BUS = ["Injection Molding", "Extrusion", "Hot Runners", "Aftermarket & Service"]
REGIONS = ["Americas", "Europe", "Asia", "India"]
COUNTRIES = {
    "Americas": ["United States", "Canada", "Mexico", "Brazil"],
    "Europe": ["Germany", "Italy", "United Kingdom", "France"],
    "Asia": ["China", "Japan", "South Korea", "Vietnam"],
    "India": ["India"],
}
CURRENCIES = {
    "United States": "USD", "Canada": "CAD", "Mexico": "MXN", "Brazil": "BRL",
    "Germany": "EUR", "Italy": "EUR", "United Kingdom": "GBP", "France": "EUR",
    "China": "CNY", "Japan": "JPY", "South Korea": "KRW", "Vietnam": "VND",
    "India": "INR",
}

entities = []
eid = 1
parent_map = {}
for bu in BUS:
    parent_id = eid
    entities.append({
        "entity_id": f"E{eid:04d}", "entity_name": f"Milacron {bu} Global",
        "parent_entity_id": "", "region": "Americas",
        "country": "United States", "business_unit": bu,
        "is_consolidated": True, "currency_code": "USD",
    })
    parent_map[bu] = f"E{eid:04d}"
    eid += 1
    for region in REGIONS:
        for country in COUNTRIES[region]:
            entities.append({
                "entity_id": f"E{eid:04d}",
                "entity_name": f"Milacron {bu} {country}",
                "parent_entity_id": parent_map[bu],
                "region": region, "country": country,
                "business_unit": bu, "is_consolidated": False,
                "currency_code": CURRENCIES[country],
            })
            eid += 1

df_entity = pd.DataFrame(entities)
write_csv(df_entity, "entity_master.csv")

# COMMAND ----------

# ── dim_account ─────────────────────────────────────────────────────────
ACCOUNT_TREE = [
    ("Revenue",  "REV", [("Product Revenue", "REV_PROD"), ("Service Revenue", "REV_SVC"), ("Parts Revenue", "REV_PARTS")]),
    ("COGS",     "COGS", [("Material Cost", "COGS_MAT"), ("Labor Cost", "COGS_LAB"), ("Overhead", "COGS_OH"), ("Warranty", "COGS_WAR")]),
    ("OpEx",     "OPEX", [("SG&A", "OPEX_SGA"), ("R&D", "OPEX_RD"), ("Depreciation", "OPEX_DA")]),
    ("BS",       "BS",   [("Cash", "BS_CASH"), ("Accounts Receivable", "BS_AR"), ("Inventory", "BS_INV"),
                           ("PP&E", "BS_PPE"), ("Accounts Payable", "BS_AP"), ("Debt", "BS_DEBT")]),
    ("CF",       "CF",   [("Operating CF", "CF_OPS"), ("Investing CF", "CF_INV"), ("Financing CF", "CF_FIN")]),
]

accounts = []
aid = 1
for acct_type, parent_code, children in ACCOUNT_TREE:
    parent_aid = f"A{aid:04d}"
    accounts.append({
        "account_id": parent_aid, "account_name": acct_type,
        "account_type": acct_type, "account_group": acct_type,
        "parent_account_id": "", "sign_convention": "credit" if acct_type == "Revenue" else "debit",
        "is_calculated": True,
    })
    aid += 1
    for name, code in children:
        accounts.append({
            "account_id": f"A{aid:04d}", "account_name": name,
            "account_type": acct_type, "account_group": code,
            "parent_account_id": parent_aid, "sign_convention": "credit" if acct_type == "Revenue" else "debit",
            "is_calculated": False,
        })
        aid += 1

df_account = pd.DataFrame(accounts)
write_csv(df_account, "account_master.csv")

# COMMAND ----------

# ── dim_scenario ────────────────────────────────────────────────────────
scenarios = []
for yr in [2024, 2025]:
    for sid, (name, locked) in enumerate([
        ("Actual", yr < 2025), ("Budget", True), ("Forecast", False),
        ("Upside", False), ("Downside", False),
    ], start=1):
        scenarios.append({
            "scenario_id": f"S{yr}{sid}", "scenario_name": name,
            "scenario_year": yr, "is_locked": locked,
        })

df_scenario = pd.DataFrame(scenarios)
write_csv(df_scenario, "scenario_master.csv")

# COMMAND ----------

# ── dim_time ────────────────────────────────────────────────────────────
dates = pd.date_range("2024-01-01", "2025-12-31", freq="D")
time_rows = []
for d in dates:
    time_rows.append({
        "time_id": d.strftime("%Y%m%d"),
        "calendar_date": d.strftime("%Y-%m-%d"),
        "fiscal_year": d.year,
        "fiscal_quarter": f"Q{(d.month - 1) // 3 + 1}",
        "fiscal_month": d.month,
        "fiscal_week": d.isocalendar()[1],
        "is_month_end": d == d + pd.offsets.MonthEnd(0),
        "is_quarter_end": d.month in (3, 6, 9, 12) and d == d + pd.offsets.MonthEnd(0),
    })

df_time = pd.DataFrame(time_rows)
write_csv(df_time, "time_master.csv")

# COMMAND ----------

# ── dim_product ─────────────────────────────────────────────────────────
PRODUCT_FAMILIES = {
    "OEM Equipment": ["Servo-Hydraulic IMM", "All-Electric IMM", "Two-Platen IMM",
                      "Single-Screw Extruder", "Twin-Screw Extruder", "Co-Extrusion Line"],
    "Aftermarket Parts": ["Screw & Barrel Sets", "Heater Bands", "Nozzle Tips",
                          "Hydraulic Seals", "Controller Boards"],
    "Service Contracts": ["Preventive Maintenance", "Full Machine Service", "Remote Diagnostics"],
    "Automation & IIoT": ["M-Powered Analytics", "Robot Integration Kit", "Smart Mold Monitoring"],
}
END_MARKETS = ["Automotive", "Packaging", "Medical", "Consumer Goods", "Electronics", "Construction"]

products = []
pid = 1
for pline, families in PRODUCT_FAMILIES.items():
    for fam in families:
        for em in END_MARKETS:
            products.append({
                "product_id": f"P{pid:04d}",
                "product_family": fam,
                "product_line": pline,
                "end_market": em,
                "is_aftermarket": pline != "OEM Equipment",
            })
            pid += 1

df_product = pd.DataFrame(products)
write_csv(df_product, "product_master.csv")

# COMMAND ----------

# ── dim_customer ────────────────────────────────────────────────────────
customers = []
for cid in range(1, 201):
    region = random.choice(REGIONS)
    country = random.choice(COUNTRIES[region])
    customers.append({
        "customer_id": f"C{cid:04d}",
        "customer_name": fake.company(),
        "customer_segment": random.choice(["Enterprise", "Mid-Market", "SMB"]),
        "region": region, "country": country,
        "industry_vertical": random.choice(END_MARKETS),
    })

df_customer = pd.DataFrame(customers)
write_csv(df_customer, "customer_master.csv")

# COMMAND ----------

# ── dim_currency ────────────────────────────────────────────────────────
currencies = [
    {"currency_code": c, "currency_name": n} for c, n in [
        ("USD", "US Dollar"), ("EUR", "Euro"), ("GBP", "British Pound"),
        ("CAD", "Canadian Dollar"), ("MXN", "Mexican Peso"), ("BRL", "Brazilian Real"),
        ("CNY", "Chinese Yuan"), ("JPY", "Japanese Yen"), ("KRW", "South Korean Won"),
        ("VND", "Vietnamese Dong"), ("INR", "Indian Rupee"),
    ]
]
df_currency = pd.DataFrame(currencies)
write_csv(df_currency, "currency_master.csv")

# COMMAND ----------

# ── dim_cost_center ─────────────────────────────────────────────────────
PLANTS = [
    ("P01", "Batavia Plant",          "United States", "Americas"),
    ("P02", "Mount Orab Plant",       "United States", "Americas"),
    ("P03", "Monterrey Plant",        "Mexico",        "Americas"),
    ("P04", "Malterdingen Plant",     "Germany",       "Europe"),
    ("P05", "Brescia Plant",          "Italy",         "Europe"),
    ("P06", "Ahmedabad Plant",        "India",         "India"),
    ("P07", "Shanghai Plant",         "China",         "Asia"),
    ("P08", "Chiba Plant",            "Japan",         "Asia"),
]

cost_centers = []
ccid = 1
for plant_id, plant_name, country, region in PLANTS:
    for dept in ["Production", "Quality", "Maintenance", "Logistics"]:
        cost_centers.append({
            "cost_center_id": f"CC{ccid:04d}",
            "cost_center_name": f"{plant_name} {dept}",
            "plant_id": plant_id, "plant_name": plant_name,
            "plant_country": country,
        })
        ccid += 1

df_cost_center = pd.DataFrame(cost_centers)
write_csv(df_cost_center, "cost_center_master.csv")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2 — Fact Tables

# COMMAND ----------

# Precompute lookup lists for efficiency
entity_ids = df_entity[~df_entity["is_consolidated"]]["entity_id"].tolist()
entity_bu = dict(zip(df_entity["entity_id"], df_entity["business_unit"]))
entity_region = dict(zip(df_entity["entity_id"], df_entity["region"]))
account_leaf_ids = df_account[~df_account["is_calculated"]]["account_id"].tolist()
account_type_map = dict(zip(df_account["account_id"], df_account["account_type"]))
product_ids = df_product["product_id"].tolist()
customer_ids = df_customer["customer_id"].tolist()
scenario_ids = df_scenario["scenario_id"].tolist()
months = pd.date_range("2024-01-01", "2025-12-31", freq="MS")

# COMMAND ----------

# ── fact_gl_journal ─────────────────────────────────────────────────────
# One row per entity × leaf account × month × scenario
print("Generating GL journal entries...")
gl_rows = []
jid = 1
for m in months:
    time_id = m.strftime("%Y%m%d")
    sf = seasonal_factor(m.month)
    yr_trend = 1.0 if m.year == 2024 else 1.06  # 6% YoY growth in actuals
    for eid in entity_ids:
        rm = region_multiplier(entity_region[eid])
        for aid in account_leaf_ids:
            at = account_type_map[aid]
            for sid in [s for s in scenario_ids if str(m.year) in s]:
                base = 250_000 if at == "Revenue" else 180_000 if at == "COGS" else 50_000
                scenario_factor = {"Actual": 1.0, "Budget": 0.98, "Forecast": 1.02,
                                   "Upside": 1.08, "Downside": 0.92}.get(
                    df_scenario[df_scenario["scenario_id"] == sid]["scenario_name"].iloc[0], 1.0
                )
                amount = base * sf * rm * yr_trend * scenario_factor * np.random.uniform(0.90, 1.10)
                gl_rows.append({
                    "journal_id": f"J{jid:08d}",
                    "entity_id": eid, "account_id": aid,
                    "scenario_id": sid, "time_id": time_id,
                    "flow_type": "Operating",
                    "intercompany_entity_id": "",
                    "amount_local": round(amount, 2),
                    "amount_usd": round(amount, 2),  # FX normalised in silver
                    "currency_code": "USD",
                })
                jid += 1

df_gl = pd.DataFrame(gl_rows)
write_csv(df_gl, "gl_journal_2024_2025.csv")

# COMMAND ----------

# ── fact_orders ─────────────────────────────────────────────────────────
print("Generating order data...")
order_rows = []
oid = 1
for m in months:
    time_id = m.strftime("%Y%m%d")
    sf = seasonal_factor(m.month)
    for _ in range(int(600 * sf)):
        eid = random.choice(entity_ids)
        rm = region_multiplier(entity_region[eid])
        qty = max(1, int(np.random.poisson(5) * rm))
        price = round(np.random.uniform(5_000, 500_000) * rm, 2)
        disc = round(np.random.beta(2, 10) * 0.25, 4)
        status = np.random.choice(["Open", "Shipped", "Cancelled"], p=[0.20, 0.72, 0.08])
        order_rows.append({
            "order_id": f"O{oid:08d}", "entity_id": eid,
            "customer_id": random.choice(customer_ids),
            "product_id": random.choice(product_ids),
            "time_id": time_id, "order_qty": qty,
            "unit_price": price,
            "discount_pct": disc,
            "net_amount_usd": round(qty * price * (1 - disc), 2),
            "order_status": status,
            "backlog_flag": status == "Open",
        })
        oid += 1

df_orders = pd.DataFrame(order_rows)
write_csv(df_orders, "orders_2024_2025.csv")

# COMMAND ----------

# ── fact_production ─────────────────────────────────────────────────────
print("Generating production data...")
prod_rows = []
prid = 1
prod_cc_ids = df_cost_center[df_cost_center["cost_center_name"].str.contains("Production")]["cost_center_id"].tolist()
sample_products = random.sample(product_ids, min(50, len(product_ids)))

for m in months:
    time_id = m.strftime("%Y%m%d")
    sf = seasonal_factor(m.month)
    for ccid in prod_cc_ids:
        for pid in sample_products:
            units = max(0, int(np.random.poisson(120) * sf))
            std_cost = round(np.random.uniform(800, 15000), 2)
            actual_cost = round(std_cost * np.random.uniform(0.92, 1.12), 2)
            util = round(min(1.0, max(0.3, np.random.normal(0.78, 0.10) * sf)), 4)
            prod_rows.append({
                "production_id": f"PR{prid:08d}",
                "cost_center_id": ccid, "product_id": pid,
                "time_id": time_id, "units_produced": units,
                "standard_cost": std_cost, "actual_cost": actual_cost,
                "utilization_pct": util,
                "energy_cost": round(units * np.random.uniform(5, 25), 2),
                "material_cost": round(units * np.random.uniform(200, 5000), 2),
                "scrap_rate": round(np.random.beta(2, 30), 4),
            })
            prid += 1

df_production = pd.DataFrame(prod_rows)
write_csv(df_production, "production_2024_2025.csv")

# COMMAND ----------

# ── fact_service ────────────────────────────────────────────────────────
print("Generating service/aftermarket data...")
svc_rows = []
svid = 1
contract_types = ["Full Service", "Parts Only", "IIoT Monitoring"]

for m in months:
    time_id = m.strftime("%Y%m%d")
    for _ in range(int(150 * seasonal_factor(m.month))):
        eid = random.choice(entity_ids)
        ct = random.choice(contract_types)
        cv = round(np.random.uniform(5_000, 120_000), 2)
        svc_rows.append({
            "service_id": f"SV{svid:08d}",
            "entity_id": eid,
            "customer_id": random.choice(customer_ids),
            "product_id": random.choice(product_ids),
            "time_id": time_id,
            "contract_type": ct,
            "contract_value_usd": cv,
            "parts_revenue_usd": round(cv * np.random.uniform(0.3, 0.6), 2),
            "labor_revenue_usd": round(cv * np.random.uniform(0.1, 0.35), 2),
            "is_renewal": random.random() < 0.45,
            "churn_flag": random.random() < 0.08,
            "service_attach_flag": random.random() < 0.62,
        })
        svid += 1

df_service = pd.DataFrame(svc_rows)
write_csv(df_service, "service_2024_2025.csv")

# COMMAND ----------

# ── fact_working_capital ────────────────────────────────────────────────
print("Generating working capital snapshots...")
wc_rows = []
wcid = 1
for m in months:
    time_id = m.strftime("%Y%m%d")
    for eid in entity_ids:
        rm = region_multiplier(entity_region[eid])
        ar = round(np.random.uniform(2e6, 15e6) * rm, 2)
        ap = round(np.random.uniform(1.5e6, 10e6) * rm, 2)
        inv_raw = round(np.random.uniform(1e6, 6e6) * rm, 2)
        inv_wip = round(np.random.uniform(0.5e6, 3e6) * rm, 2)
        inv_fin = round(np.random.uniform(0.8e6, 5e6) * rm, 2)
        revenue_proxy = 20e6 * rm * seasonal_factor(m.month)
        cogs_proxy = revenue_proxy * 0.65
        days = 30
        wc_rows.append({
            "wc_id": f"WC{wcid:08d}", "entity_id": eid,
            "time_id": time_id,
            "ar_balance": ar,
            "ar_aging_current": round(ar * 0.55, 2),
            "ar_aging_30": round(ar * 0.25, 2),
            "ar_aging_60": round(ar * 0.12, 2),
            "ar_aging_90plus": round(ar * 0.08, 2),
            "ap_balance": ap,
            "inventory_raw": inv_raw,
            "inventory_wip": inv_wip,
            "inventory_finished": inv_fin,
            "dso": round(ar / revenue_proxy * days, 1) if revenue_proxy else 0,
            "dpo": round(ap / cogs_proxy * days, 1) if cogs_proxy else 0,
            "inventory_turns": round(cogs_proxy / (inv_raw + inv_wip + inv_fin) * 12, 2) if (inv_raw + inv_wip + inv_fin) else 0,
        })
        wcid += 1

df_wc = pd.DataFrame(wc_rows)
write_csv(df_wc, "working_capital_2024_2025.csv")

# COMMAND ----------

# ── fact_debt_schedule ──────────────────────────────────────────────────
print("Generating debt schedule...")
debt_rows = []
did = 1
instruments = [
    ("Term Loan A", 350_000_000, 0.055, "2028-06-30"),
    ("Term Loan B", 500_000_000, 0.065, "2030-12-31"),
    ("Revolver", 150_000_000, 0.048, "2027-06-30"),
    ("Senior Notes 2029", 400_000_000, 0.058, "2029-09-15"),
]
for m in months:
    time_id = m.strftime("%Y%m%d")
    for name, principal, rate, maturity in instruments:
        paydown = principal * 0.005 * ((m - months[0]).days / 365)
        balance = max(0, principal - paydown)
        debt_rows.append({
            "debt_id": f"D{did:08d}",
            "entity_id": "E0001",
            "time_id": time_id,
            "instrument_type": name,
            "principal_balance": round(balance, 2),
            "interest_rate": rate,
            "interest_expense": round(balance * rate / 12, 2),
            "maturity_date": maturity,
        })
        did += 1

df_debt = pd.DataFrame(debt_rows)
write_csv(df_debt, "debt_schedule_2024_2025.csv")

# COMMAND ----------

# ── fact_fx_rates ───────────────────────────────────────────────────────
print("Generating FX rates...")
BASE_RATES = {
    "EUR": 0.92, "GBP": 0.79, "CAD": 1.36, "MXN": 17.2, "BRL": 4.95,
    "CNY": 7.24, "JPY": 149.5, "KRW": 1320.0, "VND": 24500.0, "INR": 83.1,
}
fx_rows = []
fxid = 1
for m in months:
    time_id = m.strftime("%Y%m%d")
    for ccy, base_rate in BASE_RATES.items():
        spot = round(base_rate * np.random.uniform(0.97, 1.03), 6)
        fx_rows.append({
            "rate_id": f"FX{fxid:06d}",
            "from_currency": ccy, "to_currency": "USD",
            "time_id": time_id,
            "spot_rate": spot,
            "budget_rate": round(base_rate, 6),
            "avg_rate": round((spot + base_rate) / 2, 6),
        })
        fxid += 1

df_fx = pd.DataFrame(fx_rows)
write_csv(df_fx, "fx_rates_2024_2025.csv")

# COMMAND ----------

# ── fact_capex ──────────────────────────────────────────────────────────
print("Generating capex data...")
capex_rows = []
cxid = 1
CAPEX_PROJECTS = [
    "New IMM Assembly Line", "Extruder Capacity Expansion",
    "ERP System Upgrade", "Hot Runner R&D Lab",
    "Warehouse Automation", "Solar Panel Installation",
    "IIoT Platform Build-Out", "Quality Lab Upgrade",
]

for m in months:
    time_id = m.strftime("%Y%m%d")
    for proj in CAPEX_PROJECTS:
        eid = random.choice(entity_ids[:16])
        ccid = random.choice(prod_cc_ids)
        approved = round(np.random.uniform(500_000, 8_000_000), 2)
        spent = round(approved * np.random.uniform(0.0, min(1.0, (m - months[0]).days / 730)), 2)
        capex_rows.append({
            "capex_id": f"CX{cxid:08d}",
            "entity_id": eid,
            "cost_center_id": ccid,
            "time_id": time_id,
            "project_name": proj,
            "capex_category": random.choice(["Growth", "Maintenance", "Regulatory", "IT"]),
            "approved_amount": approved,
            "spent_amount": spent,
            "forecast_amount": round(approved - spent, 2),
        })
        cxid += 1

df_capex = pd.DataFrame(capex_rows)
write_csv(df_capex, "capex_2024_2025.csv")

# COMMAND ----------

print("=" * 60)
print("Bronze data generation complete.")
print(f"All CSVs written to {VOLUME_PATH}")
print("=" * 60)
