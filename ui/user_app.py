"""End-user workspace: chat with the department agents you have access to.

Run: streamlit run ui/user_app.py --server.port 8501
"""
import sys
import uuid
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ApiError, api, login_gate, logout_button, render_message  # noqa: E402

st.set_page_config(page_title="Stixor Office Assistant", page_icon="🏢", layout="wide")

user = login_gate("🏢 Stixor Office Assistant")
if not user:
    st.stop()

ss = st.session_state
ss.setdefault("thread_id", uuid.uuid4().hex)
ss.setdefault("history", [])

# Returning from the Atlassian consent screen
qp = st.query_params
if qp.get("jira") == "connected":
    st.toast("Jira connected ✅")
    qp.clear()
elif qp.get("jira") == "error":
    st.error(f"Jira connection failed: {qp.get('detail', '')}")
    qp.clear()

agents = {a["name"]: a for a in user["available_agents"]}


def load_thread(thread_id: str) -> None:
    try:
        data = api("GET", f"/threads/{thread_id}")
    except ApiError as e:
        st.error(str(e))
        return
    ss.thread_id = thread_id
    ss.history = [{"role": m["role"], "content": m["content"], "agent": m.get("agent"),
                   "artifacts": m.get("artifacts", [])} for m in data["messages"]]


# ---------------- Sidebar ----------------
with st.sidebar:
    st.markdown(f"**{user['full_name'] or user['username']}** · `{user['role']}`")
    logout_button()
    if st.button("🆕 New conversation", use_container_width=True, type="primary"):
        ss.thread_id = uuid.uuid4().hex
        ss.history = []
        st.rerun()

    options = ["auto", *agents]
    department = st.radio(
        "Assistant",
        options,
        format_func=lambda d: "🧭 Auto (supervisor decides)" if d == "auto" else f"{agents[d]['icon']} {agents[d]['label']}",
        help="Auto lets the supervisor route your message; pick one to talk to it directly.",
    )
    if not agents:
        st.warning("You don't have access to any assistant yet. Ask an admin.")

    template_id = None
    # ---- context panels ----
    if "hr" in agents and department in ("auto", "hr"):
        with st.expander("🧾 Contract templates", expanded=department == "hr"):
            try:
                templates = api("GET", "/templates")
            except ApiError:
                templates = []
            names = {t["template_id"]: f"{t['name']} ({t['placeholder_count']} fields)" for t in templates}
            chosen = st.selectbox("Template", ["(let the agent choose)", *names], format_func=lambda x: names.get(x, x))
            template_id = None if chosen.startswith("(") else chosen
            with st.form("upload", clear_on_submit=True):
                up = st.file_uploader("Upload .docx template", type=["docx"])
                up_name = st.text_input("Name (optional)")
                if st.form_submit_button("Upload") and up is not None:
                    try:
                        t = api("POST", "/templates", files={"file": (up.name, up.getvalue(), up.type)},
                                data={"name": up_name or None, "description": ""}, timeout=60)
                        st.success(f"Uploaded {t['name']} ({t['placeholder_count']} fields)")
                    except ApiError as e:
                        st.error(str(e))

    if "finance" in agents and department in ("auto", "finance"):
        with st.expander("💵 Recent invoices", expanded=department == "finance"):
            try:
                invoices = api("GET", "/invoices", params={"limit": 8})
            except ApiError:
                invoices = []
            if not invoices:
                st.caption("No invoices yet.")
            for inv in invoices:
                st.markdown(f"**{inv['invoice_no']}** · {inv['client']} · {inv['currency']} {inv['total']:,.2f}  \n"
                            f"<small>{inv['issue_date']} – {inv['service_description'][:40]}</small>", unsafe_allow_html=True)

    if "pm" in agents and department in ("auto", "pm"):
        with st.expander("📋 Jira connection", expanded=department == "pm"):
            try:
                status = api("GET", "/integrations/jira/status")
            except ApiError as e:
                status = {"connected": False, "oauth_available": False}
                st.error(str(e))
            if status.get("connected"):
                st.success(f"Connected to {status['site_url'].replace('https://', '')} as {status['account']}")
                if st.button("Disconnect Jira"):
                    api("DELETE", "/integrations/jira")
                    st.rerun()
            else:
                if status.get("oauth_available"):
                    url = api("GET", "/integrations/jira/connect")["authorize_url"]
                    st.link_button("🔗 Connect Jira", url, type="primary", use_container_width=True)
                    st.caption("or use an API token:")
                with st.form("jira_token"):
                    site = st.text_input("Jira site", placeholder="yourcompany.atlassian.net")
                    email = st.text_input("Atlassian email")
                    token = st.text_input("API token", type="password",
                                          help="Create one at id.atlassian.com → Security → API tokens")
                    if st.form_submit_button("Connect with token"):
                        try:
                            res = api("POST", "/integrations/jira/token",
                                      json={"site_url": site, "email": email, "api_token": token})
                            st.success(f"Connected as {res.get('account', email)}")
                            st.rerun()
                        except ApiError as e:
                            st.error(str(e))

    st.divider()
    st.caption("Conversations")
    try:
        threads = api("GET", "/threads")
    except ApiError:
        threads = []
    for t in threads[:15]:
        label = ("▶ " if t["thread_id"] == ss.thread_id else "") + (t["title"] or "Untitled")[:40]
        if st.button(label, key=f"t-{t['thread_id']}", use_container_width=True):
            load_thread(t["thread_id"])
            st.rerun()

# ---------------- Chat ----------------
st.title("🏢 Stixor Office Assistant")
if agents:
    st.caption(" · ".join(f"{a['icon']} **{a['label']}** – {a['summary']}" for a in agents.values()))

for i, msg in enumerate(ss.history):
    render_message(msg, i)

prompt = st.chat_input("Ask HR, Finance, PM, DevOps or Developer…" if agents else "No assistants available",
                       disabled=not agents)
if prompt:
    ss.history.append({"role": "user", "content": prompt})
    render_message(ss.history[-1], len(ss.history) - 1)
    with st.spinner("Working on it…"):
        try:
            data = api("POST", "/chat", json={"message": prompt, "thread_id": ss.thread_id,
                                              "department": department, "template_id": template_id}, timeout=900)
            reply = {"role": "assistant", "content": data["reply"], "agent": data["agent"],
                     "route_reason": data.get("route_reason"), "artifacts": data.get("artifacts", [])}
        except ApiError as e:
            reply = {"role": "assistant", "content": f"⚠️ {e}", "agent": "supervisor"}
    ss.history.append(reply)
    render_message(reply, len(ss.history) - 1)
