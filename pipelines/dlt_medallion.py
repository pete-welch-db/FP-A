# Databricks notebook source
# MAGIC %md
# MAGIC # Nova Molding Systems FP&A — DLT Medallion Pipeline
# MAGIC Bronze → Silver → Gold using Delta Live Tables.
# MAGIC
# MAGIC * **Bronze**: Auto Loader ingestion from `/Volumes/{catalog}/{schema}/raw_landing/`
# MAGIC * **Silver**: Deduplicated, typed, FK-validated
# MAGIC * **Gold**: Pre-aggregated KPI tables consumed by the App, Genie, and Dashboards

# COMMAND ----------

import dlt
from pyspark.sql import functions as F
from pyspark.sql.window import Window

# Pipeline parameters — set via DLT configuration or DAB variables
CATALOG = spark.conf.get("pipeline.catalog", "nova_molding_demo")
SCHEMA = spark.conf.get("pipeline.schema", "fpa")
VOLUME_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/raw_landing"

# ═══════════════════════════════════════════════════════════════════════
# BRONZE LAYER — Raw ingestion with metadata
# ═══════════════════════════════════════════════════════════════════════

def bronze_autoloader(path_pattern, table_name):
    """Factory: returns a DLT streaming table reading CSVs via Auto Loader."""
    @dlt.table(
        name=table_name,
        comment=f"Raw ingestion of {table_name} from CSV",
        table_properties={"quality": "bronze"},
    )
    def _inner():
        return (
            spark.readStream
            .format("cloudFiles")
            .option("cloudFiles.format", "csv")
            .option("cloudFiles.inferColumnTypes", "true")
            .option("header", "true")
            .load(f"{VOLUME_PATH}/{path_pattern}")
            .withColumn("_ingested_at", F.current_timestamp())
            .withColumn("_source_file", F.col("_metadata.file_path"))
        )
    return _inner


# Dimension bronze tables
bronze_entity_master   = bronze_autoloader("entity_master.csv",   "bronze_entity_master")
bronze_account_master  = bronze_autoloader("account_master.csv",  "bronze_account_master")
bronze_scenario_master = bronze_autoloader("scenario_master.csv", "bronze_scenario_master")
bronze_time_master     = bronze_autoloader("time_master.csv",     "bronze_time_master")
bronze_product_master  = bronze_autoloader("product_master.csv",  "bronze_product_master")
bronze_customer_master = bronze_autoloader("customer_master.csv", "bronze_customer_master")
bronze_currency_master = bronze_autoloader("currency_master.csv", "bronze_currency_master")
bronze_cost_center     = bronze_autoloader("cost_center_master.csv", "bronze_cost_center_master")

# Fact bronze tables
bronze_gl_journal      = bronze_autoloader("gl_journal_*.csv",       "bronze_gl_journal")
bronze_orders          = bronze_autoloader("orders_*.csv",           "bronze_orders")
bronze_production      = bronze_autoloader("production_*.csv",       "bronze_production")
bronze_service         = bronze_autoloader("service_*.csv",          "bronze_service")
bronze_working_capital = bronze_autoloader("working_capital_*.csv",  "bronze_working_capital")
bronze_debt_schedule   = bronze_autoloader("debt_schedule_*.csv",    "bronze_debt_schedule")
bronze_fx_rates        = bronze_autoloader("fx_rates_*.csv",         "bronze_fx_rates")
bronze_capex           = bronze_autoloader("capex_*.csv",            "bronze_capex")


# ═══════════════════════════════════════════════════════════════════════
# SILVER LAYER — Deduplicated, typed, expectations enforced
# ═══════════════════════════════════════════════════════════════════════

# ── Dimension tables ────────────────────────────────────────────────────

@dlt.table(
    name="silver_dim_entity",
    comment="Cleaned entity master with consolidation hierarchy",
    table_properties={"quality": "silver"},
)
@dlt.expect_or_drop("valid_entity_id", "entity_id IS NOT NULL")
@dlt.expect("valid_business_unit", "business_unit IS NOT NULL")
def silver_dim_entity():
    w = Window.partitionBy("entity_id").orderBy(F.col("_ingested_at").desc())
    return (
        dlt.read("bronze_entity_master")
        .withColumn("_rn", F.row_number().over(w))
        .filter(F.col("_rn") == 1)
        .drop("_rn", "_ingested_at", "_source_file")
        .withColumn("is_consolidated", F.col("is_consolidated").cast("boolean"))
    )


