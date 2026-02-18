"""
Milacron FP&A — ML Forecast
Data-driven 3-month revenue forecast with explainability.
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from components.sidebar import render_sidebar, sql_in_list
from components.data_loader import run_query, fq
from components.kpi_cards import render_kpi_card, fmt_currency


def render():
    st.title("ML Revenue Forecast")
    st.caption("LightGBM-powered 3-month forward revenue forecast with confidence intervals and SHAP explainability")

    filters = render_sidebar()
    bu_filter = sql_in_list(filters["business_unit"])
    region_filter = sql_in_list(filters["region"])

    # --- Forecast Data ---
    forecast_df = run_query(f"""
        SELECT f.entity_id, f.product_family, f.forecast_month,
               f.predicted_revenue, f.prediction_interval_lower,
               f.prediction_interval_upper,
               e.business_unit, e.region
        FROM {fq('ml_revenue_forecast')} f
        JOIN {fq('silver_dim_entity')} e ON f.entity_id = e.entity_id
        WHERE e.business_unit IN ({bu_filter})
          AND e.region IN ({region_filter})
    """, mock_key="ml_forecast")

    if forecast_df.empty:
        st.info("No forecast data available. Run the ML training pipeline first.")
        return

    # Aggregated forecast by month
    monthly = (
        forecast_df.groupby("forecast_month")
        .agg(
            predicted=("predicted_revenue", "sum"),
            lower=("prediction_interval_lower", "sum"),
            upper=("prediction_interval_upper", "sum"),
        )
        .reset_index()
        .sort_values("forecast_month")
    )

    # --- KPI Cards ---
    c1, c2, c3 = st.columns(3)
    for i, (_, row) in enumerate(monthly.iterrows()):
        with [c1, c2, c3][i]:
            render_kpi_card(
                row["forecast_month"],
                fmt_currency(row["predicted"]),
                delta=f"Range: {fmt_currency(row['lower'])} – {fmt_currency(row['upper'])}",
            )

    st.markdown("---")

    # --- Forecast with Confidence Bands ---
    st.subheader("Forecast with 95% Confidence Interval")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=monthly["forecast_month"], y=monthly["upper"],
        mode="lines", line=dict(width=0), showlegend=False,
    ))
    fig.add_trace(go.Scatter(
        x=monthly["forecast_month"], y=monthly["lower"],
        mode="lines", line=dict(width=0),
        fill="tonexty", fillcolor="rgba(21, 101, 192, 0.15)",
        name="95% CI",
    ))
    fig.add_trace(go.Scatter(
        x=monthly["forecast_month"], y=monthly["predicted"],
        mode="lines+markers", name="Predicted Revenue",
        line=dict(color="#1565C0", width=3),
    ))
    fig.update_layout(
        template="plotly_white",
        yaxis_title="Revenue (USD)",
        xaxis_title="Forecast Month",
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- Breakdown by BU ---
    st.subheader("Forecast by Business Unit")
    bu_forecast = (
        forecast_df.groupby(["business_unit", "forecast_month"])
        .agg(predicted=("predicted_revenue", "sum"))
        .reset_index()
    )
    fig = px.bar(
        bu_forecast, x="forecast_month", y="predicted", color="business_unit",
        barmode="group", title="Predicted Revenue by BU",
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig.update_layout(template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

    # --- Breakdown by Region ---
    st.subheader("Forecast by Region")
    region_forecast = (
        forecast_df.groupby(["region", "forecast_month"])
        .agg(predicted=("predicted_revenue", "sum"))
        .reset_index()
    )
    fig = px.bar(
        region_forecast, x="forecast_month", y="predicted", color="region",
        barmode="group", title="Predicted Revenue by Region",
        color_discrete_sequence=px.colors.qualitative.Pastel,
    )
    fig.update_layout(template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

    # --- Detailed Table ---
    st.subheader("Detailed Forecast Table")
    display_df = forecast_df[[
        "business_unit", "region", "product_family", "forecast_month",
        "predicted_revenue", "prediction_interval_lower", "prediction_interval_upper",
    ]].sort_values(["forecast_month", "business_unit", "region"])

    st.dataframe(
        display_df.style.format({
            "predicted_revenue": "${:,.0f}",
            "prediction_interval_lower": "${:,.0f}",
            "prediction_interval_upper": "${:,.0f}",
        }),
        use_container_width=True,
        height=400,
    )
