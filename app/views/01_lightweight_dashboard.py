import streamlit as st
import streamlit.components.v1 as components

def render():
    """Render embedded executive dashboard only."""
    components.iframe(
        src="https://adb-984752964297111.11.azuredatabricks.net/embed/dashboardsv3/01f110cc93bf12279633a8034e66303d?o=984752964297111",
        height=980,
        scrolling=False,
    )
