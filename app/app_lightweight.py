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

with st.sidebar:
    st.image(str(_DATABRICKS_LOGO), width=240)
    st.markdown("---")


def _load_render(module_name: str):
    module = import_module(module_name)
    if hasattr(module, "render"):
        return module.render
    if hasattr(module, "render_landing_page"):
        return module.render_landing_page
    raise AttributeError(f"{module_name} must expose render()")


landing = _load_render("views.00_lightweight_landing")
dashboard = _load_render("views.01_lightweight_dashboard")
genie = _load_render("views.02_lightweight_genie")

PAGES = [
    ("Landing", landing, "landing"),
    ("Executive Dashboard", dashboard, "executive-dashboard"),
    ("Genie + Research Agent", genie, "genie-research-agent"),
]

page = st.navigation([
    st.Page(fn, title=title, url_path=slug, default=(idx == 0))
    for idx, (title, fn, slug) in enumerate(PAGES)
])
page.run()
