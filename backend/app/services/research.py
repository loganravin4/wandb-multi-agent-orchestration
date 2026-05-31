"""Tavily web research client."""

from __future__ import annotations

from functools import lru_cache

import weave
from tavily import TavilyClient

from app.config import get_settings


@lru_cache
def _get_client() -> TavilyClient:
    settings = get_settings()
    return TavilyClient(api_key=settings.tavily_api_key)


@weave.op()
def search(query: str, max_results: int = 5) -> list[dict]:
    """Run a Tavily search and return result dicts."""
    client = _get_client()
    response = client.search(query=query, max_results=max_results)
    return response.get("results", [])
