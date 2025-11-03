import json

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect, WebSocketState

from app.config import Settings
from app.dependencies import get_chat_service, get_tts_service
from app.models import ErrorResponse
from app.websocket_handlers import websocket_endpoint


class DummyChatService:
    async def complete(self, text: str) -> str:
        return f"LLM reply to: {text}"


class DummyTtsService:
    async def synthesize(self, text: str) -> bytes:
        return text.encode("utf-8")


def get_test_client(app):
    app.dependency_overrides[get_chat_service] = lambda: DummyChatService()
    app.dependency_overrides[get_tts_service] = lambda: DummyTtsService()
    return TestClient(app)


def test_websocket_happy_path(app) -> None:
    client = get_test_client(app)

    with client.websocket_connect("/ws") as websocket:
        websocket.send_text(json.dumps({"text": "hello"}))
        payload = websocket.receive_bytes()

    assert payload == b"LLM reply to: hello"


def test_websocket_invalid_json(app) -> None:
    client = get_test_client(app)

    with client.websocket_connect("/ws") as websocket:
        websocket.send_text("not-json")
        response = websocket.receive_text()

    data = json.loads(response)
    assert data["error"] == "invalid_payload"


def test_websocket_text_length_enforced(app) -> None:
    client = get_test_client(app)

    oversized = "a" * 1200

    with client.websocket_connect("/ws") as websocket:
        websocket.send_text(json.dumps({"text": oversized}))
        response = websocket.receive_text()

    data = json.loads(response)
    assert data["error"] == "validation_error"


class _ClientAddress:
    def __init__(self, host: str = "127.0.0.1", port: int = 12345) -> None:
        self.host = host
        self.port = port


class DummyWebSocket:
    """Minimal WebSocket stub to reproduce disconnect behaviour."""

    def __init__(self, messages: list[str]) -> None:
        self._messages = messages
        self.accepted = False
        self.sent_bytes: list[bytes] = []
        self.sent_text: list[str] = []
        self.close_called = False
        self.client = _ClientAddress()
        self.application_state = WebSocketState.CONNECTED

    async def accept(self) -> None:
        self.accepted = True

    async def receive_text(self) -> str:
        if not self._messages:
            raise WebSocketDisconnect()
        item = self._messages.pop(0)
        if item == "__disconnect__":
            raise WebSocketDisconnect()
        return item

    async def send_text(self, data: str) -> None:
        self.sent_text.append(data)

    async def send_bytes(self, data: bytes) -> None:
        self.sent_bytes.append(data)

    async def close(self, code: int = 1000) -> None:
        self.close_called = True
        raise AssertionError("close should not be invoked when client already disconnected")


@pytest.mark.asyncio
async def test_websocket_skips_close_after_client_disconnect(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    settings = Settings()
    chat_service = DummyChatService()
    tts_service = DummyTtsService()
    payload = json.dumps({"text": "hello"})
    websocket = DummyWebSocket([payload, "__disconnect__"])

    await websocket_endpoint(websocket, chat_service, tts_service, settings)

    assert websocket.accepted
    assert websocket.sent_bytes == [b"LLM reply to: hello"]
    assert websocket.sent_text == []
    assert websocket.close_called is False
