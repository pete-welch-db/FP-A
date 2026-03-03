#!/usr/bin/env bash
# ==============================================================================
# Nova Molding Systems FP&A — Post-Deploy ID Capture
# Captures the Genie Space ID and Dashboard embed URL after the data pipeline
# completes, then patches local .env so runtime config stays out of tracked files.
# ==============================================================================
set -euo pipefail

BUNDLE_TARGET="${1:-dev}"
ENV_FILE=".env"

update_env_var() {
    local key="$1"
    local value="$2"
    python3 - "$ENV_FILE" "$key" "$value" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
key = sys.argv[2]
value = sys.argv[3]
if path.exists():
    lines = path.read_text(encoding="utf-8").splitlines()
else:
    lines = []

updated = False
for idx, line in enumerate(lines):
    if line.startswith(f"{key}="):
        lines[idx] = f"{key}={value}"
        updated = True
        break

if not updated:
    lines.append(f"{key}={value}")

path.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY
}

echo "=== Nova Molding Systems FP&A: Capturing post-deploy IDs (target: ${BUNDLE_TARGET}) ==="

if [ ! -f "${ENV_FILE}" ]; then
    echo ">> ${ENV_FILE} not found. Copying from env.example ..."
    cp env.example "${ENV_FILE}"
fi

# ---------- Genie Space ID ----------
echo ""
echo ">> Fetching Genie Space ID from last pipeline run…"
GENIE_SPACE_ID=$(databricks bundle run data_pipeline --output json 2>/dev/null \
  | python3 -c "import sys,json; tasks=json.load(sys.stdin).get('tasks',[]); print(next((t['notebook_output']['result'] for t in tasks if t['task_key']=='deploy_genie'), ''))" \
  2>/dev/null || echo "")

if [ -z "${GENIE_SPACE_ID}" ]; then
    echo "   Could not auto-capture GENIE_SPACE_ID."
    echo "   Manually set it in ${ENV_FILE} or via:"
    echo "     databricks genie list --output json"
    read -rp "   Enter GENIE_SPACE_ID manually (or press Enter to skip): " GENIE_SPACE_ID
fi

if [ -n "${GENIE_SPACE_ID}" ]; then
    echo "   GENIE_SPACE_ID=${GENIE_SPACE_ID}"
    update_env_var "GENIE_SPACE_ID" "${GENIE_SPACE_ID}"
fi

# ---------- Dashboard Embed URL ----------
echo ""
echo ">> Fetching Dashboard embed URLs…"
DASHBOARD_ID=$(databricks bundle summary --output json 2>/dev/null \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('resources',{}).get('dashboards',{}).get('nova_molding_fpa',{}).get('id',''))" \
  2>/dev/null || echo "")
DASHBOARD_ID_V2=$(databricks bundle summary --output json 2>/dev/null \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('resources',{}).get('dashboards',{}).get('nova_molding_fpa_metrics_v2',{}).get('id',''))" \
  2>/dev/null || echo "")

WORKSPACE_HOST=$(databricks auth env 2>/dev/null \
  | python3 -c "import sys; lines=sys.stdin.read().splitlines(); print(next((ln.split('=',1)[1] for ln in lines if ln.startswith('DATABRICKS_HOST=')), ''))" \
  2>/dev/null || echo "")

if [ -n "${DASHBOARD_ID}" ] && [ -n "${WORKSPACE_HOST}" ]; then
    DASHBOARD_EMBED_URL="${WORKSPACE_HOST}/embed/dashboardsv3/${DASHBOARD_ID}"
    echo "   DASHBOARD_EMBED_URL=${DASHBOARD_EMBED_URL}"
    update_env_var "DASHBOARD_EMBED_URL" "${DASHBOARD_EMBED_URL}"
else
    echo "   Could not auto-capture DASHBOARD_EMBED_URL."
    echo "   Set it manually in ${ENV_FILE} after deployment."
fi

if [ -n "${DASHBOARD_ID_V2}" ] && [ -n "${WORKSPACE_HOST}" ]; then
    DASHBOARD_EMBED_URL_V2="${WORKSPACE_HOST}/embed/dashboardsv3/${DASHBOARD_ID_V2}"
    echo "   DASHBOARD_EMBED_URL_V2=${DASHBOARD_EMBED_URL_V2}"
    update_env_var "DASHBOARD_EMBED_URL_V2" "${DASHBOARD_EMBED_URL_V2}"
else
    echo "   Could not auto-capture DASHBOARD_EMBED_URL_V2."
    echo "   Set it manually in ${ENV_FILE} after deployment."
fi

echo ""
echo "=== Done. Updated ${ENV_FILE}. Redeploy app if app/app.yaml values changed. ==="
