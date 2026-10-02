import json
import logging
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.registry import AGENTS
from app.api.routes.auth import _available
from app.api.schemas import ChatRequest, ChatResponse, HistoryMessage, ThreadHistory
from app.auth.deps import CurrentUser, current_user
from app.services import usage
from app.services.template_store import get_store

router = APIRouter(tags=["chat"])
log = logging.getLogger(__name__)


def _check_thread(thread_id: str, user: CurrentUser) -> None:
    owner = usage.thread_owner(thread_id)
    if owner is not None and owner != user.id:
        raise HTTPException(404, "Unknown thread")


def _inputs(req: ChatRequest, user: CurrentUser, usage_cb) -> tuple[dict, dict, str]:
    if req.template_id:
        try:
            get_store().template_path(req.template_id)
        except KeyError as e:
            raise HTTPException(404, str(e))
    thread_id = req.thread_id or uuid.uuid4().hex
    _check_thread(thread_id, user)
    inputs = {
        "messages": [HumanMessage(req.message)],
        "department_hint": None if req.department == "auto" else req.department,
        "attached_template_id": req.template_id,
        "available_agents": _available(user),
        "user_id": user.id,
        "username": user.username,
    }
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 25, "callbacks": [usage_cb]}
    return inputs, config, thread_id


def _agent_name(route: str | None) -> str:
    return route if route in AGENTS else "supervisor"


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request, user: CurrentUser = Depends(current_user)) -> ChatResponse:
    graph = request.app.state.graph
    cb = usage.UsageCallbackHandler()
    inputs, config, thread_id = _inputs(req, user, cb)
    usage.touch_thread(thread_id, user.id, req.message)
    started = time.perf_counter()
    try:
        state = await graph.ainvoke(inputs, config)
    except Exception as e:
        log.exception("Graph failed")
        usage.record_run(user_id=user.id, thread_id=thread_id, agent="unknown", route_reason="", status="error",
                         latency_ms=int((time.perf_counter() - started) * 1000), usage=cb, message=req.message,
                         trace=[], error=f"{e.__class__.__name__}: {e}")
        raise HTTPException(502, f"Agent error: {e.__class__.__name__}: {e}")
    route = state.get("route")
    usage.record_run(user_id=user.id, thread_id=thread_id, agent=_agent_name(route), route_reason=state.get("route_reason") or "",
                     status="refused" if route == "refused" else "ok",
                     latency_ms=int((time.perf_counter() - started) * 1000), usage=cb, message=req.message,
                     trace=state.get("trace") or [])
    usage.record_documents(user.id, thread_id, _agent_name(route), state.get("artifacts") or [])
    last = state["messages"][-1]
    return ChatResponse(
        thread_id=thread_id,
        reply=last.content if isinstance(last, AIMessage) else "",
        agent=_agent_name(route),
        route_reason=state.get("route_reason"),
        artifacts=state.get("artifacts") or [],
    )


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest, request: Request, user: CurrentUser = Depends(current_user)) -> StreamingResponse:
    """Server-sent events: `route` once the supervisor decides, then `message` with the reply and artifacts."""
    graph = request.app.state.graph
    cb = usage.UsageCallbackHandler()
    inputs, config, thread_id = _inputs(req, user, cb)
    usage.touch_thread(thread_id, user.id, req.message)

    async def events():
        def sse(event: str, data: dict) -> str:
            return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"

        started = time.perf_counter()
        route, reason, trace, error = None, "", [], ""
        yield sse("thread", {"thread_id": thread_id})
        try:
            async for update in graph.astream(inputs, config, stream_mode="updates"):
                for node, delta in update.items():
                    if not delta:
                        continue
                    if node == "supervisor":
                        route, reason = delta.get("route"), delta.get("route_reason") or ""
                        yield sse("route", {"agent": _agent_name(route), "reason": reason})
                    trace = delta.get("trace") or trace
                    msgs = delta.get("messages") or []
                    if delta.get("artifacts"):
                        usage.record_documents(user.id, thread_id, node, delta["artifacts"])
                    if msgs:
                        yield sse("message", {"agent": node, "content": msgs[-1].content,
                                              "artifacts": delta.get("artifacts") or []})
        except Exception as e:
            log.exception("Graph failed")
            error = f"{e.__class__.__name__}: {e}"
            yield sse("error", {"detail": error})
        usage.record_run(user_id=user.id, thread_id=thread_id, agent=_agent_name(route), route_reason=reason,
                         status="error" if error else ("refused" if route == "refused" else "ok"),
                         latency_ms=int((time.perf_counter() - started) * 1000), usage=cb, message=req.message,
                         trace=trace, error=error)
        yield sse("done", {})

    return StreamingResponse(events(), media_type="text/event-stream")


@router.get("/threads")
def my_threads(limit: int = 30, user: CurrentUser = Depends(current_user)):
    return usage.list_threads(user.id, max(1, min(limit, 200)))


@router.get("/activity")
def my_activity(limit: int = 50, user: CurrentUser = Depends(current_user)):
    """The current user's own recent runs (admins use /admin/runs for everyone)."""
    return usage.recent_runs(user=user.username, limit=max(1, min(limit, 200)))


@router.get("/documents")
def my_documents(scope: str = "mine", limit: int = 100, user: CurrentUser = Depends(current_user)):
    """Files the agents generated for me. Admins may pass scope=all."""
    everyone = scope == "all" and user.is_admin
    return usage.list_documents(None if everyone else user.id, max(1, min(limit, 500)))


@router.get("/threads/{thread_id}", response_model=ThreadHistory)
async def thread_history(thread_id: str, request: Request, user: CurrentUser = Depends(current_user)) -> ThreadHistory:
    if usage.thread_owner(thread_id) != user.id:
        raise HTTPException(404, "Unknown thread")
    snapshot = await request.app.state.graph.aget_state({"configurable": {"thread_id": thread_id}})
    out = []
    for m in (snapshot.values or {}).get("messages", []):
        if isinstance(m, HumanMessage):
            out.append(HistoryMessage(role="user", content=str(m.content)))
        elif isinstance(m, AIMessage):
            out.append(HistoryMessage(role="assistant", content=str(m.content), agent=m.name,
                                      artifacts=m.additional_kwargs.get("artifacts", [])))
    return ThreadHistory(thread_id=thread_id, messages=out)
