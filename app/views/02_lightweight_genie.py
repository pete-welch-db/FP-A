"""
Nova Molding Systems FP&A — Lightweight Genie + Research Agent page.
"""
import time
import socket
import json
import subprocess
from datetime import datetime
from urllib.parse import urlparse
import pandas as pd
import requests
import streamlit as st

from config import DATABRICKS_HOST, DATABRICKS_TOKEN, GENIE_SPACE_ID

try:
    from databricks.sdk.core import Config
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False


def _get_token() -> str:
    """Get Databricks token: env first, then SDK Config (for Databricks Apps)."""
    if DATABRICKS_TOKEN:
        return DATABRICKS_TOKEN
    if SDK_AVAILABLE:
        try:
            auth = Config().authenticate()
            if auth and "Authorization" in auth:
                return auth["Authorization"].replace("Bearer ", "").strip()
        except Exception:
            pass
    return ""


PROCESSING_STATUSES = {
    "EXECUTING_QUERY",
    "PENDING",
    "FILTERING_RESULTS",
    "SUBMITTED",
    "RUNNING",
    "FILTERING_CONTEXT",
    "ASKING_AI",
    "PENDING_WAREHOUSE",
    "QUEUED",
}

GENIE_API_TIMEOUT_SECONDS = 30
DEBUG_LOG_LIMIT = 200
DEFAULT_USE_PROXY_FALLBACK = False


SAMPLE_QUESTIONS = [
    "What was total revenue by business unit for Q4 2025 vs Q4 2024?",
    "Show EBITDA margin trend by region for the last 8 quarters.",
    "Which end-markets had the highest year-over-year revenue growth?",
    "What is our current net leverage ratio and trend over the last 6 quarters?",
    "Compare free cash flow conversion between Actual and Budget for FY2025.",
    "Break down EBITDA variance between price, volume, and cost for Extrusion in Europe.",
]


def _append_debug(message: str):
    if "light_debug_logs" not in st.session_state:
        st.session_state.light_debug_logs = []
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.light_debug_logs.append(f"[{timestamp}] {message}")
    if len(st.session_state.light_debug_logs) > DEBUG_LOG_LIMIT:
        st.session_state.light_debug_logs = st.session_state.light_debug_logs[-DEBUG_LOG_LIMIT:]


def _get_http_session(trust_env: bool) -> requests.Session:
    """Create/reuse persistent HTTP session to reduce DNS churn."""
    key = f"light_http_session_{'proxy' if trust_env else 'direct'}"
    existing = st.session_state.get(key)
    if existing is not None:
        return existing

    session = requests.Session()
    session.trust_env = trust_env
    if not trust_env:
        # Force direct egress and ignore any ambient proxy config.
        session.proxies.update({"http": None, "https": None})
    st.session_state[key] = session
    return session


def _resolve_workspace_host() -> str | None:
    """Resolve workspace host and cache the last known good IP."""
    parsed = urlparse(DATABRICKS_HOST)
    hostname = parsed.hostname or ""
    if not hostname:
        return None

    try:
        ip = socket.gethostbyname(hostname)
        st.session_state.light_last_resolved_ip = ip
        _append_debug(f"DNS resolve success: {hostname} -> {ip}")
        return ip
    except Exception as exc:
        cached_ip = st.session_state.get("light_last_resolved_ip")
        _append_debug(f"DNS resolve failed for {hostname}: {exc}")
        if cached_ip:
            _append_debug(f"Using cached last-known workspace IP: {cached_ip}")
        return cached_ip


