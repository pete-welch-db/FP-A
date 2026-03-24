"""
Nova Molding Systems FP&A Analytics — Application Entry Point
Routing only: delegates to view modules via st.navigation.
"""
import streamlit as st
from importlib import import_module
from pathlib import Path

from config import BRAND_CONFIG

_ASSETS_DIR = Path(__file__).resolve().parent / "assets"
_DATABRICKS_LOGO = _ASSETS_DIR / "Databricks_Logo.png"
_MILACRON_LOGO = _ASSETS_DIR / "Milacron_Logo.png"

_brand_name = st.session_state.get("brand", "Nova Molding Systems")
_page_title = BRAND_CONFIG.get(_brand_name, BRAND_CONFIG["Nova Molding Systems"])["page_title"]

st.set_page_config(
    page_title=_page_title,
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

_sidebar_logo = _MILACRON_LOGO if _brand_name == "Milacron" and _MILACRON_LOGO.exists() else _DATABRICKS_LOGO
with st.sidebar:
    try:
        st.image(str(_sidebar_logo), use_container_width=True)
    except TypeError:
        st.image(str(_sidebar_logo))

st.markdown(
    """
    <style>
    /* Minimize top padding on all pages */
    section.main > div.block-container {
        padding-top: 1rem !important;
    }
    /* Stretch nav to fill sidebar so Settings can pin to bottom */
    [data-testid="stSidebarNav"] {
        position: relative;
        min-height: calc(100vh - 160px);
    }
    [data-testid="stSidebarNav"] li:last-child {
        position: absolute;
        bottom: 0;
        width: 100%;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def _load_render(module_name: str):
    module = import_module(module_name)
    if hasattr(module, "render"):
        return module.render
    if hasattr(module, "render_landing_page"):
        return module.render_landing_page
    raise AttributeError(f"{module_name} must expose render()")


landing = _load_render("views.00_lightweight_landing")
exec_summary = _load_render("views.01_executive_summary")
revenue_dive = _load_render("views.02_revenue_deep_dive")
profitability = _load_render("views.03_profitability")
cash_leverage = _load_render("views.04_cash_and_leverage")
aftermarket = _load_render("views.05_aftermarket")
ml_forecast = _load_render("views.06_ml_forecast")
genie_research = _load_render("views.02_lightweight_genie")
ref_arch = _load_render("views.08_reference_architecture")
settings = _load_render("views.09_settings")

FULL_PAGES = [
    ("Landing", landing, "landing"),
    ("Executive Summary", exec_summary, "executive-summary"),
    ("Revenue Deep Dive", revenue_dive, "revenue-deep-dive"),
    ("Profitability", profitability, "profitability"),
    ("Cash & Leverage", cash_leverage, "cash-and-leverage"),
    ("Aftermarket & Service", aftermarket, "aftermarket-and-service"),
    ("ML Forecast", ml_forecast, "ml-forecast"),
    ("Genie + Research Agent", genie_research, "genie-research-agent"),
    ("Reference Architecture", ref_arch, "reference-architecture"),
]

LITE_PAGES = [
    ("Landing", landing, "landing"),
    ("Executive Summary", exec_summary, "executive-summary"),
    ("Genie + Research Agent", genie_research, "genie-research-agent"),
    ("Reference Architecture", ref_arch, "reference-architecture"),
]

active_pages = LITE_PAGES if st.session_state.get("confirmed_app_mode") == "Lightweight" else FULL_PAGES

settings_page = st.Page(settings, title="Settings", url_path="settings", icon=":material/settings:")

page = st.navigation(
    [
        st.Page(fn, title=title, url_path=slug, default=(idx == 0))
        for idx, (title, fn, slug) in enumerate(active_pages)
    ]
    + [settings_page]
)

page.run()
