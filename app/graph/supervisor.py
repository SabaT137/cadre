from __future__ import annotations

import json
import logging

from langchain_core.messages import AIMessage, SystemMessage

from app.agents.json_react import _history
from app.agents.registry import AGENTS
from app.graph.state import OfficeState
from app.llm import get_supervisor_llm
from app.prompts import SUPERVISOR_REPLY_FALLBACK, supervisor_prompt

log = logging.getLogger(__name__)
ROUTER_WINDOW = 6


def _route_schema(options: list[str]) -> dict:
    return {
        "type": "object",
        "properties": {
            "next": {"type": "string", "enum": options},
            "reason": {"type": "string", "description": "One short sentence explaining the choice."},
            "reply": {"type": "string", "description": "Only for respond/refused: the reply to the user."},
        },
        "required": ["next", "reason"],
    }


async def supervisor_node(state: OfficeState) -> dict:
    available = [a for a in state.get("available_agents") or list(AGENTS) if a in AGENTS]
    unavailable = [a for a in AGENTS if a not in available]
    hint = state.get("department_hint")
    base = {"artifacts": [], "trace": []}

    if hint:
        if hint in available:
            return {**base, "route": hint, "route_reason": f"Department '{hint}' selected in the UI."}
        reply = f"You don't have access to the {AGENTS[hint].label if hint in AGENTS else hint} assistant. Please ask an admin."
        return {**base, "route": "refused", "route_reason": "Selected department not permitted.",
                "messages": [AIMessage(reply, name="supervisor")]}

    options = [*available, "respond"] + (["refused"] if unavailable else [])
    # JSON-schema output rather than tool calling: on this gateway GLM's forced tool call intermittently
    # comes back empty (consistently for e.g. "delete ..." requests), while guided JSON is reliable.
    llm = get_supervisor_llm().bind(
        response_format={"type": "json_schema", "json_schema": {"name": "Route", "schema": _route_schema(options)}}
    )
    prompt = supervisor_prompt(
        {a: AGENTS[a].description for a in available},
        {a: AGENTS[a].description for a in unavailable},
        state.get("active_agent") if state.get("active_agent") in available else None,
    )
    msgs = [SystemMessage(prompt), *_history(state["messages"][-ROUTER_WINDOW:])]
    route = None
    for attempt in range(2):
        try:
            resp = await llm.ainvoke(msgs)
            data = json.loads(str(resp.content))
            if data.get("next") in options:
                route = data
                break
            log.warning("Supervisor chose invalid option %r", data.get("next"))
        except Exception:
            log.exception("Supervisor routing failed (attempt %d)", attempt + 1)
    if route is None:
        fallback = state.get("active_agent") if state.get("active_agent") in available else (available or ["respond"])[0]
        return {**base, "route": fallback, "route_reason": "Router unavailable; used fallback."}

    update = {**base, "route": route["next"], "route_reason": route.get("reason", "")}
    if route["next"] in ("respond", "refused"):
        update["messages"] = [AIMessage((route.get("reply") or "").strip() or SUPERVISOR_REPLY_FALLBACK, name="supervisor")]
    return update


def route_after_supervisor(state: OfficeState) -> str:
    return state["route"] if state.get("route") in AGENTS else "__end__"
