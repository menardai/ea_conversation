import json

from fastapi.testclient import TestClient

from app.dependencies import get_chat_service, get_tts_service
from app.models import ErrorResponse


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
