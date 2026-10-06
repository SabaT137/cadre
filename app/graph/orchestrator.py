"""Multi-agent turn: run the supervisor's plan across several department agents in parallel,
then have the supervisor model combine their results into a single reply."""
from __future__ import annotations

import asyncio
import logging

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.agents.registry import AGENTS
from app.graph.state import OfficeState
from app.llm import get_worker_llm
from app.prompts import synthesis_prompt

log = logging.getLogger(__name__)
HISTORY_FOR_PARTS = 6


def _writer():
    """LangGraph custom-stream writer (progress events for the UI); a no-op outside a streaming run."""
    try:
        from langgraph.config import get_stream_writer

        return get_stream_writer()
    except Exception:
        return lambda _event: None


async def _run_part(state: OfficeState, part: dict, original: str, emit) -> dict:
    agent = part["agent"]
    emit({"type": "part", "agent": agent, "status": "started", "task": part["instruction"]})
    task = (
        f"{part['instruction']}\n\n"
        f"(This is one part of a larger request handled by several departments: \"{original}\". "
        f"Only do your department's part.)"
    )
    sub_state = {
        **state,
        "messages": [*state["messages"][:-1][-HISTORY_FOR_PARTS:], HumanMessage(task)],
        "department_hint": agent,
    }
    try:
        result = await AGENTS[agent].node(sub_state)
        msg = result["messages"][-1]
        out = {
            "agent": agent,
            "task": part["instruction"],
            "answer": str(msg.content),
            "artifacts": [{**a, "agent": agent} for a in result.get("artifacts") or []],
            "trace": [{**step, "agent": agent} for step in result.get("trace") or []],
            "ok": True,
        }
    except Exception as e:  # one failing department must not sink the whole answer
        log.exception("Multi-agent part %s failed", agent)
        out = {"agent": agent, "task": part["instruction"], "answer": f"This part failed: {e.__class__.__name__}.",
               "artifacts": [], "trace": [], "ok": False}
    emit({"type": "part", "agent": agent, "status": "done" if out["ok"] else "error"})
    return out


async def multi_node(state: OfficeState) -> dict:
    plan = state.get("plan") or []
    original = str(state["messages"][-1].content)
    emit = _writer()
    results = await asyncio.gather(*[_run_part(state, part, original, emit) for part in plan])

    emit({"type": "synthesis", "status": "started"})
    sections = "\n\n".join(
        f"## {AGENTS[r['agent']].label} agent\nTask: {r['task']}\nResult:\n{r['answer']}"
        + (f"\nAttached files/tables: {', '.join(a.get('filename') or a.get('title') or a['type'] for a in r['artifacts'])}"
           if r["artifacts"] else "")
        for r in results
    )
    try:
        # Qwen writes ~4x faster than GLM on this gateway; GLM keeps the (short) planning step.
        resp = await get_worker_llm(0.2).ainvoke([
            SystemMessage(synthesis_prompt()),
            HumanMessage(f"User request:\n{original}\n\nDepartment results:\n\n{sections}"),
        ])
        reply = str(resp.content).strip()
    except Exception:
        log.exception("Synthesis failed; falling back to concatenated results")
        reply = ""
    if not reply:
        reply = "\n\n".join(f"### {AGENTS[r['agent']].label}\n{r['answer']}" for r in results)

    artifacts = [a for r in results for a in r["artifacts"]]
    parts = [{"agent": r["agent"], "task": r["task"], "ok": r["ok"]} for r in results]
    return {
        "messages": [AIMessage(reply, name="multi", additional_kwargs={"artifacts": artifacts, "parts": parts})],
        "artifacts": artifacts,
        "trace": [step for r in results for step in r["trace"]],
        "active_agent": None,  # follow-ups get routed afresh
    }
