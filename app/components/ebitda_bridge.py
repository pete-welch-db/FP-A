"""
Nova Molding Systems FP&A — EBITDA Bridge (Waterfall) Chart Component
Renders a Plotly waterfall chart for the EBITDA walk.
"""
import plotly.graph_objects as go
import streamlit as st


def render_ebitda_waterfall(
    revenue: float,
    cogs: float,
    opex: float,
    title: str = "EBITDA Bridge",
):
    """Render a waterfall chart: Revenue → Gross Profit → EBITDA."""
    gross_profit = revenue - abs(cogs)
    ebitda = gross_profit - abs(opex)

    labels = ["Revenue", "COGS", "Gross Profit", "OpEx", "EBITDA"]
    measures = ["absolute", "relative", "total", "relative", "total"]
    values = [revenue, -abs(cogs), 0, -abs(opex), 0]
    text = [
        f"${revenue / 1e6:.1f}M",
        f"-${abs(cogs) / 1e6:.1f}M",
        f"${gross_profit / 1e6:.1f}M",
        f"-${abs(opex) / 1e6:.1f}M",
        f"${ebitda / 1e6:.1f}M",
    ]

    fig = go.Figure(
        go.Waterfall(
            name="EBITDA Bridge",
            orientation="v",
            measure=measures,
            x=labels,
            y=values,
            text=text,
            textposition="outside",
            connector={"line": {"color": "rgb(63, 63, 63)", "width": 1}},
            increasing={"marker": {"color": "#2E7D32"}},
            decreasing={"marker": {"color": "#C62828"}},
            totals={"marker": {"color": "#1565C0"}},
        )
    )

    fig.update_layout(
        title=title,
        showlegend=False,
        height=420,
        yaxis_title="USD",
        template="plotly_white",
    )

    st.plotly_chart(fig, use_container_width=True)
