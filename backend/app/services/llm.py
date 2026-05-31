"""W&B Serverless Inference LLM client (OpenAI-compatible API)."""

from __future__ import annotations

from langchain_openai import ChatOpenAI

from app.config import get_settings

_WB_BASE_URL = "https://api.inference.wandb.ai/v1"

# Per CLAUDE.md agent assignments
MODELS = {
    "fast": "meta-llama/Llama-3.1-8B-Instruct",       # JD Parser, Delivery Agent
    "default": "meta-llama/Llama-3.3-70B-Instruct",   # Research, Format, Interviewer
    "synthesis": "meta-llama/Llama-3.3-70B-Instruct",   # Report Agent (DeepSeek-V3 unavailable)
}


def get_llm(size: str = "default") -> ChatOpenAI:
    """Return a LangChain ChatOpenAI pointed at W&B Serverless Inference."""
    settings = get_settings()
    model_id = MODELS.get(size, size)
    return ChatOpenAI(
        model=model_id,
        base_url=_WB_BASE_URL,
        api_key=settings.wandb_api_key,
        temperature=0.7,
        max_tokens=4096,
    )
