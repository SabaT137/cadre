"""Startup tasks: create tables, first admin, agent settings, demo client, optional dev Jira connection."""
from __future__ import annotations

import asyncio
import logging

from sqlalchemy import func, select

from app.agents.registry import AGENTS
from app.auth.security import hash_password
from app.config import get_settings
from app.db.models import AgentSetting, Document, Invoice, User
from app.db.session import init_db, session_scope
from app.integrations.jira import store as jira_store
from app.services.invoice_store import seed_clients

log = logging.getLogger(__name__)


def ensure_admin() -> None:
    s = get_settings()
    with session_scope() as db:
        has_admin = db.scalar(select(func.count()).select_from(User).where(User.role == "admin"))
        if has_admin:
            return
        if not s.admin_password:
            log.warning("No admin user and ADMIN_PASSWORD is empty; skipping admin bootstrap.")
            return
        db.add(User(username=s.admin_username, full_name=s.admin_username.title(), password_hash=hash_password(s.admin_password),
                    role="admin", allowed_agents=list(AGENTS)))
        log.info("Created admin user %s", s.admin_username)


def ensure_agent_settings() -> None:
    with session_scope() as db:
        existing = {a.name for a in db.scalars(select(AgentSetting))}
        for name in AGENTS:
            if name not in existing:
                db.add(AgentSetting(name=name, enabled=True))


async def ensure_bootstrap_jira() -> None:
    s = get_settings()
    if not (s.jira_bootstrap_site and s.jira_bootstrap_email and s.jira_bootstrap_api_token):
        return
    with session_scope() as db:
        admin = db.scalar(select(User).where(User.username == s.admin_username))
        admin_id = admin.id if admin else None
    if admin_id is None or jira_store.get_connection(admin_id):
        return
    try:
        me = await jira_store.verify_api_token(s.jira_bootstrap_site, s.jira_bootstrap_email, s.jira_bootstrap_api_token)
    except Exception as e:
        log.warning("Bootstrap Jira connection failed: %s", e)
        return
    jira_store.save_connection(admin_id, auth_type="api_token", site_url=me["site_url"],
                               secret={"api_token": s.jira_bootstrap_api_token}, account_email=s.jira_bootstrap_email,
                               account_name=me.get("displayName", ""))
    log.info("Connected Jira %s for %s", me["site_url"], s.admin_username)


def backfill_invoice_documents() -> None:
    """Invoices created before the documents table existed become documents of their creator."""
    with session_scope() as db:
        for inv in db.scalars(select(Invoice)):
            if db.get(Document, inv.file_id) is None:
                db.add(Document(file_id=inv.file_id, user_id=inv.created_by, agent="finance", kind="invoice",
                                filename=f"{inv.invoice_no}.pdf", mime="application/pdf", created_at=inv.created_at))


async def bootstrap() -> None:
    init_db()
    ensure_admin()
    ensure_agent_settings()
    seed_clients()
    backfill_invoice_documents()
    await ensure_bootstrap_jira()


if __name__ == "__main__":
    asyncio.run(bootstrap())
