"""LangGraph workflow definition."""

from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.agents.nodes.format import format_node
from app.agents.nodes.research import research_node
from app.state import SessionState


def build_graph() -> StateGraph:
    """Build the multi-agent session graph: research → format → (interview loop TBD)."""
    graph = StateGraph(SessionState)

    graph.add_node("research", research_node)
    graph.add_node("format", format_node)

    graph.add_edge(START, "research")
    graph.add_edge("research", "format")
    graph.add_edge("format", END)

    return graph


@lru_cache
def get_graph():
    """Compiled graph singleton."""
    return build_graph().compile()