@dlt.table(
    name="silver_dim_account",
    comment="Cleaned chart of accounts with hierarchy",
    table_properties={"quality": "silver"},
)
@dlt.expect_or_drop("valid_account_id", "account_id IS NOT NULL")
def silver_dim_account():
    w = Window.partitionBy("account_id").orderBy(F.col("_ingested_at").desc())
    return (
        dlt.read("bronze_account_master")
        .withColumn("_rn", F.row_number().over(w))
        .filter(F.col("_rn") == 1)
        .drop("_rn", "_ingested_at", "_source_file")
        .withColumn("is_calculated", F.col("is_calculated").cast("boolean"))
    )


@dlt.table(
    name="silver_dim_scenario",
    comment="Cleaned planning scenarios",
    table_properties={"quality": "silver"},
)
@dlt.expect_or_drop("valid_scenario_id", "scenario_id IS NOT NULL")
def silver_dim_scenario():
    w = Window.partitionBy("scenario_id").orderBy(F.col("_ingested_at").desc())
    return (
        dlt.read("bronze_scenario_master")
        .withColumn("_rn", F.row_number().over(w))
        .filter(F.col("_rn") == 1)
        .drop("_rn", "_ingested_at", "_source_file")
        .withColumn("scenario_year", F.col("scenario_year").cast("int"))
        .withColumn("is_locked", F.col("is_locked").cast("boolean"))
    )


@dlt.table(
    name="silver_dim_time",
    comment="Fiscal calendar dimension",
    table_properties={"quality": "silver"},
)
@dlt.expect_or_drop("valid_time_id", "time_id IS NOT NULL")
def silver_dim_time():
    w = Window.partitionBy("time_id").orderBy(F.col("_ingested_at").desc())
    return (
        dlt.read("bronze_time_master")
        .withColumn("_rn", F.row_number().over(w))
        .filter(F.col("_rn") == 1)
        .drop("_rn", "_ingested_at", "_source_file")
        .withColumn("calendar_date", F.col("calendar_date").cast("date"))
        .withColumn("fiscal_year", F.col("fiscal_year").cast("int"))
        .withColumn("fiscal_month", F.col("fiscal_month").cast("int"))
        .withColumn("fiscal_week", F.col("fiscal_week").cast("int"))
        .withColumn("is_month_end", F.col("is_month_end").cast("boolean"))
        .withColumn("is_quarter_end", F.col("is_quarter_end").cast("boolean"))
    )


@dlt.table(
    name="silver_dim_product",
    comment="Cleaned product master",
    table_properties={"quality": "silver"},
)
@dlt.expect_or_drop("valid_product_id", "product_id IS NOT NULL")
def silver_dim_product():
    w = Window.partitionBy("product_id").orderBy(F.col("_ingested_at").desc())
    return (
        dlt.read("bronze_product_master")
        .withColumn("_rn", F.row_number().over(w))
        .filter(F.col("_rn") == 1)
        .drop("_rn", "_ingested_at", "_source_file")
        .withColumn("is_aftermarket", F.col("is_aftermarket").cast("boolean"))
    )


@dlt.table(
    name="silver_dim_customer",
    comment="Cleaned customer master",
    table_properties={"quality": "silver"},
)
@dlt.expect_or_drop("valid_customer_id", "customer_id IS NOT NULL")
def silver_dim_customer():
    w = Window.partitionBy("customer_id").orderBy(F.col("_ingested_at").desc())
    return (
        dlt.read("bronze_customer_master")
        .withColumn("_rn", F.row_number().over(w))
        .filter(F.col("_rn") == 1)
        .drop("_rn", "_ingested_at", "_source_file")
    )


@dlt.table(
    name="silver_dim_currency",
    comment="Currency reference",
    table_properties={"quality": "silver"},
)
@dlt.expect_or_drop("valid_currency", "currency_code IS NOT NULL")
def silver_dim_currency():
    w = Window.partitionBy("currency_code").orderBy(F.col("_ingested_at").desc())
    return (
        dlt.read("bronze_currency_master")
        .withColumn("_rn", F.row_number().over(w))
        .filter(F.col("_rn") == 1)
        .drop("_rn", "_ingested_at", "_source_file")
    )


