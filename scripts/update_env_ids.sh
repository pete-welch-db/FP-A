#!/usr/bin/env bash
# ==============================================================================
# Nova Molding Systems FP&A — Post-Deploy ID Capture
# Captures the Genie Space ID and Dashboard embed URL after the data pipeline
# completes, then patches app/app.yaml so the Streamlit app can reference them.
# ==============================================================================
set -euo pipefail

BUNDLE_TARGET="${1:-dev}"
APP_YAML="app/app.yaml"

update_app_yaml_env() {
    local key="$1"
    local value="$2"
    python3 - "$APP_YAML" "$key" "$value" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
key = sys.argv[2]
value = sys.argv[3]
lines = path.read_text(encoding="utf-8").splitlines()

updated = False
for idx, line in enumerate(lines):
    if line.strip() == f"- name: {key}":
        if idx + 1 < len(lines) and lines[idx + 1].lstrip().startswith("value:"):
            indent = lines[idx + 1][:len(lines[idx + 1]) - len(lines[idx + 1].lstrip())]
            lines[idx + 1] = f'{indent}value: "{value}"'
            updated = True
            break

if not updated:
    lines.append(f"  - name: {key}")
    lines.append(f'    value: "{value}"')

path.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY
}

echo "=== Nova Molding Systems FP&A: Capturing post-deploy IDs (target: ${BUNDLE_TARGET}) ==="

# ---------- Genie Space ID ----------
echo ""
echo ">> Fetching Genie Space ID from last pipeline run…"
GENIE_SPACE_ID=$(databricks bundle run data_pipeline --output json 2>/dev/null \
  | python3 -c "import sys,json; tasks=json.load(sys.stdin).get('tasks',[]); print(next((t['notebook_output']['result'] for t in tasks if t['task_key']=='deploy_genie'), ''))" \
  2>/dev/null || echo "")

if [ -z "${GENIE_SPACE_ID}" ]; then
    echo "   Could not auto-capture GENIE_SPACE_ID."
    echo "   Manually set it in ${APP_YAML} or via:"
    echo "     databricks genie list --output json"
    read -rp "   Enter GENIE_SPACE_ID manually (or press Enter to skip): " GENIE_SPACE_ID
fi

if [ -n "${GENIE_SPACE_ID}" ]; then
    echo "   GENIE_SPACE_ID=${GENIE_SPACE_ID}"
    update_app_yaml_env "GENIE_SPACE_ID" "${GENIE_SPACE_ID}"
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
    update_app_yaml_env "DASHBOARD_EMBED_URL" "${DASHBOARD_EMBED_URL}"
else
    echo "   Could not auto-capture DASHBOARD_EMBED_URL."
    echo "   Set it manually in ${APP_YAML} after deployment."
fi

if [ -n "${DASHBOARD_ID_V2}" ] && [ -n "${WORKSPACE_HOST}" ]; then
    DASHBOARD_EMBED_URL_V2="${WORKSPACE_HOST}/embed/dashboardsv3/${DASHBOARD_ID_V2}"
    echo "   DASHBOARD_EMBED_URL_V2=${DASHBOARD_EMBED_URL_V2}"
    update_app_yaml_env "DASHBOARD_EMBED_URL_V2" "${DASHBOARD_EMBED_URL_V2}"
else
    echo "   Could not auto-capture DASHBOARD_EMBED_URL_V2."
    echo "   Set it manually in ${APP_YAML} after deployment."
fi

echo ""
echo "=== Done. Redeploy the app with: databricks bundle deploy --force ==="
