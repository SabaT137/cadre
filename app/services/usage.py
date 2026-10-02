"""Run tracking (LLM usage callback + agent_runs table) and admin statistics."""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.outputs import LLMResult
from sqlalchemy import func, select

from app.db.models import AgentRun, AgentSetting, Document, Invoice, Thread, User, utcnow
from app.db.session import session_scope

log = logging.getLogger(__name__)


class UsageCallbackHandler(AsyncCallbackHandler):
    def __init__(self) -> None:
        self.llm_calls = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0

    async def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        self.llm_calls += 1
        for gens in response.generations:
            for g in gens:
                usage = getattr(getattr(g, "message", None), "usage_metadata", None) or {}
                self.prompt_tokens += int(usage.get("input_tokens", 0))
                self.completion_tokens += int(usage.get("output_tokens", 0))


def record_run(*, user_id: int, thread_id: str, agent: str, route_reason: str, status: str, latency_ms: int,
               usage: UsageCallbackHandler, message: str, trace: list[dict], error: str = "") -> None:
    try:
        with session_scope() as s:
            s.add(AgentRun(
                user_id=user_id, thread_id=thread_id, agent=agent, route_reason=route_reason or "", status=status,
                latency_ms=latency_ms, llm_calls=usage.llm_calls,
                tool_calls=sum(1 for st in trace if st.get("action") not in (None, "final_answer")),
                prompt_tokens=usage.prompt_tokens, completion_tokens=usage.completion_tokens,
                message=message[:2000], trace=trace, error=error[:2000],
            ))
    except Exception:
        log.exception("Failed to record run")


def touch_thread(thread_id: str, user_id: int, first_message: str) -> None:
    with session_scope() as s:
        t = s.get(Thread, thread_id)
        if t is None:
            s.add(Thread(thread_id=thread_id, user_id=user_id, title=first_message[:80]))
        else:
            t.updated_at = utcnow()


def thread_owner(thread_id: str) -> int | None:
    with session_scope() as s:
        t = s.get(Thread, thread_id)
        return t.user_id if t else None


def list_threads(user_id: int, limit: int = 30) -> list[dict]:
    with session_scope() as s:
        threads = list(s.scalars(select(Thread).where(Thread.user_id == user_id).order_by(Thread.updated_at.desc()).limit(limit)))
        ids = [t.thread_id for t in threads]
        last_agent: dict[str, str] = {}
        counts: dict[str, int] = defaultdict(int)
        if ids:
            for r in s.scalars(select(AgentRun).where(AgentRun.thread_id.in_(ids)).order_by(AgentRun.id)):
                counts[r.thread_id] += 1
                if r.agent not in ("supervisor", "unknown"):
                    last_agent[r.thread_id] = r.agent
        return [{"thread_id": t.thread_id, "title": t.title, "updated_at": t.updated_at.isoformat(),
                 "created_at": t.created_at.isoformat(), "agent": last_agent.get(t.thread_id),
                 "turns": counts.get(t.thread_id, 0)} for t in threads]


def _doc_kind(agent: str, filename: str) -> str:
    if agent == "finance" or filename.lower().endswith(".pdf"):
        return "invoice"
    if agent == "hr" or filename.lower().endswith(".docx"):
        return "contract"
    if agent == "pm":
        return "plan"
    return "file"


def record_documents(user_id: int, thread_id: str, agent: str, artifacts: list[dict]) -> None:
    files = [a for a in artifacts or [] if a.get("type") == "file" and a.get("file_id")]
    if not files:
        return
    try:
        with session_scope() as s:
            for a in files:
                if s.get(Document, a["file_id"]) is None:
                    s.add(Document(file_id=a["file_id"], user_id=user_id, thread_id=thread_id, agent=agent,
                                   filename=a.get("filename", a["file_id"]), mime=a.get("mime", ""),
                                   kind=_doc_kind(agent, a.get("filename", ""))))
    except Exception:
        log.exception("Failed to record documents")


def list_documents(user_id: int | None, limit: int = 100) -> list[dict]:
    """Documents for one user, or for everyone when user_id is None (admin)."""
    with session_scope() as s:
        stmt = select(Document, User.username).join(User, User.id == Document.user_id).order_by(Document.created_at.desc()).limit(limit)
        if user_id is not None:
            stmt = stmt.where(Document.user_id == user_id)
        return [{"file_id": d.file_id, "filename": d.filename, "mime": d.mime, "kind": d.kind, "agent": d.agent,
                 "thread_id": d.thread_id, "owner": uname, "created_at": d.created_at.isoformat(timespec="seconds")}
                for d, uname in s.execute(stmt)]


