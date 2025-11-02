"""Adapter for OpenAI text-to-speech synthesis."""

from __future__ import annotations

import logging

import httpx

from app.config import Settings
from app.exceptions import TtsServiceError

logger = logging.getLogger(__name__)


class TtsService:
    """Wrapper around OpenAI's TTS endpoint."""

    _endpoint = "https://api.openai.com/v1/audio/speech"
    _output_format = "audio/mpeg"

    def __init__(self, client: httpx.AsyncClient, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    async def synthesize(self, text: str) -> bytes:
        """Generate speech audio for the supplied text."""

        payload = {
            "model": self._settings.tts_model,
            "voice": self._settings.tts_voice,
            "input": text,
            "format": "mp3",
        }

        headers = {
            "Authorization": f"Bearer {self._settings.openai_api_key}",
            "Content-Type": "application/json",
            "Accept": self._output_format,
        }

        try:
            response = await self._client.post(
                self._endpoint,
                headers=headers,
                json=payload,
                timeout=self._settings.tts_timeout,
            )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            logger.warning("TTS synthesis timed out", exc_info=exc)
            raise TtsServiceError("Text-to-speech service timed out") from exc
        except httpx.HTTPStatusError as exc:
            logger.error(
                "TTS synthesis failed",
                extra={
                    "status_code": exc.response.status_code,
                    "response_text": exc.response.text,
                },
            )
            raise TtsServiceError(
                "Text-to-speech service returned an error",
                status_code=exc.response.status_code,
            ) from exc
        except httpx.HTTPError as exc:
            logger.exception("Unexpected TTS HTTP error")
            raise TtsServiceError("Text-to-speech request failed") from exc

        audio_bytes = response.content
        if not audio_bytes:
            raise TtsServiceError("Text-to-speech service returned empty payload")

        return audio_bytes
