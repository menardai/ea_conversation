import json

import httpx
import pytest

from app.config import Settings
from app.exceptions import TtsServiceError
from app.services.tts_service import TtsService


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.mark.asyncio
async def test_tts_service_success(settings: Settings) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode())
        assert payload["model"] == settings.tts_model
        assert payload["voice"] == settings.tts_voice
        return httpx.Response(200, content=b"\x00\x01")

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(transport=transport) as client:
        service = TtsService(client, settings)
        audio = await service.synthesize("hello")

    assert audio == b"\x00\x01"


@pytest.mark.asyncio
async def test_tts_service_empty_payload(settings: Settings) -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"")

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(transport=transport) as client:
        service = TtsService(client, settings)
        with pytest.raises(TtsServiceError):
            await service.synthesize("hello")


@pytest.mark.asyncio
async def test_tts_service_http_error(settings: Settings) -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": {"message": "fail"}})

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(transport=transport) as client:
        service = TtsService(client, settings)
        with pytest.raises(TtsServiceError):
            await service.synthesize("hello")
