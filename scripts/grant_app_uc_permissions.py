# Databricks notebook source
# MAGIC %md
# MAGIC # Grant App Service Principal UC Permissions
# MAGIC Ensures the Databricks App service principal can query required UC resources.

# COMMAND ----------

dbutils.widgets.text("catalog", "nova_molding_demo", "UC Catalog")
dbutils.widgets.text("schema", "fpa_dev", "UC Schema")
dbutils.widgets.text("app_name", "", "Databricks App name")

catalog = dbutils.widgets.get("catalog").strip()
schema = dbutils.widgets.get("schema").strip()
app_name = dbutils.widgets.get("app_name").strip()

if not catalog or not schema or not app_name:
    raise ValueError("catalog, schema, and app_name parameters are required")

# COMMAND ----------

import json
import requests

host = spark.conf.get("spark.databricks.workspaceUrl")
token = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()
headers = {"Authorization": f"Bearer {token}"}
base_url = f"https://{host}"

resp = requests.get(f"{base_url}/api/2.0/apps/{app_name}", headers=headers, timeout=30)
if not resp.ok:
    raise RuntimeError(f"Failed to get app '{app_name}': {resp.status_code} {resp.text[:1000]}")

app_info = resp.json()
service_principal = (
    app_info.get("service_principal_client_id")
    or app_info.get("id")
)
if not service_principal:
    raise RuntimeError(f"Could not resolve service principal for app '{app_name}'")

print(f"Resolved app service principal: {service_principal}")

# COMMAND ----------

def q(identifier: str) -> str:
    return f"`{identifier.replace('`', '``')}`"


def run_grant(sql_text: str) -> bool:
    try:
        spark.sql(sql_text)
        print(f"OK: {sql_text}")
        return True
    except Exception as exc:
        print(f"WARN: {sql_text} -> {exc}")
        return False


principal = q(service_principal)
catalog_q = q(catalog)
schema_q = q(schema)

run_grant(f"GRANT USE CATALOG ON CATALOG {catalog_q} TO {principal}")
run_grant(f"GRANT USE SCHEMA ON SCHEMA {catalog_q}.{schema_q} TO {principal}")

# COMMAND ----------

objects = spark.sql(f"SHOW TABLES IN {catalog_q}.{schema_q}").collect()
granted = 0
failed = []

for row in objects:
    obj_name = row["tableName"]
    obj_q = q(obj_name)
    stmt = f"GRANT SELECT ON TABLE {catalog_q}.{schema_q}.{obj_q} TO {principal}"
    if run_grant(stmt):
        granted += 1
    else:
        failed.append(obj_name)

summary = {
    "app_name": app_name,
    "service_principal": service_principal,
    "catalog": catalog,
    "schema": schema,
    "objects_seen": len(objects),
    "grants_succeeded": granted,
    "grants_failed": failed,
}

print("\nPermission grant summary:")
print(json.dumps(summary, indent=2))
dbutils.notebook.exit(json.dumps(summary))
