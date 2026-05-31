"""Research agent node — Tavily + LLM."""

from __future__ import annotations

import weave
from langchain_core.messages import HumanMessage, SystemMessage

from app.observability import log_research_metrics
from app.services.llm import get_llm
from app.services.research import search
from app.state import SessionState


@weave.op()
def research_node(state: SessionState) -> SessionState:
    """Gather interview context via web research and summarize with the LLM."""
    company = state.get("company", "")
    role = state.get("role", "")
    query = f"{company} {role} interview process format common questions"
    results = search(query, max_results=5)

    snippets = "\n".join(
        f"- {r.get('title', 'Untitled')}: {r.get('content', '')[:300]}"
        for r in results
    )

    llm = get_llm("default")
    response = llm.invoke(
        [
            SystemMessage(
                content=(
                    "You summarize interview research for a mock interview prep session. "
                    "Return a short interview_format paragraph and a bullet list of common_topics."
                )
            ),
            HumanMessage(content=f"Job: {state.get('job_description', '')}\n\nResearch:\n{snippets}"),
        ]
    )

    text = response.content if isinstance(response.content, str) else str(response.content)
    interview_format = text[:500]
    common_topics = [line.strip("- ").strip() for line in text.splitlines() if line.strip().startswith("-")][:10]

    log_research_metrics(interview_format, common_topics)

    return {
        **state,
        "interview_format": interview_format,
        "common_topics": common_topics or ["general behavioral", "technical depth"],
        "phase": "interview",
    }
