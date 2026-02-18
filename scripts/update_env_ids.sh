#!/usr/bin/env bash
# ==============================================================================
# Milacron FP&A — Post-Deploy ID Capture
# Captures the Genie Space ID and Dashboard embed URL after the data pipeline
# completes, then patches app/app.yaml so the Streamlit app can reference them.
# ==============================================================================
set -euo pipefail

BUNDLE_TARGET="${1:-dev}"
APP_YAML="app/app.yaml"

echo "=== Milacron FP&A: Capturing post-deploy IDs (target: ${BUNDLE_TARGET}) ==="

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
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s|GENIE_SPACE_ID.*|GENIE_SPACE_ID\n    value: \"${GENIE_SPACE_ID}\"|" "${APP_YAML}"
    else
        sed -i "s|GENIE_SPACE_ID.*|GENIE_SPACE_ID\n    value: \"${GENIE_SPACE_ID}\"|" "${APP_YAML}"
    fi
fi

# ---------- Dashboard Embed URL ----------
echo ""
echo ">> Fetching Dashboard embed URL…"
DASHBOARD_ID=$(databricks bundle summary --output json 2>/dev/null \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('resources',{}).get('dashboards',{}).get('milacron_fpa',{}).get('id',''))" \
  2>/dev/null || echo "")

if [ -n "${DASHBOARD_ID}" ]; then
    WORKSPACE_HOST=$(databricks auth env 2>/dev/null | grep DATABRICKS_HOST | cut -d= -f2 || echo "")
    DASHBOARD_EMBED_URL="${WORKSPACE_HOST}/embed/dashboardsv3/${DASHBOARD_ID}"
    echo "   DASHBOARD_EMBED_URL=${DASHBOARD_EMBED_URL}"

    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s|DASHBOARD_EMBED_URL.*|DASHBOARD_EMBED_URL\n    value: \"${DASHBOARD_EMBED_URL}\"|" "${APP_YAML}"
    else
        sed -i "s|DASHBOARD_EMBED_URL.*|DASHBOARD_EMBED_URL\n    value: \"${DASHBOARD_EMBED_URL}\"|" "${APP_YAML}"
    fi
else
    echo "   Could not auto-capture DASHBOARD_EMBED_URL."
    echo "   Set it manually in ${APP_YAML} after deployment."
fi

echo ""
echo "=== Done. Redeploy the app with: databricks bundle deploy --force ==="