@dlt.table(
    name="silver_dim_cost_center",
    comment="Cleaned cost center / plant master",
    table_properties={"quality": "silver"},
)
@dlt.expect_or_drop("valid_cc_id", "cost_center_id IS NOT NULL")
def silver_dim_cost_center():
    w = Window.partitionBy("cost_center_id").orderBy(F.col("_ingested_at").desc())
    return (
        dlt.read("bronze_cost_center_master")
        .withColumn("_rn", F.row_number().over(w))
        .filter(F.col("_rn") == 1)
        .drop("_rn", "_ingested_at", "_source_file")
    )


# ── Fact tables ─────────────────────────────────────────────────────────

@dlt.table(
    name="silver_fact_gl_journal",
    comment="Deduplicated GL journal entries",
    table_properties={"quality": "silver"},
)
@dlt.expect_or_drop("valid_journal_id", "journal_id IS NOT NULL")
@dlt.expect("valid_amount", "amount_local IS NOT NULL")
@dlt.expect("valid_entity_fk", "entity_id IS NOT NULL")
def silver_fact_gl_journal():
    w = Window.partitionBy("journal_id").orderBy(F.col("_ingested_at").desc())
    return (
        dlt.read("bronze_gl_journal")
        .withColumn("_rn", F.row_number().over(w))
        .filter(F.col("_rn") == 1)
        .drop("_rn", "_ingested_at", "_source_file")
        .withColumn("amount_local", F.col("amount_local").cast("decimal(18,2)"))
        .withColumn("amount_usd", F.col("amount_usd").cast("decimal(18,2)"))
    )


@dlt.table(
    name="silver_fact_orders",
    comment="Deduplicated order lines",
    table_properties={"quality": "silver"},
)
@dlt.expect_or_drop("valid_order_id", "order_id IS NOT NULL")
@dlt.expect("positive_qty", "order_qty > 0")
def silver_fact_orders():
    w = Window.partitionBy("order_id").orderBy(F.col("_ingested_at").desc())
    return (
        dlt.read("bronze_orders")
        .withColumn("_rn", F.row_number().over(w))
        .filter(F.col("_rn") == 1)
        .drop("_rn", "_ingested_at", "_source_file")
        .withColumn("order_qty", F.col("order_qty").cast("int"))
        .withColumn("unit_price", F.col("unit_price").cast("decimal(18,2)"))
        .withColumn("discount_pct", F.col("discount_pct").cast("decimal(8,4)"))
        .withColumn("net_amount_usd", F.col("net_amount_usd").cast("decimal(18,2)"))
        .withColumn("backlog_flag", F.col("backlog_flag").cast("boolean"))
    )


@dlt.table(
    name="silver_fact_production",
    comment="Deduplicated production metrics",
    table_properties={"quality": "silver"},
)
@dlt.expect_or_drop("valid_production_id", "production_id IS NOT NULL")
@dlt.expect("valid_units", "units_produced >= 0")
def silver_fact_production():
    w = Window.partitionBy("production_id").orderBy(F.col("_ingested_at").desc())
    return (
        dlt.read("bronze_production")
        .withColumn("_rn", F.row_number().over(w))
        .filter(F.col("_rn") == 1)
        .drop("_rn", "_ingested_at", "_source_file")
        .withColumn("units_produced", F.col("units_produced").cast("int"))
        .withColumn("standard_cost", F.col("standard_cost").cast("decimal(18,2)"))
        .withColumn("actual_cost", F.col("actual_cost").cast("decimal(18,2)"))
        .withColumn("utilization_pct", F.col("utilization_pct").cast("decimal(8,4)"))
        .withColumn("energy_cost", F.col("energy_cost").cast("decimal(18,2)"))
        .withColumn("material_cost", F.col("material_cost").cast("decimal(18,2)"))
        .withColumn("scrap_rate", F.col("scrap_rate").cast("decimal(8,4)"))
    )


