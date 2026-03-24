"""
Nova Molding Systems FP&A — Data Loader
Centralised SQL execution with connection pooling, caching, numeric
coercion, and graceful fallback to mock data.
"""
import logging
import streamlit as st
import pandas as pd
from databricks import sql
from databricks.sdk.core import Config

from config import (
    DATABRICKS_HOST,
    DATABRICKS_TOKEN,
    DATABRICKS_HTTP_PATH,
    USE_MOCK_DATA,
    DATABRICKS_CATALOG,
    DATABRICKS_SCHEMA,
)
from data.mock_data import MOCK_REGISTRY

_log = logging.getLogger(__name__)


def _normalize_host(host: str) -> str:
    host = (host or "").strip()
    if host.startswith("https://"):
        host = host[len("https://") :]
    elif host.startswith("http://"):
        host = host[len("http://") :]
    return host.rstrip("/")


def _get_oauth_token() -> str:
    """Obtain an OAuth token from SDK Config (service principal M2M)."""
    try:
        cfg = Config()
    except Exception:
        cfg = Config(host=DATABRICKS_HOST)
    headers = cfg.authenticate()
    return headers.get("Authorization", "").replace("Bearer ", "").strip()


def _open_connection():
    """Create a fresh SQL connection."""
    hostname = _normalize_host(DATABRICKS_HOST)

    token = DATABRICKS_TOKEN or _get_oauth_token()
    if not token:
        raise RuntimeError("No Databricks token available (PAT or OAuth).")

    _log.info("Connecting to %s with %s auth",
              hostname, "PAT" if DATABRICKS_TOKEN else "OAuth/SP")
    return sql.connect(
        server_hostname=hostname,
        http_path=DATABRICKS_HTTP_PATH,
        access_token=token,
    )


def _coerce_numerics(df: pd.DataFrame) -> pd.DataFrame:
    """SQL connector may return numerics as strings — force coercion."""
    for col in df.columns:
        if df[col].dtype == object:
            try:
                df[col] = pd.to_numeric(df[col], errors="ignore")
            except Exception:
                pass
    return df


def _execute(query: str) -> pd.DataFrame:
    """Open a connection, run one query, close it. Avoids stale connection issues."""
    conn = _open_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query)
            return _coerce_numerics(cursor.fetchall_arrow().to_pandas())
    finally:
        try:
            conn.close()
        except Exception:
            pass


def run_query(query: str, mock_key: str | None = None) -> pd.DataFrame:
    """Execute a SQL query and return a pandas DataFrame.

    Falls back to mock data on failure or when USE_MOCK_DATA is set.
    """
    if USE_MOCK_DATA:
        return _mock_fallback(mock_key)

    try:
        return _execute(query)
    except Exception as exc:
        _log.warning("Live query failed: %s", exc, exc_info=True)
        st.warning(f"Live query failed — showing mock data. ({exc})")
        return _mock_fallback(mock_key)


def _mock_fallback(key: str | None) -> pd.DataFrame:
    if key and key in MOCK_REGISTRY:
        return MOCK_REGISTRY[key]()
    return pd.DataFrame()


def fq(table: str) -> str:
    """Return fully-qualified table name using configured catalog/schema."""
    return f"{DATABRICKS_CATALOG}.{DATABRICKS_SCHEMA}.{table}"
