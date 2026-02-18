"""
Milacron FP&A — Genie Assistant
Natural-language Q&A powered by the Databricks Genie Conversations API.
Based on the apps-cookbook.dev recipe: Chat with a Genie Space.
"""
import streamlit as st
import pandas as pd
from config import GENIE_SPACE_ID, DASHBOARD_EMBED_URL

try:
    from databricks.sdk import WorkspaceClient
    from databricks.sdk.service.dashboards import GenieFeedbackRating
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False


def _display_message(message: dict):
    if "content" in message and message["content"]:
        st.markdown(message["content"])
    if "data" in message and message["data"] is not None:
        st.dataframe(message["data"], use_container_width=True)
    if "code" in message and message["code"]:
        with st.expander("Show generated SQL"):
            st.code(message["code"], language="sql", wrap_lines=True)


def render():
    st.title("Genie Assistant")
    st.caption("Ask natural-language questions about Milacron's financial data")

    if not GENIE_SPACE_ID:
        st.warning(
            "Genie Space ID is not configured. Deploy the pipeline and update "
            "GENIE_SPACE_ID in app.yaml."
        )
        _render_sample_questions()
        _render_dashboard_embed()
        return

    if not SDK_AVAILABLE:
        st.error("databricks-sdk is not installed. Add it to requirements.txt.")
        return

    w = WorkspaceClient()

    # Chat history
    if "genie_messages" not in st.session_state:
        st.session_state.genie_messages = []
    if "genie_conversation_id" not in st.session_state:
        st.session_state.genie_conversation_id = None

    # Display chat history
    for msg in st.session_state.genie_messages:
        with st.chat_message(msg["role"]):
            _display_message(msg)

    # Chat input
    if prompt := st.chat_input("Ask a question about Milacron's financials…"):
        st.session_state.genie_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                try:
                    if st.session_state.genie_conversation_id:
                        response = w.genie.create_message_and_wait(
                            GENIE_SPACE_ID,
                            st.session_state.genie_conversation_id,
                            prompt,
                        )
                    else:
                        response = w.genie.start_conversation_and_wait(
                            GENIE_SPACE_ID, prompt,
                        )
                        st.session_state.genie_conversation_id = response.conversation_id

                    _process_genie_response(w, response)
                except Exception as exc:
                    st.error(f"Genie error: {exc}")

    _render_sample_questions()
    _render_dashboard_embed()


def _process_genie_response(w, response):
    """Parse Genie response attachments into displayable messages."""
    for attachment in response.attachments or []:
        if attachment.text:
            msg = {"role": "assistant", "content": attachment.text.content}
            st.session_state.genie_messages.append(msg)
            _display_message(msg)
        elif attachment.query:
            data = None
            if response.query_result and response.query_result.statement_id:
                try:
                    result = w.statement_execution.get_statement(
                        response.query_result.statement_id
                    )
                    data = pd.DataFrame(
                        result.result.data_array,
                        columns=[c.name for c in result.manifest.schema.columns],
                    )
                except Exception:
                    pass

            msg = {
                "role": "assistant",
                "content": attachment.query.description,
                "data": data,
                "code": attachment.query.query,
            }
            st.session_state.genie_messages.append(msg)
            _display_message(msg)

    # Feedback
    if response.message_id:
        rating = st.feedback("thumbs", key=f"fb_{response.message_id}")
        mapping = {1: GenieFeedbackRating.POSITIVE, 0: GenieFeedbackRating.NEGATIVE}
        if rating is not None and response.message_id:
            try:
                w.genie.send_message_feedback(
                    GENIE_SPACE_ID,
                    st.session_state.genie_conversation_id,
                    response.message_id,
                    mapping[rating],
                )
            except Exception:
                pass


def _render_sample_questions():
    """Show sample questions users can ask."""
    with st.expander("Sample Questions", expanded=not GENIE_SPACE_ID):
        questions = [
            "What was total revenue by business unit for Q4 2025 vs Q4 2024?",
            "Show me EBITDA margin trend by region for the last 8 quarters.",
            "Which end-markets had the highest revenue growth year-over-year?",
            "What is our current net leverage ratio and how has it trended?",
            "Compare free cash flow conversion between Actual and Budget for FY2025.",
            "What are the top 5 entities by DSO?",
            "What is the aftermarket revenue mix by region, and which regions are below 30%?",
            "Show the service attach rate trend for Injection Molding.",
            "What does the ML model predict for Americas Injection Molding revenue next quarter?",
            "Which plants have utilization below 70% this quarter?",
            "What is the book-to-bill ratio by BU for the last 6 months?",
            "Break down the EBITDA variance between price, volume, and cost for Extrusion in Europe.",
        ]
        for q in questions:
            st.markdown(f"- {q}")


def _render_dashboard_embed():
    """Embed the AI/BI dashboard if URL is configured."""
    if DASHBOARD_EMBED_URL:
        st.markdown("---")
        st.subheader("AI/BI Dashboard")
        import streamlit.components.v1 as components
        components.iframe(src=DASHBOARD_EMBED_URL, height=700, scrolling=True)
