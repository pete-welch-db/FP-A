"""
Nova Molding Systems FP&A — Global Filters
Provides consistent filter controls across all app pages.
"""
import streamlit as st


_BU_OPTIONS = ["Injection Molding", "Extrusion", "Hot Runners", "Aftermarket & Service"]
_REGION_OPTIONS = ["Americas", "Europe", "Asia", "India"]
_SCENARIO_OPTIONS = ["Actual", "Budget", "Forecast", "Upside", "Downside"]
_FY_OPTIONS = [2026, 2025, 2024, 2023]


def render_filters() -> dict:
    """Render filters inline at the top of the page and return selected values."""
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        business_unit = st.multiselect(
            "Business Unit",
            options=_BU_OPTIONS,
            default=_BU_OPTIONS,
            key="filter_bu",
        )
    with c2:
        region = st.multiselect(
            "Region",
            options=_REGION_OPTIONS,
            default=_REGION_OPTIONS,
            key="filter_region",
        )
    with c3:
        scenario = st.selectbox(
            "Scenario",
            options=_SCENARIO_OPTIONS,
            index=0,
            key="filter_scenario",
        )
    with c4:
        fiscal_year = st.selectbox(
            "Fiscal Year",
            options=_FY_OPTIONS,
            index=0,
            key="filter_fy",
        )
    st.markdown("---")

    return {
        "business_unit": business_unit,
        "region": region,
        "scenario": scenario,
        "fiscal_year": fiscal_year,
    }


def render_sidebar() -> dict:
    """Legacy sidebar filter rendering — delegates to render_filters()."""
    return render_filters()


def sql_in_list(values: list[str]) -> str:
    """Convert a Python list to a SQL IN clause value string."""
    return ", ".join(f"'{v}'" for v in values)
