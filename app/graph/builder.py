from langgraph.graph import END, START, StateGraph

from app.agents.registry import AGENTS
from app.graph.state import OfficeState
from app.graph.supervisor import route_after_supervisor, supervisor_node


def build_graph(checkpointer=None):
    g = StateGraph(OfficeState)
    g.add_node("supervisor", supervisor_node)
    for name, spec in AGENTS.items():
        g.add_node(name, spec.node)
        g.add_edge(name, END)
    g.add_edge(START, "supervisor")
    g.add_conditional_edges("supervisor", route_after_supervisor, {**{n: n for n in AGENTS}, "__end__": END})
    return g.compile(checkpointer=checkpointer)
