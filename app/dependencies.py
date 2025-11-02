"""Dependency providers for the FastAPI application."""

import httpx
from fastapi import Depends
from starlette.requests import HTTPConnection

from app.config import Settings, get_settings
from app.services.chat_service import ChatService
from app.services.tts_service import TtsService


async def get_http_client(connection: HTTPConnection) -> httpx.AsyncClient:
    """Retrieve the shared AsyncClient from application state."""

    return connection.app.state.http_client  # type: ignore[return-value]


async def get_chat_service(
    client: httpx.AsyncClient = Depends(get_http_client),
    settings: Settings = Depends(get_settings),
) -> ChatService:
    """Dependency provider for ChatService."""

    return ChatService(client=client, settings=settings)


async def get_tts_service(
    client: httpx.AsyncClient = Depends(get_http_client),
    settings: Settings = Depends(get_settings),
) -> TtsService:
    """Dependency provider for TtsService."""

    return TtsService(client=client, settings=settings)
