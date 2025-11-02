import json

import httpx
import pytest

from app.config import Settings
from app.exceptions import ChatServiceError
from app.services.chat_service import ChatService


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.mark.asyncio
async def test_chat_service_success(settings: Settings) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode())
        assert payload["model"] == settings.chat_model
        assert payload["messages"][1]["content"] == "hello"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {"content": "hi there"},
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(transport=transport) as client:
        service = ChatService(client, settings)
        result = await service.complete("hello")

    assert result == "hi there"


@pytest.mark.asyncio
async def test_chat_service_timeout(settings: Settings) -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timeout")

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(transport=transport) as client:
        service = ChatService(client, settings)
        with pytest.raises(ChatServiceError) as exc:
            await service.complete("hello")

    assert "timed out" in str(exc.value)


@pytest.mark.asyncio
async def test_chat_service_bad_payload(settings: Settings) -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": "structure"})

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(transport=transport) as client:
        service = ChatService(client, settings)
        with pytest.raises(ChatServiceError):
            await service.complete("hello")
