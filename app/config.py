"""
Nova Molding Systems FP&A App — Centralised Configuration
ONLY place where environment variables are read.
"""
import os
from pathlib import Path


def _load_local_env() -> None:
    """Load key/value pairs from repo .env for local runs.

    Streamlit local execution does not automatically source ../.env.
    We set defaults only when variables are not already present.
    """
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_local_env()

DATABRICKS_HOST = os.getenv("DATABRICKS_HOST", "") or "https://adb-984752964297111.11.azuredatabricks.net/"
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN", "")
DATABRICKS_HTTP_PATH = os.getenv("DATABRICKS_HTTP_PATH", "") or "/sql/1.0/warehouses/148ccb90800933a1"
DATABRICKS_CATALOG = os.getenv("DATABRICKS_CATALOG", "") or "nova_molding_demo"
DATABRICKS_SCHEMA = os.getenv("DATABRICKS_SCHEMA", "") or "fpa_dev"
GENIE_SPACE_ID = os.getenv("GENIE_SPACE_ID", "")
DASHBOARD_EMBED_URL = os.getenv("DASHBOARD_EMBED_URL", "")
DASHBOARD_EMBED_URL_V2 = os.getenv("DASHBOARD_EMBED_URL_V2", "")
USE_MOCK_DATA = os.getenv("USE_MOCK_DATA", "false").lower() in ("true", "1", "yes")

_HOST = "https://adb-984752964297111.11.azuredatabricks.net"

_NOVA_DEFAULTS = {
    "genie_space_id": "01f110cdec221d0d9fcb269d8b838a57",
    "dashboard_embed_url": f"{_HOST}/embed/dashboardsv3/01f110cc93bf12279633a8034e66303d?o=984752964297111",
}
_MILACRON_DEFAULTS = {
    "genie_space_id": "01f11ee6793d135883a680f186c75ac6",
    "dashboard_embed_url": f"{_HOST}/embed/dashboardsv3/01f11ee66d0112d5894b560efe6d37c9?o=984752964297111",
}

BRAND_CONFIG = {
    "Nova Molding Systems": {
        "company": "Nova Molding Systems",
        "page_title": "Nova Molding Systems FP&A",
        "dashboard_subtitle": "AI/BI Dashboard — Nova Molding Systems FP&A",
        "genie_space_id": GENIE_SPACE_ID or _NOVA_DEFAULTS["genie_space_id"],
        "dashboard_embed_url": DASHBOARD_EMBED_URL_V2 or DASHBOARD_EMBED_URL or _NOVA_DEFAULTS["dashboard_embed_url"],
    },
    "Milacron": {
        "company": "Milacron",
        "page_title": "Milacron FP&A",
        "dashboard_subtitle": "AI/BI Dashboard — Milacron FP&A",
        "genie_space_id": _MILACRON_DEFAULTS["genie_space_id"],
        "dashboard_embed_url": _MILACRON_DEFAULTS["dashboard_embed_url"],
    },
}

_DEFAULT_BRAND = "Nova Molding Systems"


def get_brand(key: str = None):
    """Return the active brand config dict, or a single value if key is given."""
    import streamlit as st
    brand_name = st.session_state.get("brand", _DEFAULT_BRAND)
    brand = BRAND_CONFIG.get(brand_name, BRAND_CONFIG[_DEFAULT_BRAND])
    return brand[key] if key else brand
