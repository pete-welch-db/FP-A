"""
Milacron FP&A — Data Loader
Centralised SQL execution with connection pooling, caching, numeric
coercion, and graceful fallback to mock data.
"""
import streamlit as st
import pandas as pd
from databricks import sql
from databricks.sdk.core import Config

from config import (
    DATABRICKS_HOST,
    DATABRICKS_HTTP_PATH,
    USE_MOCK_DATA,
    DATABRICKS_CATALOG,
    DATABRICKS_SCHEMA,
)
from data.mock_data import MOCK_REGISTRY


@st.cache_resource(ttl=300, show_spinner=False)
def _get_connection():
    cfg = Config()
    return sql.connect(
        server_hostname=cfg.host or DATABRICKS_HOST,
        http_path=DATABRICKS_HTTP_PATH,
        credentials_provider=lambda: cfg.authenticate,
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


def run_query(query: str, mock_key: str | None = None) -> pd.DataFrame:
    """Execute a SQL query and return a pandas DataFrame.

    Falls back to mock data on failure or when USE_MOCK_DATA is set.
    """
    if USE_MOCK_DATA:
        return _mock_fallback(mock_key)

    try:
        conn = _get_connection()
        with conn.cursor() as cursor:
            cursor.execute(query)
            result = cursor.fetchall_arrow().to_pandas()
        return _coerce_numerics(result)
    except Exception as exc:
        st.warning(f"Live query failed — showing mock data. ({exc})")
        return _mock_fallback(mock_key)


def _mock_fallback(key: str | None) -> pd.DataFrame:
    if key and key in MOCK_REGISTRY:
        return MOCK_REGISTRY[key]()
    return pd.DataFrame()


def fq(table: str) -> str:
    """Return fully-qualified table name using configured catalog/schema."""
    return f"{DATABRICKS_CATALOG}.{DATABRICKS_SCHEMA}.{table}"
