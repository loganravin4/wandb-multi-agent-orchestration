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
      jd_parser → research → format
      Sequential so research can use jd_parser's structured signals
      to build a targeted Tavily query.
    """
    graph = StateGraph(SessionState)

    graph.add_node("jd_parser", jd_parser_node)
    graph.add_node("research", research_node)
    graph.add_node("format", format_node)

    graph.add_edge(START, "jd_parser")
    graph.add_edge("jd_parser", "research")
    graph.add_edge("research", "format")
    graph.add_edge("format", END)

    return graph


@lru_cache(maxsize=1)
def get_graph():
    """Compiled graph singleton — call get_graph.cache_clear() to rebuild."""
    return build_graph().compile()
