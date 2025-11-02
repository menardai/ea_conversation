"""Adapter for OpenAI chat completions."""

from __future__ import annotations

import logging

import httpx

from app.config import Settings
from app.exceptions import ChatServiceError

logger = logging.getLogger(__name__)


class ChatService:
    """Wrapper around OpenAI's chat completions endpoint."""

    _endpoint = "https://api.openai.com/v1/chat/completions"

    def __init__(self, client: httpx.AsyncClient, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    async def complete(self, prompt: str) -> str:
        """Generate a chat completion from OpenAI."""

        payload = {
            "model": self._settings.chat_model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
        }

        headers = {
            "Authorization": f"Bearer {self._settings.openai_api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = await self._client.post(
                self._endpoint,
                headers=headers,
                json=payload,
                timeout=self._settings.chat_timeout,
            )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            logger.warning("Chat completion timed out", exc_info=exc)
            raise ChatServiceError("Chat service timed out") from exc
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Chat completion failed",
                extra={
                    "status_code": exc.response.status_code,
                    "response_text": exc.response.text,
                },
            )
            raise ChatServiceError(
                "Chat service returned an error",
                status_code=exc.response.status_code,
            ) from exc
        except httpx.HTTPError as exc:
            logger.exception("Unexpected chat HTTP error")
            raise ChatServiceError("Chat service request failed") from exc

        data = response.json()
        try:
            choice = data["choices"][0]
            message = choice["message"]
            content = message["content"]
        except (KeyError, IndexError, TypeError) as exc:
            logger.error("Malformed chat response", extra={"raw_response": data})
            raise ChatServiceError("Invalid chat response payload") from exc

        if not content:
            raise ChatServiceError("Chat service returned empty content")

        return content.strip()
