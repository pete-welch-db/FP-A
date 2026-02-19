"""
Milacron FP&A Analytics — Application Entry Point
Routing only: delegates to view modules via st.navigation.
"""
import streamlit as st
from importlib import import_module

st.set_page_config(
    page_title="Milacron FP&A",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

def _load_render(module_name: str):
    return import_module(module_name).render


exec_summary = _load_render("views.01_executive_summary")
revenue_dive = _load_render("views.02_revenue_deep_dive")
profitability = _load_render("views.03_profitability")
cash_leverage = _load_render("views.04_cash_and_leverage")
aftermarket = _load_render("views.05_aftermarket")
ml_forecast = _load_render("views.06_ml_forecast")
genie_assistant = _load_render("views.07_genie_assistant")

PAGES = {
    "Executive Summary": exec_summary,
    "Revenue Deep Dive": revenue_dive,
    "Profitability": profitability,
    "Cash & Leverage": cash_leverage,
    "Aftermarket & Service": aftermarket,
    "ML Forecast": ml_forecast,
    "Genie Assistant": genie_assistant,
}

page = st.navigation([st.Page(fn, title=title) for title, fn in PAGES.items()])
page.run()