def _api_request(method: str, url: str, payload: dict | None = None) -> dict:
    """Call Databricks REST API with retry and network-path fallbacks.

    We first try direct egress (trust_env=False). If DNS fails, we retry using
    environment proxy settings (trust_env=True). If proxy tunnel fails, we retry
    direct egress. This handles common local networking differences.
    """
    headers = {
        "Authorization": f"Bearer {_get_token()}",
        "Content-Type": "application/json",
    }
    _resolve_workspace_host()

    use_proxy_fallback = st.session_state.get(
        "light_use_proxy_fallback",
        DEFAULT_USE_PROXY_FALLBACK,
    )
    attempts = [False, True, False, True] if use_proxy_fallback else [False, False]
    last_exc = None

    last_msg = ""
    for idx, trust_env in enumerate(attempts):
        session = _get_http_session(trust_env=trust_env)
        try:
            _append_debug(
                f"HTTP attempt {idx + 1}/{len(attempts)} {method} {url} trust_env={trust_env}"
            )
            if method == "GET":
                resp = session.get(url, headers=headers, timeout=GENIE_API_TIMEOUT_SECONDS)
            else:
                resp = session.post(
                    url, headers=headers, json=payload, timeout=GENIE_API_TIMEOUT_SECONDS
                )
            resp.raise_for_status()
            _append_debug(
                f"HTTP success {method} {url} status={resp.status_code} trust_env={trust_env}"
            )
            return resp.json()
        except requests.RequestException as exc:
            last_exc = exc
            msg = str(exc).lower()
            last_msg = msg
            is_dns_error = "nameresolutionerror" in msg or "failed to resolve" in msg
            is_proxy_error = "proxyerror" in msg or "tunnel connection failed" in msg
            can_retry = idx < len(attempts) - 1 and (is_dns_error or is_proxy_error)
            _append_debug(
                "HTTP failure "
                f"{method} {url} trust_env={trust_env} "
                f"type={type(exc).__name__} retry={can_retry} err={exc}"
            )
            if can_retry:
                time.sleep(0.8 * (idx + 1))
                continue
            break

    # Last-resort fallback through curl, which can behave differently with local DNS/proxy stacks.
    if last_exc is not None and (
        "nameresolutionerror" in last_msg
        or "failed to resolve" in last_msg
        or "proxyerror" in last_msg
        or "tunnel connection failed" in last_msg
    ):
        _append_debug(f"Trying curl fallback for {method} {url}")
        try:
            cmd = [
                "curl",
                "-sS",
                "--noproxy",
                "*",
                "-X",
                method,
                "-H",
                f"Authorization: Bearer {_get_token()}",
                "-H",
                "Content-Type: application/json",
                url,
            ]
            if payload is not None:
                cmd.extend(["--data", json.dumps(payload)])

            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
            )
            parsed = json.loads(result.stdout) if result.stdout.strip() else {}
            _append_debug(f"curl fallback succeeded for {method} {url}")
            return parsed
        except Exception as curl_exc:
            _append_debug(f"curl fallback failed for {method} {url}: {curl_exc}")

    _append_debug(f"HTTP final failure {method} {url}: {last_exc}")
    raise RuntimeError(f"API request failed for {url}: {last_exc}") from last_exc


def _genie_base_url() -> str:
    return f"{DATABRICKS_HOST.rstrip('/')}/api/2.0/genie/spaces/{GENIE_SPACE_ID}"


def _run_connectivity_check() -> tuple[bool, dict]:
    """Run DNS + API checks and return structured diagnostics."""
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


def _start_conversation(prompt: str) -> tuple[str, str]:
    body = {"content": prompt}
    resp = _api_request("POST", f"{_genie_base_url()}/start-conversation", body)
    return resp.get("conversation_id", ""), resp.get("message_id", "")


def _create_message(conversation_id: str, prompt: str) -> str:
    body = {"content": prompt}
    resp = _api_request(
        "POST",
        f"{_genie_base_url()}/conversations/{conversation_id}/messages",
        body,
    )
    return resp.get("message_id", "")


def _get_message(conversation_id: str, message_id: str) -> dict:
    return _api_request(
        "GET",
        f"{_genie_base_url()}/conversations/{conversation_id}/messages/{message_id}",
    )


def _extract_text_and_query(response: dict):
    assistant_text = []
    sql_blocks = []
    table_df = None

    direct_content = response.get("content")
    if direct_content:
        assistant_text.append(str(direct_content))

    for attachment in response.get("attachments") or []:
        if attachment.get("text") and attachment["text"].get("content"):
            assistant_text.append(attachment["text"]["content"])
        if attachment.get("query"):
            query = attachment["query"].get("query")
            if query:
                sql_blocks.append(query)

    query_result = response.get("query_result") or {}
    statement_id = query_result.get("statement_id")
    if statement_id:
        try:
            statement = _api_request(
                "GET",
                f"{DATABRICKS_HOST.rstrip('/')}/api/2.0/sql/statements/{statement_id}",
            )
            data_array = (
                statement.get("result", {}).get("data_array")
                or statement.get("result", {}).get("chunk", {}).get("data_array")
                or []
            )
            columns = [
                c.get("name")
                for c in statement.get("manifest", {}).get("schema", {}).get("columns", [])
            ]
            if data_array and columns:
                table_df = pd.DataFrame(data_array, columns=columns)
        except Exception:
            pass

    return "\n\n".join(assistant_text).strip(), sql_blocks, table_df


