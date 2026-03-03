import streamlit as st
import streamlit.components.v1 as components

from config import DASHBOARD_EMBED_URL, DASHBOARD_EMBED_URL_V2


def render():
    """Render embedded executive dashboard only."""
    embed_url = DASHBOARD_EMBED_URL_V2 or DASHBOARD_EMBED_URL
    if not embed_url:
        st.warning(
            "Dashboard embed URL is not configured. "
            "Set DASHBOARD_EMBED_URL (or DASHBOARD_EMBED_URL_V2) in your local .env and app/app.yaml."
        )
        return

    components.iframe(src=embed_url, height=980, scrolling=False)
