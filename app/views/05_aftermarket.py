"""
Nova Molding Systems FP&A — Aftermarket & Service
Growth engine: attach rate, renewal trends, IIoT opportunities.
"""
import streamlit as st
import plotly.express as px

from components.sidebar import render_filters, sql_in_list
from components.data_loader import run_query, fq
from components.kpi_cards import render_kpi_card, fmt_currency, fmt_pct


def render():
    st.title("Aftermarket & Service")
    st.caption("Track the aftermarket growth engine — attach rates, renewals, and IIoT-driven service opportunities")

    filters = render_filters()
    bu_filter = sql_in_list(filters["business_unit"])
    region_filter = sql_in_list(filters["region"])
    fy = filters["fiscal_year"]

    # --- Aftermarket Mix ---
    am_df = run_query(f"""
        SELECT business_unit, region, fiscal_quarter,
               SUM(aftermarket_revenue) AS am_rev,
               SUM(total_revenue) AS total_rev,
               AVG(aftermarket_mix_pct) AS am_mix,
               AVG(service_attach_rate) AS attach_rate
        FROM {fq('gold_aftermarket_mix')}
        WHERE business_unit IN ({bu_filter})
          AND region IN ({region_filter})
          AND fiscal_year = {fy}
        GROUP BY business_unit, region, fiscal_quarter
        ORDER BY fiscal_quarter
    """, mock_key="aftermarket")

    if not am_df.empty:
        # KPIs
        c1, c2, c3 = st.columns(3)
        with c1:
            render_kpi_card("Aftermarket Revenue", fmt_currency(am_df["am_rev"].sum()))
        with c2:
            render_kpi_card("Avg Aftermarket Mix", fmt_pct(am_df["am_mix"].mean()))
        with c3:
            render_kpi_card("Avg Service Attach Rate", fmt_pct(am_df["attach_rate"].mean() * 100))

        st.markdown("---")

        # Aftermarket mix by region
        col1, col2 = st.columns(2)
        with col1:
            region_mix = am_df.groupby("region").agg({"am_rev": "sum", "total_rev": "sum"}).reset_index()
            region_mix["mix_pct"] = region_mix["am_rev"] / region_mix["total_rev"] * 100
            fig = px.bar(
                region_mix, x="region", y="mix_pct",
                title="Aftermarket Mix by Region (%)",
                color="mix_pct", color_continuous_scale="YlOrRd",
            )
            fig.add_hline(y=30, line_dash="dash", line_color="green",
                          annotation_text="Target (30%)")
            fig.update_layout(template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = px.line(
                am_df.groupby("fiscal_quarter").agg({"am_mix": "mean"}).reset_index(),
                x="fiscal_quarter", y="am_mix",
                title="Aftermarket Mix Trend",
                markers=True, color_discrete_sequence=["#FF3621"],
            )
            fig.update_layout(template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)

        # Service attach rate by BU
        st.subheader("Service Attach Rate by Business Unit")
        attach_by_bu = am_df.groupby("business_unit").agg({"attach_rate": "mean"}).reset_index()
        fig = px.bar(
            attach_by_bu, x="business_unit", y="attach_rate",
            title="Avg Service Attach Rate",
            color_discrete_sequence=["#1565C0"],
        )
        fig.update_layout(template="plotly_white", yaxis_tickformat=".0%")
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("No aftermarket data available for the selected filters.")

    # --- Order Backlog / Book-to-Bill ---
    st.markdown("---")
    st.subheader("Order Backlog & Book-to-Bill")
    backlog_df = run_query(f"""
        SELECT business_unit, fiscal_month,
               SUM(order_intake) AS intake,
               SUM(backlog_value) AS backlog,
               AVG(book_to_bill_ratio) AS btb
        FROM {fq('gold_order_backlog')}
        WHERE business_unit IN ({bu_filter})
          AND region IN ({region_filter})
          AND fiscal_year = {fy}
        GROUP BY business_unit, fiscal_month
        ORDER BY fiscal_month
    """, mock_key="order_backlog")

    if not backlog_df.empty:
        fig = px.line(
            backlog_df, x="fiscal_month", y="btb", color="business_unit",
            title="Book-to-Bill Ratio by BU",
            markers=True,
        )
        fig.add_hline(y=1.0, line_dash="dash", line_color="gray", annotation_text="Parity (1.0)")
        fig.update_layout(template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)
