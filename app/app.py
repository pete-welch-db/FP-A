"""
Nova Molding Systems FP&A Analytics — Application Entry Point
Routing only: delegates to view modules via st.navigation.
"""
import streamlit as st
from importlib import import_module

st.set_page_config(
    page_title="Nova Molding Systems FP&A",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

def _load_render(module_name: str):
    module = import_module(module_name)
    if hasattr(module, "render"):
        return module.render
    if hasattr(module, "render_landing_page"):
        return module.render_landing_page
    raise AttributeError(f"{module_name} must expose render()")


landing = _load_render("views.00_Landing")
exec_summary = _load_render("views.01_executive_summary")
revenue_dive = _load_render("views.02_revenue_deep_dive")
profitability = _load_render("views.03_profitability")
cash_leverage = _load_render("views.04_cash_and_leverage")
aftermarket = _load_render("views.05_aftermarket")
ml_forecast = _load_render("views.06_ml_forecast")
genie_assistant = _load_render("views.07_genie_assistant")

PAGES = [
    ("Landing", landing, "landing"),
    ("Executive Summary", exec_summary, "executive-summary"),
    ("Revenue Deep Dive", revenue_dive, "revenue-deep-dive"),
    ("Profitability", profitability, "profitability"),
    ("Cash & Leverage", cash_leverage, "cash-and-leverage"),
    ("Aftermarket & Service", aftermarket, "aftermarket-and-service"),
    ("ML Forecast", ml_forecast, "ml-forecast"),
    ("Genie Assistant", genie_assistant, "genie-assistant"),
]

# Explicit URL paths avoid pathname collisions from shared callable names.
page = st.navigation([
    st.Page(fn, title=title, url_path=slug, default=(idx == 0))
    for idx, (title, fn, slug) in enumerate(PAGES)
])
page.run()
