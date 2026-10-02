"""Single source of truth for the department agents: routing descriptions, nodes, tools, UI labels."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Awaitable, Callable

from app.agents import subagents
from app.tools.finance_tools import FINANCE_TOOLS
from app.tools.hr_tools import HR_TOOLS
from app.tools.pm_tools import PM_TOOLS
from app.tools.sql_tools import DEVOPS_TOOLS


@dataclass(frozen=True)
class AgentSpec:
    name: str
    label: str
    icon: str
    description: str      # shown to the supervisor for routing
    summary: str          # shown in UIs
    node: Callable[..., Awaitable[dict]]
    tools: list = field(default_factory=list)


AGENTS: dict[str, AgentSpec] = {a.name: a for a in [
    AgentSpec(
        "hr", "HR", "🧾",
        "contracts and HR paperwork. Drafting/customising employment or consultant contracts from templates, "
        "filling in new-hire details, editing clauses, job descriptions for contracts, listing contract templates.",
        "Drafts new-hire contracts from .docx templates.",
        subagents.hr_node, HR_TOOLS,
    ),
    AgentSpec(
        "devops", "DevOps", "🛠️",
        "questions answered from the company's IT/operations database: employees directory, IT assets/laptops, "
        "warranties, servers, cloud costs, deployments, incidents, software licenses, access requests. Any "
        "'how many / which / list / show me' question about that data.",
        "Answers IT/ops questions with read-only SQL.",
        subagents.devops_node, DEVOPS_TOOLS,
    ),
    AgentSpec(
        "finance", "Finance", "💵",
        "client invoices and billing: creating/duplicating invoices, billing hours × rate, invoice totals, tax, "
        "listing past invoices, clients and the company bank accounts used for payment.",
        "Generates client invoices on the company letterhead (PDF).",
        subagents.finance_node, FINANCE_TOOLS,
    ),
    AgentSpec(
        "pm", "PM", "📋",
        "project management with the user's Jira: projects, boards, sprints, backlog/issue status, velocity, "
        "workload, and planning sprints or roadmaps against a deadline.",
        "Reads your Jira and plans sprints against deadlines (read-only).",
        subagents.pm_node, PM_TOOLS,
    ),
    AgentSpec(
        "developer", "Developer", "💡",
        "brainstorming and refining software ideas, architecture, technical design, code questions, "
        "research-style discussion, writing specs, diagrams (Mermaid).",
        "Brainstorming, architecture and diagrams.",
        subagents.developer_node, [],
    ),
]}