def can_access_file(file_id: str, user_id: int, is_admin: bool, allowed_agents: tuple[str, ...]) -> bool:
    if is_admin:
        return True
    with session_scope() as s:
        doc = s.get(Document, file_id)
        if doc is not None and doc.user_id == user_id:
            return True
        # Invoices are shared within Finance.
        if "finance" in allowed_agents and s.scalar(select(Invoice.id).where(Invoice.file_id == file_id)):
            return True
    return False


def enabled_agents() -> dict[str, bool]:
    with session_scope() as s:
        return {a.name: a.enabled for a in s.scalars(select(AgentSetting))}


def _pct(values: list[int], p: float) -> int:
    if not values:
        return 0
    values = sorted(values)
    return values[min(len(values) - 1, int(round(p * (len(values) - 1))))]


def stats(days: int = 7) -> dict:
    since = utcnow() - timedelta(days=days)
    today = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    with session_scope() as s:
        runs = list(s.scalars(select(AgentRun).where(AgentRun.created_at >= since)))
        users_total = s.scalar(select(func.count()).select_from(User).where(User.is_active.is_(True)))
        names = dict(s.execute(select(User.id, User.username)).all())
    per_agent: dict[str, dict] = defaultdict(lambda: {"runs": 0, "errors": 0, "latencies": [], "tokens": 0})
    per_day: dict[tuple[str, str], int] = defaultdict(int)
    per_user: dict[str, int] = defaultdict(int)
    for r in runs:
        a = per_agent[r.agent]
        a["runs"] += 1
        a["errors"] += r.status == "error"
        a["latencies"].append(r.latency_ms)
        a["tokens"] += r.prompt_tokens + r.completion_tokens
        per_day[(r.created_at.date().isoformat(), r.agent)] += 1
        per_user[names.get(r.user_id, str(r.user_id))] += 1
    lat = [r.latency_ms for r in runs]
    return {
        "days": days,
        "requests": len(runs),
        "requests_today": sum(1 for r in runs if r.created_at >= today),
        "active_users": len({r.user_id for r in runs}),
        "users_total": users_total,
        "error_rate": round(100 * sum(r.status == "error" for r in runs) / len(runs), 1) if runs else 0.0,
        "refused": sum(r.status == "refused" for r in runs),
        "avg_latency_ms": int(sum(lat) / len(lat)) if lat else 0,
        "p95_latency_ms": _pct(lat, 0.95),
        "tokens": sum(r.prompt_tokens + r.completion_tokens for r in runs),
        "per_agent": {k: {"runs": v["runs"], "errors": v["errors"], "tokens": v["tokens"],
                          "avg_latency_ms": int(sum(v["latencies"]) / len(v["latencies"])) if v["latencies"] else 0,
                          "p95_latency_ms": _pct(v["latencies"], 0.95)} for k, v in per_agent.items()},
        "per_day": [{"date": d, "agent": a, "runs": n} for (d, a), n in sorted(per_day.items())],
        "per_user": [{"user": u, "runs": n} for u, n in sorted(per_user.items(), key=lambda kv: -kv[1])],
    }


def recent_runs(agent: str = "", user: str = "", status: str = "", limit: int = 100) -> list[dict]:
    with session_scope() as s:
        stmt = select(AgentRun, User.username).join(User, User.id == AgentRun.user_id).order_by(AgentRun.id.desc()).limit(limit)
        if agent:
            stmt = stmt.where(AgentRun.agent == agent)
        if user:
            stmt = stmt.where(User.username == user)
        if status:
            stmt = stmt.where(AgentRun.status == status)
        return [{
            "id": r.id, "created_at": r.created_at.isoformat(timespec="seconds"), "user": uname, "agent": r.agent,
            "status": r.status, "latency_ms": r.latency_ms, "llm_calls": r.llm_calls, "tool_calls": r.tool_calls,
            "tokens": r.prompt_tokens + r.completion_tokens, "message": r.message, "route_reason": r.route_reason,
            "trace": r.trace, "error": r.error, "thread_id": r.thread_id,
        } for r, uname in s.execute(stmt)]
