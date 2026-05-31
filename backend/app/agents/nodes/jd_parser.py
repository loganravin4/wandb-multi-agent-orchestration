"""JD Parser agent node — extracts structured signals from the job description."""

from __future__ import annotations

import json
import re

import weave
from langchain_core.messages import HumanMessage, SystemMessage

from app.services.llm import get_llm
from app.state import SessionState

_SYSTEM = """\
You are a job description parser. Extract structured signals from the JD and return JSON only.

Return exactly this shape:
{
  "company": "string (infer from JD if not obvious)",
  "role": "string (job title)",
  "seniority": "intern|junior|mid|senior|staff|principal",
  "tech_stack": ["list", "of", "technologies"],
  "behavioral_signals": ["ownership", "cross-functional", "etc"]
}

No markdown fences. No explanation. Valid JSON only."""


@weave.op()
def jd_parser_node(state: SessionState) -> SessionState:
    """Parse the job description into structured fields."""
    llm = get_llm("fast")
    response = llm.invoke(
        [
            SystemMessage(content=_SYSTEM),
            HumanMessage(content=state.get("job_description", "")),
        ]
    )

    raw = response.content if isinstance(response.content, str) else str(response.content)
    match = re.search(r"\{[\s\S]*\}", raw)
    parsed: dict = json.loads(match.group()) if match else {}

    return {
        **state,
        "company": parsed.get("company") or state.get("company", ""),
        "role": parsed.get("role") or state.get("role", ""),
        "seniority": parsed.get("seniority") or state.get("seniority", "mid"),
        "jd_parsed": parsed,
    }
