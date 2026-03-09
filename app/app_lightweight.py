"""
Nova Molding Systems FP&A Analytics — Lightweight Demo Entry Point
Focused 3-page flow for sub-5-minute executive walkthrough.
"""
import streamlit as st
from importlib import import_module
from pathlib import Path


st.set_page_config(
    page_title="Nova Molding Systems FP&A (Lightweight)",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

_ASSETS_DIR = Path(__file__).resolve().parent / "assets"
_DATABRICKS_LOGO = _ASSETS_DIR / "Databricks_Logo.png"

st.logo(str(_DATABRICKS_LOGO), size="large")

st.markdown(
    """
    <style>
    /* Minimize top padding on all pages */
    section.main > div.block-container {
        padding-top: 1rem !important;
    }
    /* Enlarge the sidebar logo */
    [data-testid="stLogo"] {
        height: auto !important;
        max-height: none !important;
        padding-bottom: 1rem;
    }
    [data-testid="stLogo"] img {
        max-height: 80px !important;
        width: auto !important;
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
dashboard = _load_render("views.01_executive_summary")
genie = _load_render("views.02_lightweight_genie")
ref_arch = _load_render("views.08_reference_architecture")
settings = _load_render("views.09_settings")

PAGES = [
    ("Landing", landing, "landing"),
    ("Executive Summary", dashboard, "executive-summary"),
    ("Genie + Research Agent", genie, "genie-research-agent"),
    ("Reference Architecture", ref_arch, "reference-architecture"),
]

settings_page = st.Page(settings, title="Settings", url_path="settings", icon=":material/settings:")

page = st.navigation(
    [
        st.Page(fn, title=title, url_path=slug, default=(idx == 0))
        for idx, (title, fn, slug) in enumerate(PAGES)
    ]
    + [settings_page]
)

page.run()
