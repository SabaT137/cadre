"""A ReAct loop driven by JSON-schema constrained output.

The worker model on our gateway has no native tool calling (vLLM without --tool-call-parser),
but it does support `response_format: json_schema`. Each step the model emits
{"thought", "action", "args", "answer"}; we execute the named tool and feed the result back
as an observation until it chooses "final_answer".
"""
from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Sequence

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool

log = logging.getLogger(__name__)

FINAL = "final_answer"


@dataclass
class AgentRun:
    answer: str
    artifacts: list[dict] = field(default_factory=list)
    steps: list[dict] = field(default_factory=list)


def _tool_catalog(tools: Sequence[BaseTool]) -> str:
    lines = []
    for t in tools:
        schema = t.tool_call_schema.model_json_schema() if t.tool_call_schema else {}
        params = json.dumps(schema.get("properties", {}), ensure_ascii=False)
        defs = schema.get("$defs")
        if defs:
            params += f" defs={json.dumps(defs, ensure_ascii=False)}"
        required = schema.get("required", [])
        lines.append(f"- {t.name}: {t.description.strip()}\n  args: {params}\n  required: {required}")
    return "\n".join(lines)


def _step_schema(tool_names: list[str], final_only: bool = False) -> dict:
    actions = [FINAL] if final_only else [*tool_names, FINAL]
    return {
        "type": "object",
        "properties": {
            "thought": {"type": "string", "description": "Brief private reasoning about the next step."},
            "action": {"type": "string", "enum": actions},
            "args": {"type": "object", "description": "Arguments for the tool; {} for final_answer."},
            "answer": {"type": "string", "description": "Reply to the user (markdown) when action is final_answer, else empty."},
        },
        "required": ["thought", "action", "args", "answer"],
    }


PROTOCOL = """
## How to act
You work in steps. Every reply MUST be a single JSON object:
{{"thought": "...", "action": "<tool name or final_answer>", "args": {{...}}, "answer": "..."}}
- To use a tool: set "action" to the tool name and "args" to its arguments; leave "answer" empty.
- After each tool call you receive an "Observation". Use it to decide the next step.
- When you are done, or need to ask the user something, set "action" to "final_answer" and put your
  full reply to the user in "answer" (markdown allowed). "args" must be {{}}.
- Never invent tool results. Call one tool per step.

## Tools
{catalog}
"""


def _as_text(m: BaseMessage) -> str:
    c = m.content
    if isinstance(c, list):
        c = "\n".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in c)
    return str(c)


def _history(messages: Sequence[BaseMessage]) -> list[BaseMessage]:
    """Keep only user/assistant turns as plain text (no tool-call structures)."""
    out: list[BaseMessage] = []
    for m in messages:
        if isinstance(m, HumanMessage):
            out.append(HumanMessage(_as_text(m)))
        elif isinstance(m, AIMessage) and _as_text(m).strip():
            out.append(AIMessage(_as_text(m)))
    return out


async def run_json_react(
    llm: BaseChatModel,
    tools: Sequence[BaseTool],
    system_prompt: str,
    messages: Sequence[BaseMessage],
    max_steps: int = 8,
    max_observation_chars: int = 12000,
) -> AgentRun:
    by_name = {t.name: t for t in tools}
    names = list(by_name)
    system = SystemMessage(system_prompt + PROTOCOL.format(catalog=_tool_catalog(tools)))
    convo: list[BaseMessage] = [system, *_history(messages)]
    run = AgentRun(answer="")

    for step_no in range(max_steps):
        final_only = step_no == max_steps - 1
        schema = _step_schema(names, final_only)
        bound = llm.bind(response_format={"type": "json_schema", "json_schema": {"name": "agent_step", "schema": schema}})
        if final_only:
            convo.append(HumanMessage("Step limit reached. Respond now with action=final_answer using what you have."))
        resp = await bound.ainvoke(convo)
        raw = _as_text(resp)
        try:
            step = json.loads(raw)
            action = step["action"]
            args = step.get("args") or {}
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            log.warning("Unparseable step: %s (%s)", raw[:200], e)
            convo += [AIMessage(raw), HumanMessage(f"Observation: your reply was not valid JSON for the protocol ({e}). Try again.")]
            continue

        run.steps.append({"thought": step.get("thought", ""), "action": action, "args": args})
        convo.append(AIMessage(json.dumps(step, ensure_ascii=False)))

        if action == FINAL:
            run.answer = step.get("answer", "").strip() or step.get("thought", "")
            return run

        tool = by_name.get(action)
        if tool is None:
            convo.append(HumanMessage(f"Observation: unknown tool {action!r}. Available: {names}"))
            continue
        try:
            result = await tool.ainvoke({"type": "tool_call", "name": action, "args": args, "id": uuid.uuid4().hex})
            content = result.content if isinstance(result, ToolMessage) else str(result)
            artifact = getattr(result, "artifact", None)
            if artifact:
                run.artifacts.append(artifact)
        except Exception as e:  # validation errors, tool bugs -> let the model recover
            content = f"ERROR calling {action}: {e.__class__.__name__}: {str(e)[:800]}"
        content = str(content)
        if len(content) > max_observation_chars:
            content = content[:max_observation_chars] + "\n…(truncated)"
        convo.append(HumanMessage(f"Observation from {action}:\n{content}"))

    run.answer = run.answer or "I couldn't finish this request within the step limit. Please rephrase or narrow it down."
    return run


async def run_native_agent(
    llm: BaseChatModel,
    tools: Sequence[BaseTool],
    system_prompt: str,
    messages: Sequence[BaseMessage],
    max_steps: int = 8,
) -> AgentRun:
    """Same contract as run_json_react, using provider-native tool calling (WORKER_NATIVE_TOOLS=true)."""
    from langchain.agents import create_agent

    agent = create_agent(model=llm, tools=list(tools), system_prompt=system_prompt)
    result: dict[str, Any] = await agent.ainvoke(
        {"messages": _history(messages)}, {"recursion_limit": max_steps * 2 + 1}
    )
    out = result["messages"]
    artifacts = [m.artifact for m in out if isinstance(m, ToolMessage) and getattr(m, "artifact", None)]
    answer = next((_as_text(m) for m in reversed(out) if isinstance(m, AIMessage) and _as_text(m).strip()), "")
    return AgentRun(answer=answer, artifacts=artifacts)