def _wait_for_completion(conversation_id: str, message_id: str, max_attempts: int = 60):
    """Poll Genie message status with explicit timeout/failure handling."""
    for _ in range(max_attempts):
        response = _get_message(conversation_id=conversation_id, message_id=message_id)
        status = str(response.get("status", "")).upper()
        if status == "COMPLETED":
            return response
        if status in ("FAILED", "CANCELLED"):
            error = response.get("error")
            if isinstance(error, dict):
                error = error.get("message")
            raise RuntimeError(f"Genie request failed with status {status}: {error}")
        if status and status not in PROCESSING_STATUSES:
            print(f"[lightweight_genie] unexpected status: {status}")
        time.sleep(2.0)
    raise TimeoutError("Genie request timed out while waiting for completion.")


def _is_stale_conversation_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return (
        "not found" in msg
        or "404" in msg
        or "conversation" in msg and "invalid" in msg
    )


def _ask_genie(prompt: str):
    """Send prompt to Genie with stale-conversation recovery + bounded wait."""
    response = None

    if st.session_state.light_conversation_id:
        try:
            message_id = _create_message(
                conversation_id=st.session_state.light_conversation_id,
                prompt=prompt,
            )
            if not message_id:
                raise RuntimeError("Genie did not return message_id for follow-up message.")
            response = _wait_for_completion(
                conversation_id=st.session_state.light_conversation_id,
                message_id=message_id,
            )
        except Exception as exc:
            if not _is_stale_conversation_error(exc):
                raise
            print("[lightweight_genie] stale conversation detected, resetting and retrying")
            st.session_state.light_conversation_id = None

    if response is None:
        conversation_id, message_id = _start_conversation(prompt=prompt)
        if not conversation_id or not message_id:
            raise RuntimeError("Genie did not return conversation_id/message_id.")
        st.session_state.light_conversation_id = conversation_id
        response = _wait_for_completion(
            conversation_id=conversation_id,
            message_id=message_id,
        )

    return response


def _render_chat_mode(prompt: str):
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Genie is generating an answer..."):
            try:
                _append_debug("Chat mode request started")
                response = _ask_genie(prompt)
                text, sql_blocks, data = _extract_text_and_query(response)
                st.markdown(text or "No text response returned.")
                if data is not None:
                    st.dataframe(data, use_container_width=True)
                for idx, sql in enumerate(sql_blocks):
                    with st.expander(f"Generated SQL {idx + 1}"):
                        st.code(sql, language="sql", wrap_lines=True)
                _append_debug("Chat mode request completed")
            except TimeoutError:
                st.error(
                    "Genie timed out while processing this request. "
                    "Try a simpler question or reset conversation."
                )
                _append_debug("Chat mode request timed out")
            except Exception as exc:
                st.error(f"Genie request failed: {exc}")
                _append_debug(f"Chat mode request failed: {exc}")


