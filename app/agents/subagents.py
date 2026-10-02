"""Department sub-agent nodes. Each returns only its final reply + artifacts to the shared thread."""
from __future__ import annotations

from langchain_core.messages import AIMessage, SystemMessage

from app.agents.context import RunUser, current_run_user
from app.agents.json_react import AgentRun, _history, run_json_react, run_native_agent
from app.config import get_settings
from app.graph.state import OfficeState
from app.integrations.jira.store import describe_connection
from app.llm import get_worker_llm
from app.prompts import developer_prompt, devops_prompt, finance_prompt, hr_prompt, pm_prompt
from app.services import db
from app.services.invoice_pdf import load_finance_config
from app.tools.finance_tools import FINANCE_TOOLS, bank_accounts_text
from app.tools.hr_tools import HR_TOOLS
from app.tools.pm_tools import PM_TOOLS
from app.tools.sql_tools import DEVOPS_TOOLS

HISTORY_WINDOW = 20


async def _run_tool_agent(tools, system_prompt: str, state: OfficeState, temperature: float,
                          max_steps: int = 8) -> AgentRun:
    llm = get_worker_llm(temperature)
    runner = run_native_agent if get_settings().worker_native_tools else run_json_react
    token = current_run_user.set(RunUser(state.get("user_id") or 0, state.get("username") or ""))
    try:
        return await runner(llm, tools, system_prompt, state["messages"][-HISTORY_WINDOW:], max_steps=max_steps)
    finally:
        current_run_user.reset(token)


def _result(name: str, run: AgentRun, artifacts: list[dict] | None = None) -> dict:
    artifacts = run.artifacts if artifacts is None else artifacts
    return {
        # Artifacts ride along on the message so thread history can re-render downloads and tables.
        "messages": [AIMessage(run.answer, name=name, additional_kwargs={"artifacts": artifacts})],
        "artifacts": artifacts,
        "trace": run.steps,
        "active_agent": name,
    }


async def hr_node(state: OfficeState) -> dict:
    run = await _run_tool_agent(HR_TOOLS, hr_prompt(state.get("attached_template_id")), state, 0.3)
    return _result("hr", run)


async def devops_node(state: OfficeState) -> dict:
    run = await _run_tool_agent(DEVOPS_TOOLS, devops_prompt(db.dialect_name()), state, 0.0)
    # Earlier queries are usually exploration or failed attempts; the UI only needs the final result.
    return _result("devops", run, run.artifacts[-1:])


async def finance_node(state: OfficeState) -> dict:
    cfg = load_finance_config()
    prompt = finance_prompt(bank_accounts_text(), cfg["invoice"]["default_currency"])
    run = await _run_tool_agent(FINANCE_TOOLS, prompt, state, 0.1)
    return _result("finance", run)


async def pm_node(state: OfficeState) -> dict:
    prompt = pm_prompt(describe_connection(state.get("user_id") or 0))
    run = await _run_tool_agent(PM_TOOLS, prompt, state, 0.2, max_steps=10)
    return _result("pm", run)


async def developer_node(state: OfficeState) -> dict:
    llm = get_worker_llm(0.7)
    resp = await llm.ainvoke([SystemMessage(developer_prompt()), *_history(state["messages"][-HISTORY_WINDOW:])])
    return {"messages": [AIMessage(resp.content, name="developer")], "artifacts": [], "trace": [],
            "active_agent": "developer"}
