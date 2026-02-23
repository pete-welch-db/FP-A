"""
Nova Molding Systems FP&A — Reusable KPI Card Component
Renders a styled metric card with value, delta, and optional sparkline.
"""
import streamlit as st
import plotly.graph_objects as go


def render_kpi_card(
    label: str,
    value: str,
    delta: str | None = None,
    delta_color: str = "normal",
    sparkline_data: list[float] | None = None,
):
    """Display a KPI metric card with an optional sparkline beneath."""
    st.metric(label=label, value=value, delta=delta, delta_color=delta_color)

    if sparkline_data and len(sparkline_data) > 1:
        fig = go.Figure(
            go.Scatter(
                y=sparkline_data,
                mode="lines",
                line=dict(color="#FF3621", width=2),
                fill="tozeroy",
                fillcolor="rgba(255, 54, 33, 0.1)",
            )
        )
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            height=50,
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def fmt_currency(value: float, prefix: str = "$", suffix: str = "") -> str:
    """Format a number as currency with appropriate magnitude suffix."""
    if abs(value) >= 1e9:
        return f"{prefix}{value / 1e9:.1f}B{suffix}"
    if abs(value) >= 1e6:
        return f"{prefix}{value / 1e6:.1f}M{suffix}"
    if abs(value) >= 1e3:
        return f"{prefix}{value / 1e3:.1f}K{suffix}"
    return f"{prefix}{value:,.0f}{suffix}"


def fmt_pct(value: float) -> str:
    """Format a decimal or percentage value."""
    return f"{value:.1f}%"
