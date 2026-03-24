"""
Nova Molding Systems FP&A — Cash & Leverage
Treasury view: FCF generation, debt trajectory, working capital efficiency.
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from components.sidebar import render_filters, sql_in_list
from components.data_loader import run_query, fq
from components.kpi_cards import render_kpi_card, fmt_currency, fmt_pct


def render():
    st.title("Cash & Leverage")
    st.caption("Free cash flow generation, balance sheet health, and working capital efficiency")

    filters = render_filters()
    bu_filter = sql_in_list(filters["business_unit"])
    region_filter = sql_in_list(filters["region"])
    fy = filters["fiscal_year"]

    # --- FCF Summary ---
    fcf_df = run_query(f"""
        SELECT fiscal_quarter,
               SUM(operating_cf) AS operating_cf,
               SUM(capex) AS capex,
               SUM(fcf) AS fcf,
               AVG(fcf_conversion_pct) AS fcf_conversion_pct
        FROM {fq('gold_cash_flow_summary')}
        WHERE fiscal_year = {fy}
        GROUP BY fiscal_quarter ORDER BY fiscal_quarter
    """, mock_key="cash_flow")

    if not fcf_df.empty:
        # KPI cards
        c1, c2, c3 = st.columns(3)
        with c1:
            render_kpi_card("Operating Cash Flow", fmt_currency(fcf_df["operating_cf"].sum()))
        with c2:
            render_kpi_card("CapEx", fmt_currency(abs(fcf_df["capex"].sum())))
        with c3:
            render_kpi_card("Free Cash Flow", fmt_currency(fcf_df["fcf"].sum()))

        # FCF waterfall
        fig = go.Figure(go.Waterfall(
            x=fcf_df["fiscal_quarter"],
            y=fcf_df["fcf"],
            text=[fmt_currency(v) for v in fcf_df["fcf"]],
            textposition="outside",
            connector={"line": {"color": "rgb(63, 63, 63)"}},
        ))
        fig.update_layout(title="Quarterly Free Cash Flow", template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # --- Leverage Trend ---
    st.subheader("Net Leverage Trend")
    lev_df = run_query(f"""
        SELECT fiscal_quarter, AVG(net_leverage) AS net_leverage,
               AVG(interest_coverage) AS interest_coverage
        FROM {fq('gold_leverage_metrics')}
        WHERE fiscal_year = {fy}
        GROUP BY fiscal_quarter ORDER BY fiscal_quarter
    """, mock_key="leverage")

    if not lev_df.empty:
        col1, col2 = st.columns(2)
        with col1:
            fig = px.line(
                lev_df, x="fiscal_quarter", y="net_leverage",
                title="Net Leverage (Net Debt / EBITDA)",
                markers=True, color_discrete_sequence=["#C62828"],
            )
            fig.add_hline(y=4.0, line_dash="dash", line_color="red",
                          annotation_text="Guardrail (4.0x)")
            fig.update_layout(template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig = px.line(
                lev_df, x="fiscal_quarter", y="interest_coverage",
                title="Interest Coverage Ratio",
                markers=True, color_discrete_sequence=["#2E7D32"],
            )
            fig.add_hline(y=3.0, line_dash="dash", line_color="orange",
                          annotation_text="Min Coverage (3.0x)")
            fig.update_layout(template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # --- Working Capital Gauges ---
    st.subheader("Working Capital Efficiency")
    wc_df = run_query(f"""
        SELECT business_unit, region,
               AVG(dso) AS dso, AVG(dpo) AS dpo,
               AVG(inventory_turns) AS inventory_turns,
               AVG(cash_conversion_cycle) AS cash_conversion_cycle
        FROM {fq('gold_working_capital')}
        WHERE business_unit IN ({bu_filter})
          AND region IN ({region_filter})
          AND fiscal_year = {fy}
        GROUP BY business_unit, region
        ORDER BY dso DESC
    """, mock_key="working_capital")

    if not wc_df.empty:
        c1, c2, c3 = st.columns(3)
        with c1:
            render_kpi_card("Avg DSO", f"{wc_df['dso'].mean():.0f} days")
        with c2:
            render_kpi_card("Avg DPO", f"{wc_df['dpo'].mean():.0f} days")
        with c3:
            render_kpi_card("Avg Inventory Turns", f"{wc_df['inventory_turns'].mean():.1f}x")

        st.dataframe(
            wc_df.style.format({
                "dso": "{:.0f}", "dpo": "{:.0f}",
                "inventory_turns": "{:.1f}", "cash_conversion_cycle": "{:.0f}",
            }),
            use_container_width=True,
        )