@dlt.table(
    name="silver_fact_service",
    comment="Deduplicated service/aftermarket records",
    table_properties={"quality": "silver"},
)
@dlt.expect_or_drop("valid_service_id", "service_id IS NOT NULL")
@dlt.expect("valid_contract_type", "contract_type IS NOT NULL")
def silver_fact_service():
    w = Window.partitionBy("service_id").orderBy(F.col("_ingested_at").desc())
    return (
        dlt.read("bronze_service")
        .withColumn("_rn", F.row_number().over(w))
        .filter(F.col("_rn") == 1)
        .drop("_rn", "_ingested_at", "_source_file")
        .withColumn("contract_value_usd", F.col("contract_value_usd").cast("decimal(18,2)"))
        .withColumn("parts_revenue_usd", F.col("parts_revenue_usd").cast("decimal(18,2)"))
        .withColumn("labor_revenue_usd", F.col("labor_revenue_usd").cast("decimal(18,2)"))
        .withColumn("is_renewal", F.col("is_renewal").cast("boolean"))
        .withColumn("churn_flag", F.col("churn_flag").cast("boolean"))
        .withColumn("service_attach_flag", F.col("service_attach_flag").cast("boolean"))
    )


@dlt.table(
    name="silver_fact_working_capital",
    comment="Deduplicated working capital snapshots",
    table_properties={"quality": "silver"},
)
@dlt.expect_or_drop("valid_wc_id", "wc_id IS NOT NULL")
@dlt.expect("valid_entity_fk", "entity_id IS NOT NULL")
def silver_fact_working_capital():
    w = Window.partitionBy("wc_id").orderBy(F.col("_ingested_at").desc())
    return (
        dlt.read("bronze_working_capital")
        .withColumn("_rn", F.row_number().over(w))
        .filter(F.col("_rn") == 1)
        .drop("_rn", "_ingested_at", "_source_file")
        .withColumn("ar_balance", F.col("ar_balance").cast("decimal(18,2)"))
        .withColumn("ap_balance", F.col("ap_balance").cast("decimal(18,2)"))
        .withColumn("inventory_raw", F.col("inventory_raw").cast("decimal(18,2)"))
        .withColumn("inventory_wip", F.col("inventory_wip").cast("decimal(18,2)"))
        .withColumn("inventory_finished", F.col("inventory_finished").cast("decimal(18,2)"))
        .withColumn("dso", F.col("dso").cast("decimal(8,1)"))
        .withColumn("dpo", F.col("dpo").cast("decimal(8,1)"))
        .withColumn("inventory_turns", F.col("inventory_turns").cast("decimal(8,2)"))
    )


@dlt.table(
    name="silver_fact_debt_schedule",
    comment="Deduplicated debt schedule",
    table_properties={"quality": "silver"},
)
@dlt.expect_or_drop("valid_debt_id", "debt_id IS NOT NULL")
@dlt.expect("valid_principal", "principal_balance >= 0")
def silver_fact_debt_schedule():
    w = Window.partitionBy("debt_id").orderBy(F.col("_ingested_at").desc())
    return (
        dlt.read("bronze_debt_schedule")
        .withColumn("_rn", F.row_number().over(w))
        .filter(F.col("_rn") == 1)
        .drop("_rn", "_ingested_at", "_source_file")
        .withColumn("principal_balance", F.col("principal_balance").cast("decimal(18,2)"))
        .withColumn("interest_rate", F.col("interest_rate").cast("decimal(8,6)"))
        .withColumn("interest_expense", F.col("interest_expense").cast("decimal(18,2)"))
        .withColumn("maturity_date", F.col("maturity_date").cast("date"))
    )


@dlt.table(
    name="silver_fact_fx_rates",
    comment="Deduplicated FX rates",
    table_properties={"quality": "silver"},
)
@dlt.expect_or_drop("valid_rate_id", "rate_id IS NOT NULL")
@dlt.expect("positive_rate", "spot_rate > 0")
def silver_fact_fx_rates():
    w = Window.partitionBy("rate_id").orderBy(F.col("_ingested_at").desc())
    return (
        dlt.read("bronze_fx_rates")
        .withColumn("_rn", F.row_number().over(w))
        .filter(F.col("_rn") == 1)
        .drop("_rn", "_ingested_at", "_source_file")
        .withColumn("spot_rate", F.col("spot_rate").cast("decimal(12,6)"))
        .withColumn("budget_rate", F.col("budget_rate").cast("decimal(12,6)"))
        .withColumn("avg_rate", F.col("avg_rate").cast("decimal(12,6)"))
    )


