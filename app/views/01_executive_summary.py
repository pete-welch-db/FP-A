"""
Milacron FP&A — Executive Summary
CFO-level pulse: "How are we doing this quarter vs plan?"
"""
import streamlit as st
import plotly.express as px

from components.sidebar import render_sidebar, sql_in_list
from components.data_loader import run_query, fq
from components.kpi_cards import render_kpi_card, fmt_currency, fmt_pct


def render():
    st.title("Executive Summary")
    st.caption("Consolidated performance snapshot across Milacron's global operations")

    filters = render_sidebar()
    bu_filter = sql_in_list(filters["business_unit"])
    region_filter = sql_in_list(filters["region"])
    fy = filters["fiscal_year"]
    scenario = filters["scenario"]

    # --- Revenue ---
    rev_df = run_query(f"""
        SELECT fiscal_month, SUM(revenue_usd) AS revenue
        FROM {fq('gold_revenue_summary')}
        WHERE business_unit IN ({bu_filter})
          AND region IN ({region_filter})
          AND fiscal_year = {fy}
          AND scenario_name = '{scenario}'
        GROUP BY fiscal_month ORDER BY fiscal_month
    """, mock_key="revenue_summary")

    # --- EBITDA ---
    ebitda_df = run_query(f"""
        SELECT fiscal_quarter,
               SUM(revenue) AS revenue, SUM(ebitda) AS ebitda,
               AVG(ebitda_margin) AS ebitda_margin
        FROM {fq('gold_ebitda_bridge')}
        WHERE business_unit IN ({bu_filter})
          AND region IN ({region_filter})
          AND fiscal_year = {fy}
          AND scenario_name = '{scenario}'
        GROUP BY fiscal_quarter ORDER BY fiscal_quarter
    """, mock_key="ebitda_bridge")

    # --- Leverage ---
    lev_df = run_query(f"""
        SELECT fiscal_quarter, AVG(net_leverage) AS net_leverage
        FROM {fq('gold_leverage_metrics')}
        WHERE fiscal_year = {fy}
        GROUP BY fiscal_quarter ORDER BY fiscal_quarter
    """, mock_key="leverage")

    # --- Working Capital ---
    wc_df = run_query(f"""
        SELECT AVG(dso) AS dso, AVG(dpo) AS dpo, AVG(inventory_turns) AS inv_turns
        FROM {fq('gold_working_capital')}
        WHERE business_unit IN ({bu_filter})
          AND region IN ({region_filter})
          AND fiscal_year = {fy}
    """, mock_key="working_capital")

    # --- Aftermarket Mix ---
    am_df = run_query(f"""
        SELECT AVG(aftermarket_mix_pct) AS am_mix, AVG(service_attach_rate) AS attach
        FROM {fq('gold_aftermarket_mix')}
        WHERE business_unit IN ({bu_filter})
          AND region IN ({region_filter})
          AND fiscal_year = {fy}
    """, mock_key="aftermarket")

    # --- FCF ---
    fcf_df = run_query(f"""
        SELECT SUM(fcf) AS fcf, AVG(fcf_conversion_pct) AS fcf_conv
        FROM {fq('gold_cash_flow_summary')}
        WHERE fiscal_year = {fy}
    """, mock_key="cash_flow")

    # ---- KPI Cards Row ----
    c1, c2, c3, c4, c5, c6 = st.columns(6)

    total_rev = rev_df["revenue"].sum() if not rev_df.empty else 0
    with c1:
        render_kpi_card(
            "Revenue", fmt_currency(total_rev),
            sparkline_data=rev_df["revenue"].tolist() if not rev_df.empty else None,
        )

    ebitda_margin = ebitda_df["ebitda_margin"].mean() * 100 if not ebitda_df.empty else 0
    with c2:
        render_kpi_card("EBITDA Margin", fmt_pct(ebitda_margin))

    fcf_val = fcf_df["fcf"].iloc[0] if not fcf_df.empty else 0
    with c3:
        render_kpi_card("Free Cash Flow", fmt_currency(fcf_val))

    net_lev = lev_df["net_leverage"].iloc[-1] if not lev_df.empty else 0
    with c4:
        render_kpi_card(
            "Net Leverage",
            f"{net_lev:.1f}x",
            delta_color="inverse" if net_lev > 4.0 else "normal",
        )

    dso_val = wc_df["dso"].iloc[0] if not wc_df.empty else 0
    with c5:
        render_kpi_card("DSO", f"{dso_val:.0f} days")

    am_mix = am_df["am_mix"].iloc[0] if not am_df.empty else 0
    with c6:
        render_kpi_card("Aftermarket Mix", fmt_pct(am_mix))

    # ---- Charts ----
    st.markdown("---")
    col_left, col_right = st.columns(2)

    with col_left:
        if not rev_df.empty:
            fig = px.bar(
                rev_df, x="fiscal_month", y="revenue",
                title="Monthly Revenue Trend",
                labels={"fiscal_month": "Month", "revenue": "Revenue (USD)"},
                color_discrete_sequence=["#FF3621"],
            )
            fig.update_layout(template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)

    with col_right:
        if not ebitda_df.empty:
            fig = px.line(
                ebitda_df, x="fiscal_quarter", y="ebitda_margin",
                title="Quarterly EBITDA Margin",
                labels={"fiscal_quarter": "Quarter", "ebitda_margin": "Margin"},
                markers=True,
                color_discrete_sequence=["#1565C0"],
            )
            fig.update_layout(template="plotly_white", yaxis_tickformat=".1%")
            st.plotly_chart(fig, use_container_width=True)

    # ---- Leverage Trend ----
    if not lev_df.empty:
        fig = px.line(
            lev_df, x="fiscal_quarter", y="net_leverage",
            title="Net Leverage Trend",
            markers=True, color_discrete_sequence=["#FF6F00"],
        )
        fig.add_hline(y=4.0, line_dash="dash", line_color="red", annotation_text="Guardrail (4.0x)")
        fig.update_layout(template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)
