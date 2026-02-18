"""
Milacron FP&A App — Centralised Configuration
ONLY place where environment variables are read.
"""
import os

DATABRICKS_HOST = os.getenv("DATABRICKS_HOST", "")
DATABRICKS_HTTP_PATH = os.getenv("DATABRICKS_HTTP_PATH", "")
DATABRICKS_CATALOG = os.getenv("DATABRICKS_CATALOG", "milacron_demo")
DATABRICKS_SCHEMA = os.getenv("DATABRICKS_SCHEMA", "fpa")
GENIE_SPACE_ID = os.getenv("GENIE_SPACE_ID", "")
DASHBOARD_EMBED_URL = os.getenv("DASHBOARD_EMBED_URL", "")
USE_MOCK_DATA = os.getenv("USE_MOCK_DATA", "false").lower() in ("true", "1", "yes")
