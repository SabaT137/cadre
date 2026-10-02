"""Admin console: usage stats, agents, activity, users, integrations.

Run: streamlit run ui/admin_app.py --server.port 8502
"""
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import AGENT_BADGES, ApiError, api, login_gate, logout_button  # noqa: E402

st.set_page_config(page_title="Stixor Admin Console", page_icon="🛡️", layout="wide")

user = login_gate("🛡️ Stixor Admin Console", admin_only=True)
if not user:
    st.stop()

with st.sidebar:
    st.markdown(f"**{user['full_name'] or user['username']}** · admin")
    days = st.select_slider("Period", options=[1, 7, 14, 30, 90], value=7, format_func=lambda d: f"Last {d} day(s)")
    if st.button("↻ Refresh", use_container_width=True):
        st.rerun()
    logout_button()

st.title("🛡️ Admin Console")
tab_overview, tab_agents, tab_activity, tab_users, tab_integrations = st.tabs(
    ["📈 Overview", "🤖 Agents", "🧾 Activity", "👥 Users", "🔌 Integrations"])


def safe(call, default):
    try:
        return call()
    except ApiError as e:
        st.error(str(e))
        return default


# ---------------- Overview ----------------
with tab_overview:
    s = safe(lambda: api("GET", "/admin/stats", params={"days": days}), None)
    if s:
        c = st.columns(6)
        c[0].metric("Requests today", s["requests_today"])
        c[1].metric(f"Requests ({days}d)", s["requests"])
        c[2].metric("Active users", f"{s['active_users']} / {s['users_total']}")
        c[3].metric("Error rate", f"{s['error_rate']}%")
        c[4].metric("Avg / p95 latency", f"{s['avg_latency_ms'] / 1000:.1f}s / {s['p95_latency_ms'] / 1000:.1f}s")
        c[5].metric("Tokens", f"{s['tokens']:,}")
        if s["per_day"]:
            left, right = st.columns([2, 1])
            df = pd.DataFrame(s["per_day"])
            left.plotly_chart(px.bar(df, x="date", y="runs", color="agent", title="Requests per day by agent"),
                              use_container_width=True)
            pa = pd.DataFrame([{"agent": k, **v} for k, v in s["per_agent"].items()])
            right.plotly_chart(px.pie(pa, names="agent", values="runs", title="Routing share", hole=0.5),
                               use_container_width=True)
            l2, r2 = st.columns(2)
            pa["avg_latency_s"] = pa["avg_latency_ms"] / 1000
            l2.plotly_chart(px.bar(pa, x="agent", y="avg_latency_s", title="Average latency (s) by agent"),
                            use_container_width=True)
            if s["per_user"]:
                r2.plotly_chart(px.bar(pd.DataFrame(s["per_user"]).head(10), x="user", y="runs", title="Top users"),
                                use_container_width=True)
        else:
            st.info("No activity in this period yet.")

# ---------------- Agents ----------------
with tab_agents:
    agents = safe(lambda: api("GET", "/admin/agents"), [])
    for a in agents:
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
            c1.markdown(f"### {a['icon']} {a['label']}\n{a['summary']}")
            c1.caption(f"Model `{a['model']}`" + (f" · tools: {', '.join(a['tools'])}" if a["tools"] else ""))
            c2.metric("Runs (7d)", a["runs_7d"], delta=f"{a['errors_7d']} errors" if a["errors_7d"] else None,
                      delta_color="inverse")
            c3.metric("Avg latency", f"{a['avg_latency_ms'] / 1000:.1f}s")
            if a["name"] != "supervisor":
                new = c4.toggle("Enabled", value=a["enabled"], key=f"en-{a['name']}")
                if new != a["enabled"]:
                    safe(lambda: api("PATCH", f"/admin/agents/{a['name']}", json={"enabled": new}), None)
                    st.rerun()

