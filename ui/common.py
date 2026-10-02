"""Shared Streamlit helpers: API client with JWT, login form, chat/artifact rendering."""
from __future__ import annotations

import os
import re

import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components

API = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
MERMAID_RE = re.compile(r"```mermaid\s*\n(.*?)```", re.DOTALL)
AGENT_BADGES = {"hr": "🧾 HR", "devops": "🛠️ DevOps", "finance": "💵 Finance", "pm": "📋 PM",
                "developer": "💡 Developer", "supervisor": "🧭 Supervisor"}


class ApiError(Exception):
    pass


def _headers() -> dict:
    tok = st.session_state.get("token")
    return {"Authorization": f"Bearer {tok}"} if tok else {}


def api(method: str, path: str, **kwargs):
    try:
        r = requests.request(method, f"{API}{path}", headers=_headers(), timeout=kwargs.pop("timeout", 30), **kwargs)
    except requests.RequestException as e:
        raise ApiError(f"API not reachable: {e}")
    if r.status_code == 401 and path != "/auth/login":
        st.session_state.pop("token", None)
        st.session_state.pop("user", None)
        raise ApiError("Session expired. Please log in again.")
    if not r.ok:
        try:
            detail = r.json().get("detail", r.text)
        except ValueError:
            detail = r.text
        raise ApiError(str(detail))
    return r.json() if r.headers.get("content-type", "").startswith("application/json") else r.content


def login_gate(title: str, admin_only: bool = False) -> dict | None:
    """Render a login form until the user is authenticated. Returns the user dict."""
    if st.session_state.get("user"):
        return st.session_state["user"]
    st.title(title)
    with st.form("login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in", type="primary")
    if submitted:
        try:
            data = api("POST", "/auth/login", json={"username": username, "password": password})
        except ApiError as e:
            st.error(str(e))
            return None
        if admin_only and data["user"]["role"] != "admin":
            st.error("This console is for admins only.")
            return None
        st.session_state.token = data["access_token"]
        st.session_state.user = data["user"]
        st.rerun()
    return None


def logout_button() -> None:
    if st.sidebar.button("Log out", use_container_width=True):
        for k in list(st.session_state):
            del st.session_state[k]
        st.rerun()


def render_mermaid(code: str) -> None:
    lines = code.count("\n") + 1
    components.html(
        f"""<div class="mermaid">{code}</div>
        <script type="module">
          import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
          mermaid.initialize({{ startOnLoad: true, theme: "default" }});
        </script>""",
        height=min(900, 140 + lines * 28), scrolling=True,
    )


def render_content(text: str) -> None:
    pos = 0
    for m in MERMAID_RE.finditer(text):
        if text[pos:m.start()].strip():
            st.markdown(text[pos:m.start()])
        render_mermaid(m.group(1).strip())
        with st.expander("Mermaid source"):
            st.code(m.group(1).strip(), language="mermaid")
        pos = m.end()
    if text[pos:].strip():
        st.markdown(text[pos:])


@st.cache_data(show_spinner=False, ttl=600)
def _fetch_file(file_id: str, token: str) -> bytes:
    r = requests.get(f"{API}/files/{file_id}", headers={"Authorization": f"Bearer {token}"}, timeout=60)
    r.raise_for_status()
    return r.content


def download_button(a: dict, key: str) -> None:
    try:
        data = _fetch_file(a["file_id"], st.session_state.get("token", ""))
    except requests.RequestException as e:
        st.error(f"Could not fetch file: {e}")
        return
    icon = {"application/pdf": "📄"}.get(a.get("mime", ""), "⬇️")
    st.download_button(f"{icon} Download {a['filename']}", data=data, file_name=a["filename"],
                       mime=a.get("mime", "application/octet-stream"), key=key)


def render_artifacts(artifacts: list[dict], key: str) -> None:
    for i, a in enumerate(artifacts or []):
        t = a.get("type")
        if t == "file":
            download_button(a, f"dl-{key}-{i}")
        elif t == "sql":
            with st.expander(f"🗄️ Query result ({len(a.get('rows', []))} rows)"):
                st.code(a.get("query", ""), language="sql")
                if a.get("rows"):
                    st.dataframe(pd.DataFrame(a["rows"], columns=a["columns"]), use_container_width=True)
        elif t == "table":
            with st.expander(f"📊 {a.get('title', 'Table')} ({len(a.get('rows', []))} rows)", expanded=True):
                st.dataframe(pd.DataFrame(a["rows"], columns=a["columns"]), use_container_width=True, hide_index=True)


def render_message(msg: dict, idx: int) -> None:
    with st.chat_message(msg["role"], avatar="🧑" if msg["role"] == "user" else "🤖"):
        if msg["role"] == "assistant":
            badge = AGENT_BADGES.get(msg.get("agent"), msg.get("agent") or "")
            st.caption(f"{badge}" + (f" · {msg['route_reason']}" if msg.get("route_reason") else ""))
        render_content(msg["content"])
        render_artifacts(msg.get("artifacts"), f"m{idx}")
