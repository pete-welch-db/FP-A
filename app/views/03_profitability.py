"""
Nova Molding Systems FP&A — Profitability (EBITDA Bridge)
Explain margin walk: revenue → COGS → gross profit → OpEx → EBITDA.
"""
import streamlit as st
import plotly.express as px

from components.sidebar import render_filters, sql_in_list
from components.data_loader import run_query, fq
from components.ebitda_bridge import render_ebitda_waterfall
from components.kpi_cards import fmt_currency, fmt_pct


def render():
    st.title("Profitability — EBITDA Bridge")
    st.caption("Decompose margin performance across business units and regions")

    filters = render_filters()
    bu_filter = sql_in_list(filters["business_unit"])
    region_filter = sql_in_list(filters["region"])
    fy = filters["fiscal_year"]
    scenario = filters["scenario"]

    # Consolidated EBITDA bridge
    bridge_df = run_query(f"""
        SELECT SUM(revenue) AS revenue, SUM(cogs) AS cogs,
               SUM(opex) AS opex, SUM(gross_profit) AS gross_profit,
               SUM(ebitda) AS ebitda
        FROM {fq('gold_ebitda_bridge')}
        WHERE business_unit IN ({bu_filter})
          AND region IN ({region_filter})
          AND fiscal_year = {fy}
          AND scenario_name = '{scenario}'
    """, mock_key="ebitda_bridge")

    if not bridge_df.empty and bridge_df["revenue"].iloc[0]:
        row = bridge_df.iloc[0]
        render_ebitda_waterfall(
            revenue=float(row["revenue"]),
            cogs=float(row["cogs"]),
            opex=float(row["opex"]),
            title=f"EBITDA Bridge — FY{fy} {scenario}",
        )
    else:
        st.info("No profitability data available for the selected filters.")

    st.markdown("---")

    # Margin trend by BU and quarter — line chart
    st.subheader("EBITDA Margin Trend by Quarter")
    margin_df = run_query(f"""
        SELECT business_unit, fiscal_quarter,
               SUM(ebitda) / NULLIF(SUM(revenue), 0) AS ebitda_margin
        FROM {fq('gold_ebitda_bridge')}
        WHERE business_unit IN ({bu_filter})
          AND region IN ({region_filter})
          AND fiscal_year = {fy}
          AND scenario_name = '{scenario}'
        GROUP BY business_unit, fiscal_quarter ORDER BY fiscal_quarter
    """, mock_key="ebitda_bridge")

    if not margin_df.empty and "ebitda_margin" in margin_df.columns:
        fig = px.line(
            margin_df, x="fiscal_quarter", y="ebitda_margin", color="business_unit",
            markers=True, title="Quarterly EBITDA Margin by BU",
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig.update_layout(template="plotly_white", yaxis_tickformat=".1%",
                          yaxis_title="EBITDA Margin")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # BU comparison — side-by-side
    st.subheader("EBITDA by Business Unit")
    bu_df = run_query(f"""
        SELECT business_unit,
               SUM(revenue) AS revenue, SUM(ebitda) AS ebitda,
               SUM(ebitda) / NULLIF(SUM(revenue), 0) AS ebitda_margin
        FROM {fq('gold_ebitda_bridge')}
        WHERE business_unit IN ({bu_filter})
          AND region IN ({region_filter})
          AND fiscal_year = {fy}
          AND scenario_name = '{scenario}'
        GROUP BY business_unit ORDER BY ebitda DESC
    """, mock_key="ebitda_bridge")

    if not bu_df.empty:
        col1, col2 = st.columns(2)
        with col1:
            fig = px.bar(
                bu_df, x="business_unit", y="ebitda",
                title="EBITDA by BU", color="business_unit",
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig.update_layout(template="plotly_white", yaxis_title="EBITDA (USD)",
                              showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        if "ebitda_margin" in bu_df.columns:
            with col2:
                fig = px.bar(
                    bu_df, x="business_unit", y="ebitda_margin",
                    title="EBITDA Margin by BU", color="business_unit",
                    color_discrete_sequence=px.colors.qualitative.Set2,
                )
                fig.update_layout(template="plotly_white", yaxis_tickformat=".1%",
                                  yaxis_title="EBITDA Margin", showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
