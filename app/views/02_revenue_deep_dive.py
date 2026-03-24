"""
Nova Molding Systems FP&A — Revenue Deep Dive
Drill into revenue by BU, region, end-market, and scenario.
"""
import streamlit as st
import plotly.express as px

from components.sidebar import render_filters, sql_in_list
from components.data_loader import run_query, fq


def render():
    st.title("Revenue Deep Dive")
    st.caption("Analyse revenue performance across business units, regions, and end-markets")

    filters = render_filters()
    bu_filter = sql_in_list(filters["business_unit"])
    region_filter = sql_in_list(filters["region"])
    fy = filters["fiscal_year"]

    # Revenue by BU × Region — stacked bar
    rev_bu = run_query(f"""
        SELECT business_unit, region, SUM(revenue_usd) AS revenue
        FROM {fq('gold_revenue_summary')}
        WHERE business_unit IN ({bu_filter})
          AND region IN ({region_filter})
          AND fiscal_year = {fy}
          AND scenario_name = 'Actual'
        GROUP BY business_unit, region
        ORDER BY revenue DESC
    """, mock_key="revenue_summary")

    if not rev_bu.empty and "revenue" in rev_bu.columns:
        fig = px.bar(
            rev_bu, x="business_unit", y="revenue", color="region",
            title="Revenue by Business Unit & Region",
            barmode="stack",
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig.update_layout(template="plotly_white", yaxis_title="Revenue (USD)")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Quarterly revenue trend by BU — line chart
    st.subheader("Quarterly Revenue Trend by Business Unit")
    trend_df = run_query(f"""
        SELECT business_unit, fiscal_quarter, SUM(revenue_usd) AS revenue
        FROM {fq('gold_revenue_summary')}
        WHERE business_unit IN ({bu_filter})
          AND region IN ({region_filter})
          AND fiscal_year = {fy}
          AND scenario_name = 'Actual'
        GROUP BY business_unit, fiscal_quarter
        ORDER BY fiscal_quarter
    """, mock_key="revenue_summary")

    if not trend_df.empty and "revenue" in trend_df.columns:
        fig = px.line(
            trend_df, x="fiscal_quarter", y="revenue", color="business_unit",
            markers=True, title="Revenue by Quarter",
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig.update_layout(template="plotly_white", yaxis_title="Revenue (USD)")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # YoY Growth Heatmap
    st.subheader("Year-over-Year Growth by BU & Quarter")
    yoy_df = run_query(f"""
        SELECT business_unit, fiscal_quarter, AVG(yoy_growth_pct) AS yoy_growth_pct
        FROM {fq('gold_revenue_summary')}
        WHERE business_unit IN ({bu_filter})
          AND region IN ({region_filter})
          AND fiscal_year = {fy}
          AND scenario_name = 'Actual'
        GROUP BY business_unit, fiscal_quarter
    """, mock_key="revenue_summary")

    if not yoy_df.empty and "yoy_growth_pct" in yoy_df.columns:
        pivot = yoy_df.pivot_table(index="business_unit", columns="fiscal_quarter", values="yoy_growth_pct", aggfunc="mean")
        fig = px.imshow(
            pivot, text_auto=".1f", aspect="auto",
            title="YoY Revenue Growth (%)",
            color_continuous_scale="RdYlGn", zmin=-5, zmax=25,
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Scenario Comparison
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Scenario Comparison")
        scenario_df = run_query(f"""
            SELECT scenario_name, fiscal_quarter, SUM(revenue_usd) AS revenue
            FROM {fq('gold_revenue_summary')}
            WHERE business_unit IN ({bu_filter})
              AND region IN ({region_filter})
              AND fiscal_year = {fy}
              AND scenario_name IN ('Actual', 'Budget', 'Forecast')
            GROUP BY scenario_name, fiscal_quarter
            ORDER BY fiscal_quarter
        """, mock_key="revenue_summary")

        if not scenario_df.empty:
            fig = px.line(
                scenario_df, x="fiscal_quarter", y="revenue", color="scenario_name",
                markers=True, title="Quarterly Revenue by Scenario",
                color_discrete_map={"Actual": "#2E7D32", "Budget": "#1565C0", "Forecast": "#FF6F00"},
            )
            fig.update_layout(template="plotly_white", yaxis_title="Revenue (USD)")
            st.plotly_chart(fig, use_container_width=True)

    # Budget Variance
    with col2:
        st.subheader("Budget Variance by BU")
        var_df = run_query(f"""
            SELECT business_unit, AVG(budget_variance_pct) AS budget_variance_pct
            FROM {fq('gold_revenue_summary')}
            WHERE business_unit IN ({bu_filter})
              AND region IN ({region_filter})
              AND fiscal_year = {fy}
              AND scenario_name = 'Actual'
            GROUP BY business_unit
            ORDER BY budget_variance_pct
        """, mock_key="revenue_summary")

        if not var_df.empty and "budget_variance_pct" in var_df.columns:
            fig = px.bar(
                var_df, x="business_unit", y="budget_variance_pct",
                title="Avg Budget Variance (%)",
                color="budget_variance_pct",
                color_continuous_scale="RdYlGn", color_continuous_midpoint=0,
            )
            fig.update_layout(template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)
