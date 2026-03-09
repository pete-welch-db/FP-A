"""
Nova Molding Systems FP&A — Settings
Network diagnostics, proxy configuration, and debug logs.
"""
import socket
from importlib import import_module
from urllib.parse import urlparse

import streamlit as st

from config import DATABRICKS_HOST, GENIE_SPACE_ID

_genie_mod = import_module("views.02_lightweight_genie")


def render():
    st.title("Settings")

    st.subheader("App Mode")

    current_mode = st.session_state.get("confirmed_app_mode", "Lightweight")
    options = ["Lightweight", "Full"]
    selected = st.selectbox(
        "App Mode",
        options=options,
        index=options.index(current_mode),
        help="Lightweight: 4-page executive walkthrough. Full: all analytics pages.",
    )

    if selected != current_mode:
        if st.button(f"Switch to {selected}", type="primary"):
            st.session_state.confirmed_app_mode = selected
            st.rerun()
    else:
        st.caption(f"Currently in **{current_mode}** mode.")

    st.markdown("---")

    st.subheader("Network & Proxy")

    st.checkbox(
        "Use proxy fallback (advanced)",
        key="light_use_proxy_fallback",
        value=st.session_state.get("light_use_proxy_fallback", False),
        help=(
            "Disabled by default because corporate proxies can block Genie tunnel requests "
            "with 403. Enable only if direct networking fails."
        ),
    )

    st.subheader("Connectivity Check")

    if st.button("Run connectivity check", use_container_width=False):
        with st.spinner("Running connectivity checks..."):
            ok, diagnostics = _run_connectivity_check()
        if ok:
            st.success("Connectivity check passed")
        else:
            st.error("Connectivity check failed")
        st.json(diagnostics)

    st.subheader("Debug Logs")

    if "light_debug_logs" not in st.session_state:
        st.session_state.light_debug_logs = []

    if st.session_state.light_debug_logs:
        st.code("\n".join(st.session_state.light_debug_logs[-80:]))
    else:
        st.caption("No debug logs yet.")

    if st.button("Clear debug logs"):
        st.session_state.light_debug_logs = []
        st.rerun()


def _run_connectivity_check() -> tuple[bool, dict]:
    _api_request = _genie_mod._api_request
    _genie_base_url = _genie_mod._genie_base_url
    _append_debug = _genie_mod._append_debug

    diagnostics: dict = {
        "host": DATABRICKS_HOST,
        "space_id": GENIE_SPACE_ID,
    }
    try:
        parsed = urlparse(DATABRICKS_HOST)
        hostname = parsed.hostname or ""
        diagnostics["hostname"] = hostname
        diagnostics["dns_ip"] = socket.gethostbyname(hostname) if hostname else ""
        _append_debug(f"DNS resolved {hostname} -> {diagnostics['dns_ip']}")
    except Exception as exc:
        diagnostics["dns_error"] = str(exc)
        _append_debug(f"DNS resolution failed: {exc}")

    try:
        space = _api_request("GET", _genie_base_url())
        diagnostics["space_title"] = space.get("title")
        diagnostics["warehouse_id"] = space.get("warehouse_id")
        _append_debug("Connectivity check passed: space metadata fetched successfully")
        return True, diagnostics
    except Exception as exc:
        diagnostics["api_error"] = str(exc)
        _append_debug(f"Connectivity API check failed: {exc}")
        return False, diagnostics
