from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.agents.registry import AGENTS
from app.auth.deps import CurrentUser, current_user
from app.auth.security import create_token, verify_password
from app.db.models import User
from app.db.session import session_scope
from app.services.usage import enabled_agents

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


def _available(user: CurrentUser) -> list[str]:
    enabled = enabled_agents()
    allowed = list(AGENTS) if user.is_admin else list(user.allowed_agents)
    return [a for a in AGENTS if a in allowed and enabled.get(a, True)]


def user_payload(user: CurrentUser) -> dict:
    return {
        "id": user.id, "username": user.username, "full_name": user.full_name, "role": user.role,
        "allowed_agents": list(user.allowed_agents),
        "available_agents": [{"name": a, "label": AGENTS[a].label, "icon": AGENTS[a].icon, "summary": AGENTS[a].summary}
                             for a in _available(user)],
    }


@router.post("/login")
def login(req: LoginRequest):
    with session_scope() as s:
        user = s.scalar(select(User).where(User.username == req.username.strip().lower()))
        if user is None or not user.is_active or not verify_password(req.password, user.password_hash):
            raise HTTPException(401, "Invalid username or password")
        cu = CurrentUser(user.id, user.username, user.full_name, user.role, tuple(user.allowed_agents or []))
    return {"access_token": create_token(str(cu.id)), "token_type": "bearer", "user": user_payload(cu)}


@router.get("/me")
def me(user: CurrentUser = Depends(current_user)):
    return user_payload(user)
