import streamlit as st


def render():
    """Landing page narrative for lightweight FP&A platform demo — light mode, Databricks colors."""
    st.markdown(
        """
        <div style="
            background: linear-gradient(135deg, #FFFFFF 0%, #F5F7FA 100%);
            border-radius: 16px;
            padding: 40px 36px;
            margin-bottom: 24px;
            border: 1px solid #E8ECF1;
            position: relative;
            overflow: hidden;
        ">
            <div style="
                position: absolute;
                top: -60px;
                right: -60px;
                width: 220px;
                height: 220px;
                background: radial-gradient(circle, rgba(255,54,33,0.12) 0%, transparent 70%);
                border-radius: 50%;
            "></div>
            <div style="position: relative; z-index: 1;">
                <p style="
                    color: #FF3621;
                    font-size: 0.82rem;
                    font-weight: 600;
                    letter-spacing: 1.8px;
                    text-transform: uppercase;
                    margin-bottom: 10px;
                ">DATABRICKS FOR FINANCE</p>
                <p style="
                    color: #1B3139;
                    font-size: 2.4rem;
                    font-weight: 700;
                    line-height: 1.15;
                    margin: 0 0 12px 0;
                ">AI-Driven FP&A Automation</p>
                <p style="
                    color: #4A5568;
                    font-size: 1.1rem;
                    margin: 0;
                    max-width: 700px;
                ">
                    Unify finance data, automate planning cycles, and empower every analyst with
                    AI/BI dashboards plus natural language analytics on Databricks.
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div style="
            background: #FFFFFF;
            border-radius: 12px;
            padding: 20px 24px;
            margin-bottom: 24px;
            border: 1px solid #E8ECF1;
            border-left: 4px solid #FF3621;
        ">
            <p style="
                color: #1B3139;
                font-size: 1.02rem;
                font-style: italic;
                margin: 0 0 6px 0;
                line-height: 1.45;
            ">"Finance teams should spend less time assembling data and more time driving decisions.
            Databricks helps automate the data-to-decision loop."</p>
            <p style="color: #718096; font-size: 0.9rem; margin: 0;">
                Modern FP&A operating principle
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Problem section with research-backed stats
    st.subheader("The Problem: FP&A Is Often Manual")
    p1, p2, p3 = st.columns(3)
    p1.metric("FP&A effort on data prep", "45–50%")
    p2.metric("Time on insight & action", "≈35%")
    p3.metric("Typical forecast refresh", "8–16 days")

    st.caption(
        "Sources: FP&A Trends Survey 2024, AFP/Workday FP&A Technology & Data Platform Survey, "
        "APQC forecasting benchmarks."
    )

    q1, q2 = st.columns(2)
    with q1:
        st.metric("Teams relying on spreadsheets", ">90%")
    with q2:
        st.metric("Finance leaders citing low automation", "≈80%")

    st.caption(
        "Sources: AFP/Workday FP&A Survey; EY 'Finance of the Future' survey."
    )

    st.markdown("---")
    st.subheader("Why Databricks for FP&A Automation")
    c1, c2 = st.columns(2)

    with c1:
        st.markdown(
            """
            - **Unified Finance Lakehouse**: consolidate ERP, planning, CRM, and ops data.
            - **Unity Catalog Governance**: one control plane for secure, trusted finance assets.
            - **Automated Pipelines**: refresh KPI layers and forecasts without spreadsheet churn.
            """
        )

    with c2:
        st.markdown(
            """
            - **AI/BI Dashboards**: executive-ready KPI visibility in near real time.
            - **Genie Natural Language**: ask finance questions and get SQL-backed answers.
            - **Apps + Agents**: package repeatable workflows for analysts and business users.
            """
        )

    st.markdown(
        """
        <div style="
            background: #F5F7FA;
            border-radius: 12px;
            padding: 18px 20px;
            margin: 22px 0 18px 0;
            border: 1px solid #E8ECF1;
            border-left: 4px solid #FF3621;
        ">
            <p style="color: #1B3139; font-size: 1.0rem; font-weight: 600; margin: 0 0 6px 0;">
                Unity Catalog as the FP&A control plane
            </p>
            <p style="color: #4A5568; font-size: 0.92rem; margin: 0;">
                Governed finance data products, AI tools, and dashboard semantics all in one place,
                reused consistently across BI, Genie, and applications.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
