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

DATABRICKS_HOST = os.getenv("DATABRICKS_HOST", "")
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN", "")
DATABRICKS_HTTP_PATH = os.getenv("DATABRICKS_HTTP_PATH", "")
DATABRICKS_CATALOG = os.getenv("DATABRICKS_CATALOG", "nova_molding_demo")
DATABRICKS_SCHEMA = os.getenv("DATABRICKS_SCHEMA", "fpa")
GENIE_SPACE_ID = os.getenv("GENIE_SPACE_ID", "")
DASHBOARD_EMBED_URL = os.getenv("DASHBOARD_EMBED_URL", "")
DASHBOARD_EMBED_URL_V2 = os.getenv("DASHBOARD_EMBED_URL_V2", "")
USE_MOCK_DATA = os.getenv("USE_MOCK_DATA", "false").lower() in ("true", "1", "yes")
