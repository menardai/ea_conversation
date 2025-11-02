"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx
from fastapi import Depends, FastAPI

from app import __version__
from app.config import Settings, get_settings
from app.logging import configure_logging
from app.websocket_handlers import websocket_endpoint


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create application resources during startup and clean up on shutdown."""

    async with httpx.AsyncClient() as client:
        app.state.http_client = client
        yield
        del app.state.http_client


def create_app() -> FastAPI:
    """Application factory."""

    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="LLM to TTS WebSocket Service",
        version=__version__,
        lifespan=lifespan,
    )

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/version")
    async def version(settings: Settings = Depends(get_settings)) -> dict[str, str]:
        return {"version": __version__, "environment": settings.environment}

    app.add_api_websocket_route("/ws", websocket_endpoint)

    return app


app = create_app()
