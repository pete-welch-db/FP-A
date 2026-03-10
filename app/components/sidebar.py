"""
Nova Molding Systems FP&A — Global Filters
Provides consistent filter controls across all app pages.
Filter selections persist across page navigation via session_state.
"""
import streamlit as st


_BU_OPTIONS = ["Injection Molding", "Extrusion", "Hot Runners", "Aftermarket & Service"]
_REGION_OPTIONS = ["Americas", "Europe", "Asia", "India"]
_SCENARIO_OPTIONS = ["Actual", "Budget", "Forecast", "Upside", "Downside"]
_FY_OPTIONS = [2026, 2025, 2024, 2023]

_PERSIST_DEFAULTS = {
    "persist_bu": list(_BU_OPTIONS),
    "persist_region": list(_REGION_OPTIONS),
    "persist_scenario": "Actual",
    "persist_fy": 2026,
}


def _init_persistent_filters():
    for key, default in _PERSIST_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = default


def _sync(persist_key: str, widget_key: str):
    """Copy the widget value into the persistent key on change."""
    st.session_state[persist_key] = st.session_state[widget_key]


def render_filters() -> dict:
    """Render filters inline at the top of the page and return selected values."""
    _init_persistent_filters()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        business_unit = st.multiselect(
            "Business Unit",
            options=_BU_OPTIONS,
            default=st.session_state["persist_bu"],
            key="filter_bu",
            on_change=_sync,
            args=("persist_bu", "filter_bu"),
        )
    with c2:
        region = st.multiselect(
            "Region",
            options=_REGION_OPTIONS,
            default=st.session_state["persist_region"],
            key="filter_region",
            on_change=_sync,
            args=("persist_region", "filter_region"),
        )
    with c3:
        scenario = st.selectbox(
            "Scenario",
            options=_SCENARIO_OPTIONS,
            index=_SCENARIO_OPTIONS.index(st.session_state["persist_scenario"]),
            key="filter_scenario",
            on_change=_sync,
            args=("persist_scenario", "filter_scenario"),
        )
    with c4:
        fiscal_year = st.selectbox(
            "Fiscal Year",
            options=_FY_OPTIONS,
            index=_FY_OPTIONS.index(st.session_state["persist_fy"]),
            key="filter_fy",
            on_change=_sync,
            args=("persist_fy", "filter_fy"),
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
