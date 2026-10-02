from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.agents.registry import AGENTS
from app.auth.deps import CurrentUser, require_admin
from app.auth.security import hash_password
from app.config import get_settings
from app.db.models import AgentSetting, JiraConnection, User
from app.db.session import session_scope
from app.integrations.jira.store import delete_connection
from app.services import usage

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/stats")
def stats(days: int = 7):
    return usage.stats(max(1, min(days, 90)))


@router.get("/runs")
def runs(agent: str = "", user: str = "", status: str = "", limit: int = 100):
    return usage.recent_runs(agent, user, status, max(1, min(limit, 500)))


@router.get("/agents")
def agents():
    s = get_settings()
    enabled = usage.enabled_agents()
    per_agent = usage.stats(7)["per_agent"]
    return [{
        "name": a.name, "label": a.label, "icon": a.icon, "summary": a.summary, "enabled": enabled.get(a.name, True),
        "model": s.worker_model, "tools": [t.name for t in a.tools],
        "runs_7d": per_agent.get(a.name, {}).get("runs", 0),
        "errors_7d": per_agent.get(a.name, {}).get("errors", 0),
        "avg_latency_ms": per_agent.get(a.name, {}).get("avg_latency_ms", 0),
    } for a in AGENTS.values()] + [{
        "name": "supervisor", "label": "Supervisor", "icon": "🧭", "summary": "Routes each message to a department.",
        "enabled": True, "model": s.supervisor_model, "tools": [], "runs_7d": per_agent.get("supervisor", {}).get("runs", 0),
        "errors_7d": per_agent.get("supervisor", {}).get("errors", 0),
        "avg_latency_ms": per_agent.get("supervisor", {}).get("avg_latency_ms", 0),
    }]


class AgentPatch(BaseModel):
    enabled: bool


@router.patch("/agents/{name}")
def patch_agent(name: str, body: AgentPatch):
    if name not in AGENTS:
        raise HTTPException(404, "Unknown agent")
    with session_scope() as s:
        setting = s.get(AgentSetting, name) or AgentSetting(name=name)
        setting.enabled = body.enabled
        s.merge(setting)
    return {"name": name, "enabled": body.enabled}


class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(min_length=4)
    full_name: str = ""
    role: str = Field(default="user", pattern="^(admin|user)$")
    allowed_agents: list[str] = []


class UserPatch(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = Field(default=None, pattern="^(admin|user)$")
    allowed_agents: Optional[list[str]] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(default=None, min_length=4)


def _user_dict(u: User, jira: set[int]) -> dict:
    return {"id": u.id, "username": u.username, "full_name": u.full_name, "role": u.role,
            "allowed_agents": u.allowed_agents, "is_active": u.is_active, "jira_connected": u.id in jira,
            "created_at": u.created_at.isoformat(timespec="seconds")}


@router.get("/users")
def list_users():
    with session_scope() as s:
        jira = {c.user_id for c in s.scalars(select(JiraConnection))}
        return [_user_dict(u, jira) for u in s.scalars(select(User).order_by(User.id))]


@router.post("/users", status_code=201)
def create_user(body: UserCreate):
    bad = [a for a in body.allowed_agents if a not in AGENTS]
    if bad:
        raise HTTPException(400, f"Unknown agents: {bad}")
    with session_scope() as s:
        if s.scalar(select(User).where(User.username == body.username.lower())):
            raise HTTPException(409, "Username already exists")
        u = User(username=body.username.lower(), full_name=body.full_name, role=body.role,
                 password_hash=hash_password(body.password), allowed_agents=body.allowed_agents)
        s.add(u)
        s.flush()
        return _user_dict(u, set())


@router.patch("/users/{user_id}")
def update_user(user_id: int, body: UserPatch, admin: CurrentUser = Depends(require_admin)):
    with session_scope() as s:
        u = s.get(User, user_id)
        if u is None:
            raise HTTPException(404, "Unknown user")
        if u.id == admin.id and (body.is_active is False or body.role == "user"):
            raise HTTPException(400, "You can't deactivate or demote yourself")
        if body.allowed_agents is not None:
            bad = [a for a in body.allowed_agents if a not in AGENTS]
            if bad:
                raise HTTPException(400, f"Unknown agents: {bad}")
            u.allowed_agents = body.allowed_agents
        for f in ("full_name", "role", "is_active"):
            if getattr(body, f) is not None:
                setattr(u, f, getattr(body, f))
        if body.password:
            u.password_hash = hash_password(body.password)
        jira = {c.user_id for c in s.scalars(select(JiraConnection))}
        return _user_dict(u, jira)


@router.get("/integrations")
def integrations():
    with session_scope() as s:
        rows = s.execute(select(JiraConnection, User.username).join(User, User.id == JiraConnection.user_id))
        return [{"user_id": c.user_id, "user": name, "auth_type": c.auth_type, "site_url": c.site_url,
                 "account": c.account_name or c.account_email, "connected_at": c.connected_at.isoformat(timespec="seconds"),
                 "expires_at": c.expires_at.isoformat(timespec="seconds") if c.expires_at else None} for c, name in rows]


@router.delete("/integrations/jira/{user_id}")
def revoke_jira(user_id: int):
    if not delete_connection(user_id):
        raise HTTPException(404, "No Jira connection for that user")
    return {"revoked": True}