def _render_research_mode(user_prompt: str):
    with st.chat_message("user"):
        st.markdown(user_prompt)

    with st.chat_message("assistant"):
        status = st.status("Research Agent running...", expanded=True)
        step_outputs = []
        steps = [
            (
                "Step 1: scope",
                (
                    "You are an FP&A research planner. For the question below, produce 3 concise "
                    "sub-questions that would validate the answer from different angles.\n\n"
                    f"Question: {user_prompt}"
                ),
            ),
            (
                "Step 2: evidence",
                (
                    "Answer the original question with key evidence. Return concise bullets first, "
                    "then include any supporting tabular output if available.\n\n"
                    f"Question: {user_prompt}"
                ),
            ),
            (
                "Step 3: challenge and risks",
                (
                    "Identify assumptions, potential data caveats, and what could change this "
                    "answer in the next quarter for this FP&A question.\n\n"
                    f"Question: {user_prompt}"
                ),
            ),
            (
                "Step 4: executive synthesis",
                (
                    "Provide a CFO-ready synthesis in 5 bullets: answer, key drivers, confidence, "
                    "risk flags, and recommended next action.\n\n"
                    f"Question: {user_prompt}"
                ),
            ),
        ]

        try:
            with st.spinner("Running multi-step analysis..."):
                for label, prompt in steps:
                    status.update(label=f"{label}...", state="running")
                    _append_debug(f"Research step started: {label}")
                    response = _ask_genie(prompt)
                    text, sql_blocks, data = _extract_text_and_query(response)
                    step_outputs.append({
                        "label": label,
                        "text": text,
                        "sql": sql_blocks,
                        "data": data,
                    })
                    time.sleep(0.15)
                    _append_debug(f"Research step completed: {label}")
        except TimeoutError:
            status.update(label="Research Agent timeout", state="error")
            st.error(
                "Research Agent timed out on one of the steps. "
                "Try resetting conversation and asking a narrower question."
            )
            _append_debug("Research agent timed out")
            return
        except Exception as exc:
            status.update(label="Research Agent error", state="error")
            st.error(f"Research Agent failed: {exc}")
            _append_debug(f"Research agent failed: {exc}")
            return

        status.update(label="Research Agent complete", state="complete")
        st.markdown("### Research output")
        for item in step_outputs:
            with st.expander(item["label"], expanded=item["label"].endswith("synthesis")):
                st.markdown(item["text"] or "No text response returned.")
                if item["data"] is not None:
                    st.dataframe(item["data"], use_container_width=True)
                for sql in item["sql"]:
                    st.code(sql, language="sql", wrap_lines=True)

        st.success("Reasoning steps completed: 4/4")


def _render_question_chips():
    st.markdown("#### Sample questions")
    cols = st.columns(2)
    for idx, question in enumerate(SAMPLE_QUESTIONS):
        with cols[idx % 2]:
            if st.button(question, use_container_width=True, key=f"sample_q_{idx}"):
                st.session_state.light_prefill_prompt = question


def render():
    st.title("Genie Space")
    st.caption("Databricks-style experience with Chat and Research Agent modes")

    if "light_conversation_id" not in st.session_state:
        st.session_state.light_conversation_id = None
    if "light_prefill_prompt" not in st.session_state:
        st.session_state.light_prefill_prompt = ""
    if "light_debug_logs" not in st.session_state:
        st.session_state.light_debug_logs = []

    if not GENIE_SPACE_ID:
        st.warning(
            "GENIE_SPACE_ID is not configured. Set it in app.yaml or .env to enable this page."
        )
        _render_question_chips()
        return

    if not DATABRICKS_HOST or not _get_token():
        st.error("DATABRICKS_HOST and a valid token (DATABRICKS_TOKEN or Databricks CLI auth) must be configured for Genie.")
        return

    mode = st.radio(
        "Mode",
        options=["Chat", "Research Agent"],
        horizontal=True,
        help="Chat: direct answer. Research Agent: multi-step investigation and synthesis.",
    )

    left, right = st.columns([1.35, 1])
    with right:
        st.checkbox(
            "Use proxy fallback (advanced)",
            key="light_use_proxy_fallback",
            value=DEFAULT_USE_PROXY_FALLBACK,
            help=(
                "Disabled by default because corporate proxies can block Genie tunnel requests "
                "with 403. Enable only if direct networking fails."
            ),
        )

        if st.button("Run connectivity check", use_container_width=True):
            with st.spinner("Running connectivity checks..."):
                ok, diagnostics = _run_connectivity_check()
            if ok:
                st.success("Connectivity check passed")
            else:
                st.error("Connectivity check failed")
            st.json(diagnostics)

        _render_question_chips()
        if st.button("Reset conversation", use_container_width=True):
            st.session_state.light_conversation_id = None
            st.session_state.light_prefill_prompt = ""
            _append_debug("Conversation reset by user")
            st.rerun()

        with st.expander("Debug logs", expanded=False):
            if st.session_state.light_debug_logs:
                st.code("\n".join(st.session_state.light_debug_logs[-80:]))
            else:
                st.caption("No debug logs yet.")
            if st.button("Clear debug logs", use_container_width=True):
                st.session_state.light_debug_logs = []
                st.rerun()

    with left:
        prompt = st.chat_input(
            "Ask a finance question...",
            key="lightweight_chat_input",
        )

        effective_prompt = prompt or st.session_state.light_prefill_prompt
        if effective_prompt:
            st.session_state.light_prefill_prompt = ""
            if mode == "Chat":
                _render_chat_mode(effective_prompt)
            else:
                _render_research_mode(effective_prompt)
