import asyncio
import json

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool

from app.agents.json_react import run_json_react
from app.graph.supervisor import route_after_supervisor, supervisor_node


@tool(response_format="content_and_artifact")
def add(a: int, b: int) -> tuple[str, dict]:
    """Add two numbers."""
    return str(a + b), {"type": "sum", "value": a + b}


def _step(action, args=None, answer=""):
    return AIMessage(json.dumps({"thought": "t", "action": action, "args": args or {}, "answer": answer}))


def test_json_react_tool_then_answer():
    llm = GenericFakeChatModel(messages=iter([_step("add", {"a": 2, "b": 3}), _step("final_answer", answer="It is 5.")]))
    run = asyncio.run(run_json_react(llm, [add], "You add.", [HumanMessage("2+3?")]))
    assert run.answer == "It is 5."
    assert run.artifacts == [{"type": "sum", "value": 5}]
    assert [s["action"] for s in run.steps] == ["add", "final_answer"]


def test_json_react_recovers_from_bad_json_and_bad_args():
    llm = GenericFakeChatModel(messages=iter([
        AIMessage("not json"),
        _step("add", {"a": "x"}),  # invalid args -> error observation
        _step("final_answer", answer="done"),
    ]))
    run = asyncio.run(run_json_react(llm, [add], "You add.", [HumanMessage("hi")]))
    assert run.answer == "done"


def test_department_hint_skips_llm():
    state = {"messages": [HumanMessage("anything")], "department_hint": "devops"}
    update = asyncio.run(supervisor_node(state))
    assert update["route"] == "devops"
    assert route_after_supervisor({**state, **update}) == "devops"


def test_respond_route_ends():
    assert route_after_supervisor({"route": "respond"}) == "__end__"
