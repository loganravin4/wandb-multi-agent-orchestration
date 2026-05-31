"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # W&B Serverless Inference (OpenAI-compatible). No Anthropic key needed.
    inference_base_url: str = "https://api.inference.wandb.ai/v1"

    # Per-agent model IDs (override via env, e.g. MODEL_RESEARCH=...).
    model_jd_parser: str = "meta-llama/Llama-3.1-8B-Instruct"
    model_research: str = "meta-llama/Llama-3.3-70B-Instruct"
    model_format: str = "meta-llama/Llama-3.3-70B-Instruct"
    model_interviewer: str = "meta-llama/Llama-3.3-70B-Instruct"
    model_delivery: str = "meta-llama/Llama-3.1-8B-Instruct"
    model_report: str = "deepseek-ai/DeepSeek-V3-0324"

    # Tavily
    tavily_api_key: str = ""

    # W&B
    wandb_api_key: str = ""
    wandb_project: str = "loopprep"
    wandb_entity: str = ""

    # Whisper
    whisper_model: str = "base"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def missing_required(self) -> list[str]:
        """Names of required keys that are unset (PRD: all four needed to start)."""
        required = {
            "WANDB_API_KEY": self.wandb_api_key,
            "WANDB_ENTITY": self.wandb_entity,
            "WANDB_PROJECT": self.wandb_project,
            "TAVILY_API_KEY": self.tavily_api_key,
        }
        return [name for name, value in required.items() if not value]


@lru_cache
def get_settings() -> Settings:
    return Settings()