@dlt.table(
    name="silver_fact_capex",
    comment="Deduplicated capex records",
    table_properties={"quality": "silver"},
)
@dlt.expect_or_drop("valid_capex_id", "capex_id IS NOT NULL")
@dlt.expect("valid_approved", "approved_amount >= 0")
def silver_fact_capex():
    w = Window.partitionBy("capex_id").orderBy(F.col("_ingested_at").desc())
    return (
        dlt.read("bronze_capex")
        .withColumn("_rn", F.row_number().over(w))
        .filter(F.col("_rn") == 1)
        .drop("_rn", "_ingested_at", "_source_file")
        .withColumn("approved_amount", F.col("approved_amount").cast("decimal(18,2)"))
        .withColumn("spent_amount", F.col("spent_amount").cast("decimal(18,2)"))
        .withColumn("forecast_amount", F.col("forecast_amount").cast("decimal(18,2)"))
    )


# ═══════════════════════════════════════════════════════════════════════
# GOLD LAYER — Aggregated KPI tables for App, Genie, Dashboards
# ═══════════════════════════════════════════════════════════════════════

@dlt.table(
    name="gold_revenue_summary",
    comment="Revenue by BU, region, end-market, period, and scenario",
    table_properties={"quality": "gold"},
)
def gold_revenue_summary():
    gl = dlt.read("silver_fact_gl_journal")
    acct = dlt.read("silver_dim_account")
    entity = dlt.read("silver_dim_entity")
    time_dim = dlt.read("silver_dim_time")
    scenario = dlt.read("silver_dim_scenario")

    rev = (
        gl.join(acct, "account_id")
        .filter(F.col("account_type") == "Revenue")
        .join(entity, "entity_id")
        .join(
            time_dim.select("time_id", "fiscal_year", "fiscal_quarter", "fiscal_month"),
            "time_id",
        )
        .join(scenario.select("scenario_id", "scenario_name"), "scenario_id")
        .groupBy(
            "business_unit", "region", "fiscal_year",
            "fiscal_quarter", "fiscal_month", "scenario_name",
        )
        .agg(F.sum("amount_usd").alias("revenue_usd"))
    )

    # YoY growth — self-join on prior year
    prior = rev.withColumnRenamed("revenue_usd", "py_revenue").withColumnRenamed(
        "fiscal_year", "py_year"
    )
    joined = rev.join(
        prior,
        (rev.business_unit == prior.business_unit)
        & (rev.region == prior.region)
        & (rev.fiscal_month == prior.fiscal_month)
        & (rev.scenario_name == prior.scenario_name)
        & (rev.fiscal_year == prior.py_year + 1),
        "left",
    ).select(
        rev["*"],
        F.when(F.col("py_revenue") != 0,
               (F.col("revenue_usd") - F.col("py_revenue")) / F.col("py_revenue") * 100
        ).otherwise(F.lit(None)).alias("yoy_growth_pct"),
    )

    # Budget variance — join Actual to Budget
    budget = rev.filter(F.col("scenario_name") == "Budget").select(
        "business_unit", "region", "fiscal_year", "fiscal_month",
        F.col("revenue_usd").alias("budget_revenue"),
    )
    result = joined.join(
        budget,
        ["business_unit", "region", "fiscal_year", "fiscal_month"],
        "left",
    ).withColumn(
        "budget_variance_pct",
        F.when(F.col("budget_revenue") != 0,
               (F.col("revenue_usd") - F.col("budget_revenue")) / F.col("budget_revenue") * 100
        ).otherwise(F.lit(None)),
    ).drop("budget_revenue")

    return result


