import streamlit as st


def render():
    """Render landing page and orientation content."""
    st.title("Nova Molding Systems FP&A on Databricks")
    st.caption("AI-driven planning, governed metrics, and real-time financial visibility")

    st.markdown(
        """
        ### Why this app
        Finance teams need one governed platform to unify data, speed planning cycles, and
        make higher-confidence decisions.
        """
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Data Prep Time", "↓ 60–70%")
    c2.metric("Forecast Refresh", "From weeks to hours")
    c3.metric("Trusted KPI Layer", "Single source of truth")

    st.markdown("---")
    st.subheader("What you can explore")
    st.markdown(
        """
        - **Executive Summary**: CFO-level KPI pulse by scenario, region, and business unit
        - **Revenue / Profitability / Cash**: driver-level drilldowns and trend analysis
        - **ML Forecast**: near-term prediction and variance context
        - **Genie Assistant**: natural language analytics on governed datasets
        """
    )

    st.info("Use the left navigation to move through each workflow page.")
