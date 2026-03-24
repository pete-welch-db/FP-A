"""
Nova Molding Systems FP&A — Executive Summary
Embedded AI/BI dashboard view.
"""
import streamlit as st
import streamlit.components.v1 as components
from urllib.parse import parse_qsl, urlencode, urlparse

from config import DATABRICKS_HOST, DASHBOARD_EMBED_URL, DASHBOARD_EMBED_URL_V2, get_brand


def _normalize_dashboard_url(raw_value: str) -> str:
    value = (raw_value or "").strip()
    if not value:
        return ""

    if not value.startswith("http://") and not value.startswith("https://"):
        host = DATABRICKS_HOST.rstrip("/")
        if host:
            return f"{host}/embed/dashboardsv3/{value}"
        return value

    parsed = urlparse(value)
    base = f"{parsed.scheme}://{parsed.netloc}"
    path = parsed.path or ""

    if "/embed/dashboardsv3/" in path:
        return value

    if "/dashboardsv3/" in path:
        tail = path.split("/dashboardsv3/", 1)[1].strip("/")
        dashboard_id = tail.split("/", 1)[0]
        if dashboard_id:
            query_pairs = dict(parse_qsl(parsed.query, keep_blank_values=True))
            allowed_query = {}
            if "o" in query_pairs:
                allowed_query["o"] = query_pairs["o"]
            query = f"?{urlencode(allowed_query)}" if allowed_query else ""
            return f"{base}/embed/dashboardsv3/{dashboard_id}{query}"

    return value


def render():
    brand = get_brand()
    st.title("Executive Summary")
    st.caption(brand["dashboard_subtitle"])

    embed_url = _normalize_dashboard_url(brand["dashboard_embed_url"])
    if not embed_url:
        st.warning(
            "Dashboard embed URL is not configured. "
            "Set DASHBOARD_EMBED_URL (or DASHBOARD_EMBED_URL_V2) in your local .env."
        )
        return

    components.iframe(src=embed_url, height=900, scrolling=True)
