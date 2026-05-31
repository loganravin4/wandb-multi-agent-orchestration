"""LangGraph workflow definition."""

from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.agents.nodes.format import format_node
from app.agents.nodes.jd_parser import jd_parser_node
from app.agents.nodes.research import research_node
from app.state import SessionState


def build_graph() -> StateGraph:
    """
    Ingest pipeline:
      [jd_parser ‖ research]  ← parallel fan-out from START
            └── format        ← runs after both complete (automatic join)
    """
    graph = StateGraph(SessionState)

    graph.add_node("jd_parser", jd_parser_node)
    graph.add_node("research", research_node)
    graph.add_node("format", format_node)

    # Both jd_parser and research start immediately — they only need the initial state
    graph.add_edge(START, "jd_parser")
    graph.add_edge(START, "research")

    # format waits for both to finish (LangGraph joins automatically)
    graph.add_edge("jd_parser", "format")
    graph.add_edge("research", "format")

    graph.add_edge("format", END)

    return graph


@lru_cache(maxsize=1)
def get_graph():
    """Compiled graph singleton — call get_graph.cache_clear() to rebuild."""
    return build_graph().compile()