@dlt.table(
    name="gold_ebitda_bridge",
    comment="EBITDA walk: revenue through cost categories to EBITDA",
    table_properties={"quality": "gold"},
)
def gold_ebitda_bridge():
    gl = dlt.read("silver_fact_gl_journal")
    acct = dlt.read("silver_dim_account")
    entity = dlt.read("silver_dim_entity")
    time_dim = dlt.read("silver_dim_time")
    scenario = dlt.read("silver_dim_scenario")

    base = (
        gl.join(acct.select("account_id", "account_type"), "account_id")
        .join(entity.select("entity_id", "business_unit", "region"), "entity_id")
        .join(time_dim.select("time_id", "fiscal_year", "fiscal_quarter"), "time_id")
        .join(scenario.select("scenario_id", "scenario_name"), "scenario_id")
        .groupBy("business_unit", "region", "fiscal_year", "fiscal_quarter", "scenario_name", "account_type")
        .agg(F.sum("amount_usd").alias("total_usd"))
    )

    pivoted = (
        base.groupBy("business_unit", "region", "fiscal_year", "fiscal_quarter", "scenario_name")
        .pivot("account_type", ["Revenue", "COGS", "OpEx"])
        .agg(F.sum("total_usd"))
    )

    return (
        pivoted
        .withColumnRenamed("Revenue", "revenue")
        .withColumnRenamed("COGS", "cogs")
        .withColumnRenamed("OpEx", "opex")
        .withColumn("gross_profit", F.col("revenue") - F.coalesce(F.col("cogs"), F.lit(0)))
        .withColumn("ebitda", F.col("gross_profit") - F.coalesce(F.col("opex"), F.lit(0)))
        .withColumn("ebitda_margin",
                     F.when(F.col("revenue") != 0, F.col("ebitda") / F.col("revenue")).otherwise(F.lit(None)))
    )


@dlt.table(
    name="gold_cash_flow_summary",
    comment="Free cash flow and conversion by entity and period",
    table_properties={"quality": "gold"},
)
def gold_cash_flow_summary():
    gl = dlt.read("silver_fact_gl_journal")
    acct = dlt.read("silver_dim_account")
    entity = dlt.read("silver_dim_entity")
    time_dim = dlt.read("silver_dim_time")

    cf = (
        gl.join(acct.select("account_id", "account_type", "account_group"), "account_id")
        .filter(F.col("account_type") == "CF")
        .join(entity.select("entity_id", "entity_name", "region"), "entity_id")
        .join(time_dim.select("time_id", "fiscal_year", "fiscal_quarter"), "time_id")
        .groupBy("entity_name", "region", "fiscal_year", "fiscal_quarter", "account_group")
        .agg(F.sum("amount_usd").alias("cf_amount"))
    )

    pivoted = (
        cf.groupBy("entity_name", "region", "fiscal_year", "fiscal_quarter")
        .pivot("account_group", ["CF_OPS", "CF_INV", "CF_FIN"])
        .agg(F.sum("cf_amount"))
    )

    return (
        pivoted
        .withColumnRenamed("CF_OPS", "operating_cf")
        .withColumnRenamed("CF_INV", "capex")
        .withColumnRenamed("CF_FIN", "financing_cf")
        .withColumn("fcf", F.coalesce(F.col("operating_cf"), F.lit(0)) + F.coalesce(F.col("capex"), F.lit(0)))
        .withColumn("fcf_conversion_pct",
                     F.when(F.col("operating_cf") != 0, F.col("fcf") / F.col("operating_cf") * 100)
                     .otherwise(F.lit(None)))
    )


@dlt.table(
    name="gold_leverage_metrics",
    comment="Net leverage and interest coverage by period",
    table_properties={"quality": "gold"},
)
def gold_leverage_metrics():
    debt = dlt.read("silver_fact_debt_schedule")
    time_dim = dlt.read("silver_dim_time")

    return (
        debt
        .join(time_dim.select("time_id", "fiscal_year", "fiscal_quarter"), "time_id")
        .groupBy("entity_id", "fiscal_year", "fiscal_quarter")
        .agg(
            F.sum("principal_balance").alias("net_debt"),
            F.sum("interest_expense").alias("total_interest"),
        )
        .withColumn("ltm_ebitda", F.lit(350_000_000))  # Placeholder — will be enriched
        .withColumn("net_leverage", F.col("net_debt") / F.col("ltm_ebitda"))
        .withColumn("interest_coverage",
                     F.when(F.col("total_interest") > 0, F.col("ltm_ebitda") / F.col("total_interest"))
                     .otherwise(F.lit(None)))
    )


@dlt.table(
    name="gold_working_capital",
    comment="DSO, DPO, inventory turns by entity and period",
    table_properties={"quality": "gold"},
)
def gold_working_capital():
    wc = dlt.read("silver_fact_working_capital")
    entity = dlt.read("silver_dim_entity")
    time_dim = dlt.read("silver_dim_time")

    return (
        wc.join(entity.select("entity_id", "entity_name", "region", "business_unit"), "entity_id")
        .join(time_dim.select("time_id", "fiscal_year", "fiscal_quarter", "fiscal_month"), "time_id")
        .groupBy("entity_name", "business_unit", "region", "fiscal_year", "fiscal_quarter", "fiscal_month")
        .agg(
            F.avg("dso").alias("dso"),
            F.avg("dpo").alias("dpo"),
            F.avg("inventory_turns").alias("inventory_turns"),
        )
        .withColumn("cash_conversion_cycle", F.col("dso") - F.col("dpo") + F.lit(30))
    )


