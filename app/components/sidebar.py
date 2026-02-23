"""
Nova Molding Systems FP&A — Global Sidebar Filters
Provides consistent filter controls across all app pages.
"""
import streamlit as st
from pathlib import Path


_ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"
_DATABRICKS_LOGO = _ASSETS_DIR / "Databricks_Logo.png"


def render_sidebar() -> dict:
    """Render sidebar filters and return the selected values as a dict."""
    with st.sidebar:
        st.image(str(_DATABRICKS_LOGO), width=240)
        st.markdown("&nbsp;")
        st.markdown("---")
        st.subheader("Filters")

        business_unit = st.multiselect(
            "Business Unit",
            options=["Injection Molding", "Extrusion", "Hot Runners", "Aftermarket & Service"],
            default=["Injection Molding", "Extrusion", "Hot Runners", "Aftermarket & Service"],
            key="filter_bu",
        )

        region = st.multiselect(
            "Region",
            options=["Americas", "Europe", "Asia", "India"],
            default=["Americas", "Europe", "Asia", "India"],
            key="filter_region",
        )

        scenario = st.selectbox(
            "Scenario",
            options=["Actual", "Budget", "Forecast", "Upside", "Downside"],
            index=0,
            key="filter_scenario",
        )

        fiscal_year = st.selectbox(
            "Fiscal Year",
            options=[2025, 2024],
            index=0,
            key="filter_fy",
        )

        st.markdown("---")
        st.caption("Nova Molding Systems FP&A Demo — Powered by Databricks")

    return {
        "business_unit": business_unit,
        "region": region,
        "scenario": scenario,
        "fiscal_year": fiscal_year,
    }


def sql_in_list(values: list[str]) -> str:
    """Convert a Python list to a SQL IN clause value string."""
    return ", ".join(f"'{v}'" for v in values)
