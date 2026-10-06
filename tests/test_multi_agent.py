import asyncio
import dataclasses

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, HumanMessage

from app.agents import registry
from app.graph import orchestrator
from app.graph.supervisor import _clean_plan, route_after_supervisor


def test_clean_plan_filters_and_caps():
    tasks = [
        {"agent": "hr", "instruction": "Draft contract"},
        {"agent": "hr", "instruction": "duplicate"},
        {"agent": "finance", "instruction": "not allowed"},
        {"agent": "devops", "instruction": ""},
        {"agent": "devops", "instruction": "Find laptop"},
        {"agent": "pm", "instruction": "Check Jira"},
        {"agent": "developer", "instruction": "over the cap"},
    ]
    plan = _clean_plan(tasks, ["hr", "devops", "pm", "developer"])
    assert [p["agent"] for p in plan] == ["hr", "devops", "pm"]


def test_route_after_supervisor_multi():
    assert route_after_supervisor({"route": "multi", "plan": [{"agent": "hr"}, {"agent": "pm"}]}) == "multi"
    assert route_after_supervisor({"route": "multi", "plan": []}) == "__end__"
    assert route_after_supervisor({"route": "hr"}) == "hr"


def test_multi_node_runs_parts_and_synthesises(monkeypatch):
    seen: dict[str, str] = {}

    def fake_node(name, artifacts):
        async def node(state):
            seen[name] = state["messages"][-1].content
            return {"messages": [AIMessage(f"{name} result")], "artifacts": artifacts,
                    "trace": [{"action": "tool_x", "thought": "", "args": {}}]}
        return node

    async def broken(state):
        raise RuntimeError("boom")

    patched = dict(registry.AGENTS)
    patched["hr"] = dataclasses.replace(patched["hr"], node=fake_node("hr", [{"type": "file", "file_id": "c1", "filename": "c.docx"}]))
    patched["devops"] = dataclasses.replace(patched["devops"], node=fake_node("devops", []))
    patched["pm"] = dataclasses.replace(patched["pm"], node=broken)
    monkeypatch.setattr(orchestrator, "AGENTS", patched)
    monkeypatch.setattr(orchestrator, "get_worker_llm",
                        lambda *a, **k: GenericFakeChatModel(messages=iter([AIMessage("Combined answer")])))

    state = {
        "messages": [HumanMessage("Onboard Ali: contract, laptop, Jira")],
        "plan": [{"agent": "hr", "instruction": "Draft contract"},
                 {"agent": "devops", "instruction": "Find laptop"},
                 {"agent": "pm", "instruction": "Check Jira"}],
        "user_id": 1, "username": "t",
    }
    out = asyncio.run(orchestrator.multi_node(state))
    msg = out["messages"][0]
    assert msg.content == "Combined answer" and msg.name == "multi"
    assert [p["agent"] for p in msg.additional_kwargs["parts"]] == ["hr", "devops", "pm"]
    assert msg.additional_kwargs["parts"][2]["ok"] is False  # failure isolated
    assert out["artifacts"] == [{"type": "file", "file_id": "c1", "filename": "c.docx", "agent": "hr"}]
    assert {s["agent"] for s in out["trace"]} == {"hr", "devops"}
    assert seen["hr"].startswith("Draft contract") and "Onboard Ali" in seen["hr"]