# ---------------- Activity ----------------
with tab_activity:
    f1, f2, f3, f4 = st.columns(4)
    agent_f = f1.selectbox("Agent", ["", *AGENT_BADGES], format_func=lambda x: AGENT_BADGES.get(x, "All agents"))
    users_list = safe(lambda: api("GET", "/admin/users"), [])
    user_f = f2.selectbox("User", ["", *[u["username"] for u in users_list]], format_func=lambda x: x or "All users")
    status_f = f3.selectbox("Status", ["", "ok", "error", "refused"], format_func=lambda x: x or "All statuses")
    limit = f4.number_input("Rows", 10, 500, 100, step=10)
    runs = safe(lambda: api("GET", "/admin/runs", params={"agent": agent_f, "user": user_f, "status": status_f,
                                                          "limit": limit}), [])
    if runs:
        df = pd.DataFrame(runs)
        df["latency_s"] = df["latency_ms"] / 1000
        st.dataframe(df[["id", "created_at", "user", "agent", "status", "latency_s", "llm_calls", "tool_calls",
                         "tokens", "message"]], use_container_width=True, hide_index=True)
        pick = st.selectbox("Inspect run", [r["id"] for r in runs],
                            format_func=lambda i: next(f"#{r['id']} · {r['user']} · {r['agent']} · {r['message'][:60]}"
                                                       for r in runs if r["id"] == i))
        r = next(x for x in runs if x["id"] == pick)
        st.markdown(f"**Route reason:** {r['route_reason'] or '-'}")
        if r["error"]:
            st.error(r["error"])
        for n, step in enumerate(r["trace"] or [], 1):
            with st.expander(f"Step {n}: {step.get('action')}"):
                st.write(step.get("thought", ""))
                if step.get("args"):
                    st.json(step["args"])
    else:
        st.info("No runs match.")

# ---------------- Users ----------------
with tab_users:
    agent_names = [a for a in AGENT_BADGES if a != "supervisor"]
    if users_list:
        st.dataframe(pd.DataFrame(users_list)[["id", "username", "full_name", "role", "allowed_agents", "is_active",
                                               "jira_connected", "created_at"]], use_container_width=True, hide_index=True)
    left, right = st.columns(2)
    with left, st.form("new_user", clear_on_submit=True):
        st.subheader("Create user")
        nu = st.text_input("Username")
        nn = st.text_input("Full name")
        npw = st.text_input("Password", type="password")
        nr = st.selectbox("Role", ["user", "admin"])
        na = st.multiselect("Allowed assistants", agent_names, format_func=lambda x: AGENT_BADGES[x])
        if st.form_submit_button("Create", type="primary"):
            if safe(lambda: api("POST", "/admin/users", json={"username": nu, "full_name": nn, "password": npw,
                                                               "role": nr, "allowed_agents": na}), None):
                st.success(f"Created {nu}")
                st.rerun()
    with right:
        st.subheader("Edit user")
        if users_list:
            uid = st.selectbox("User", [u["id"] for u in users_list],
                               format_func=lambda i: next(u["username"] for u in users_list if u["id"] == i))
            u = next(x for x in users_list if x["id"] == uid)
            with st.form("edit_user"):
                er = st.selectbox("Role", ["user", "admin"], index=["user", "admin"].index(u["role"]))
                ea = st.multiselect("Allowed assistants", agent_names, default=[a for a in u["allowed_agents"] if a in agent_names],
                                    format_func=lambda x: AGENT_BADGES[x])
                eact = st.checkbox("Active", value=u["is_active"])
                epw = st.text_input("Reset password (optional)", type="password")
                if st.form_submit_button("Save"):
                    body = {"role": er, "allowed_agents": ea, "is_active": eact}
                    if epw:
                        body["password"] = epw
                    if safe(lambda: api("PATCH", f"/admin/users/{uid}", json=body), None):
                        st.success("Saved")
                        st.rerun()

# ---------------- Integrations ----------------
with tab_integrations:
    st.subheader("Jira connections")
    conns = safe(lambda: api("GET", "/admin/integrations"), [])
    if not conns:
        st.info("No users have connected Jira yet.")
    for c in conns:
        with st.container(border=True):
            a, b = st.columns([5, 1])
            a.markdown(f"**{c['user']}** → {c['site_url']} as {c['account']} · `{c['auth_type']}` · connected {c['connected_at']}")
            if b.button("Revoke", key=f"rv-{c['user_id']}"):
                safe(lambda: api("DELETE", f"/admin/integrations/jira/{c['user_id']}"), None)
                st.rerun()
    st.caption("The PM agent only reads Jira. To enable the one-click 'Connect Jira' button, set JIRA_OAUTH_CLIENT_ID / "
               "JIRA_OAUTH_CLIENT_SECRET in .env (see README).")
