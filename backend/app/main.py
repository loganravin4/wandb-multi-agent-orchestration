"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.observability import init_weave
from app.routers import health, sessions


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fail fast if required credentials are missing (PRD requirement).
    missing = get_settings().missing_required()
    if missing:
        raise RuntimeError(
            "Missing required environment variables: " + ", ".join(missing)
        )
    # Initialize Weave tracing once, before serving any requests.
    init_weave()
    # Warm-up hooks (e.g. preload Whisper) can go here
    yield


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Multi-Agent Orchestration API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix="/api")
    app.include_router(sessions.router, prefix="/api")

    return app


app = create_app()
