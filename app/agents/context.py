"""Per-request user context visible to tools (works for both the JSON loop and native tool calling)."""
from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass


@dataclass(frozen=True)
class RunUser:
    id: int
    username: str


current_run_user: ContextVar[RunUser | None] = ContextVar("current_run_user", default=None)


def require_run_user() -> RunUser:
    user = current_run_user.get()
    if user is None:
        raise RuntimeError("No user in context for this tool call")
    return user
