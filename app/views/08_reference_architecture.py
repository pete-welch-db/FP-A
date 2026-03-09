"""
Nova Molding Systems FP&A — Reference Architecture
Displays the FP&A platform reference architecture diagram.
"""
import streamlit as st
from pathlib import Path


_ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"
_ARCH_IMAGE = _ASSETS_DIR / "FP&A Reference Architecture.png"


def render():
    st.title("Reference Architecture")
    st.caption("Databricks FP&A platform architecture overview")

    if _ARCH_IMAGE.exists():
        st.image(str(_ARCH_IMAGE), use_container_width=True)
    else:
        st.warning(
            f"Reference architecture image not found at: {_ARCH_IMAGE}"
        )
