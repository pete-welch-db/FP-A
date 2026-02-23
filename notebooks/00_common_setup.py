# Databricks notebook source
# MAGIC %md
# MAGIC # Nova Molding Systems FP&A Demo — Common Setup
# MAGIC Creates the Unity Catalog catalog, schema, and volumes required by all
# MAGIC downstream notebooks and the DLT pipeline.

# COMMAND ----------

dbutils.widgets.text("catalog", "nova_molding_demo", "UC Catalog")
dbutils.widgets.text("schema", "fpa", "UC Schema")

catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")

# COMMAND ----------

spark.sql(f"CREATE CATALOG IF NOT EXISTS {catalog}")
spark.sql(f"USE CATALOG {catalog}")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {schema}")
spark.sql(f"USE SCHEMA {schema}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create Volumes
# MAGIC `raw_landing` — holds CSV extracts that simulate OneStream data feeds.

# COMMAND ----------

spark.sql(f"CREATE VOLUME IF NOT EXISTS {catalog}.{schema}.raw_landing")

# COMMAND ----------

print(f"Setup complete: {catalog}.{schema}")
print(f"Volume path: /Volumes/{catalog}/{schema}/raw_landing")