@dlt.table(
    name="gold_aftermarket_mix",
    comment="Aftermarket revenue share and service attach rate",
    table_properties={"quality": "gold"},
)
def gold_aftermarket_mix():
    svc = dlt.read("silver_fact_service")
    entity = dlt.read("silver_dim_entity")
    time_dim = dlt.read("silver_dim_time")
    orders = dlt.read("silver_fact_orders")

    svc_agg = (
        svc.join(entity.select("entity_id", "business_unit", "region"), "entity_id")
        .join(time_dim.select("time_id", "fiscal_year", "fiscal_quarter"), "time_id")
        .groupBy("business_unit", "region", "fiscal_year", "fiscal_quarter")
        .agg(
            F.sum("contract_value_usd").alias("aftermarket_revenue"),
            F.avg(F.col("service_attach_flag").cast("int")).alias("service_attach_rate"),
        )
    )

    order_rev = (
        orders.join(entity.select("entity_id", "business_unit", "region"), "entity_id")
        .join(time_dim.select("time_id", "fiscal_year", "fiscal_quarter"), "time_id")
        .groupBy("business_unit", "region", "fiscal_year", "fiscal_quarter")
        .agg(F.sum("net_amount_usd").alias("total_revenue"))
    )

    return (
        svc_agg.join(order_rev, ["business_unit", "region", "fiscal_year", "fiscal_quarter"], "left")
        .withColumn("aftermarket_mix_pct",
                     F.when(F.col("total_revenue") > 0,
                            F.col("aftermarket_revenue") / F.col("total_revenue") * 100)
                     .otherwise(F.lit(None)))
    )


@dlt.table(
    name="gold_order_backlog",
    comment="Order intake, backlog, and book-to-bill by BU",
    table_properties={"quality": "gold"},
)
def gold_order_backlog():
    orders = dlt.read("silver_fact_orders")
    entity = dlt.read("silver_dim_entity")
    time_dim = dlt.read("silver_dim_time")

    return (
        orders
        .join(entity.select("entity_id", "business_unit", "region"), "entity_id")
        .join(time_dim.select("time_id", "fiscal_year", "fiscal_quarter", "fiscal_month"), "time_id")
        .groupBy("business_unit", "region", "fiscal_year", "fiscal_quarter", "fiscal_month")
        .agg(
            F.sum("net_amount_usd").alias("order_intake"),
            F.sum(F.when(F.col("backlog_flag"), F.col("net_amount_usd")).otherwise(0)).alias("backlog_value"),
            F.sum(F.when(F.col("order_status") == "Shipped", F.col("net_amount_usd")).otherwise(0)).alias("shipped_revenue"),
        )
        .withColumn("book_to_bill_ratio",
                     F.when(F.col("shipped_revenue") > 0, F.col("order_intake") / F.col("shipped_revenue"))
                     .otherwise(F.lit(None)))
    )


@dlt.table(
    name="gold_plant_performance",
    comment="Plant utilization, cost variance, and scrap rate",
    table_properties={"quality": "gold"},
)
def gold_plant_performance():
    prod = dlt.read("silver_fact_production")
    cc = dlt.read("silver_dim_cost_center")
    time_dim = dlt.read("silver_dim_time")

    return (
        prod
        .join(cc.select("cost_center_id", "plant_id", "plant_name", "plant_country"), "cost_center_id")
        .join(time_dim.select("time_id", "fiscal_year", "fiscal_quarter"), "time_id")
        .groupBy("plant_id", "plant_name", "plant_country", "fiscal_year", "fiscal_quarter")
        .agg(
            F.avg("utilization_pct").alias("utilization_pct"),
            F.avg(
                (F.col("actual_cost") - F.col("standard_cost")) / F.col("standard_cost") * 100
            ).alias("cost_variance_pct"),
            F.avg("scrap_rate").alias("scrap_rate"),
            F.sum("units_produced").alias("total_units"),
        )
    )
