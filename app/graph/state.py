from typing import Optional

from langgraph.graph import MessagesState


class OfficeState(MessagesState):
    active_agent: Optional[str]          # last sub-agent used (sticky routing hint)
    department_hint: Optional[str]       # UI override: name of an agent
    attached_template_id: Optional[str]  # contract template chosen in the UI for this turn
    available_agents: list[str]          # agents this user may use right now (enabled ∩ allowed)
    user_id: Optional[int]
    username: Optional[str]
    route: Optional[str]                 # where the supervisor sent this turn
    route_reason: Optional[str]
    artifacts: list[dict]                # files / tables produced this turn
    trace: list[dict]                    # sub-agent steps this turn (admin drill-down)
    plan: list[dict]                     # multi-agent turn: [{"agent", "instruction"}] chosen by the supervisor
