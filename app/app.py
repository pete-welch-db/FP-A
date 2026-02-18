"""
Milacron FP&A Analytics — Application Entry Point
Routing only: delegates to view modules via st.navigation.
"""
import streamlit as st

st.set_page_config(
    page_title="Milacron FP&A",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

from views.01_executive_summary import render as exec_summary
from views.02_revenue_deep_dive import render as revenue_dive
from views.03_profitability import render as profitability
from views.04_cash_and_leverage import render as cash_leverage
from views.05_aftermarket import render as aftermarket
from views.06_ml_forecast import render as ml_forecast
from views.07_genie_assistant import render as genie_assistant

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
