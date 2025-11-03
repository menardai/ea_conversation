"""WebSocket handlers for the application."""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from typing import Annotated

from fastapi import Depends, WebSocket, WebSocketDisconnect, status
from starlette.websockets import WebSocketState

from app.config import Settings, get_settings
from app.dependencies import get_chat_service, get_tts_service
from app.exceptions import ChatServiceError, TtsServiceError
from app.models import ErrorResponse, MessageIn
from app.services.chat_service import ChatService
from app.services.tts_service import TtsService

logger = logging.getLogger(__name__)


async def websocket_endpoint(
    websocket: WebSocket,
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
    tts_service: Annotated[TtsService, Depends(get_tts_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    """Main WebSocket workflow: text → chat → TTS → audio bytes."""

    await websocket.accept()
    should_close = True
    logger.info(
        "WebSocket connection accepted",
        extra={"client": _client_repr(websocket)},
    )

    try:
        while True:
            try:
                message = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=settings.ws_inactivity_timeout,
                )
            except asyncio.TimeoutError:
                logger.info(
                    "WebSocket inactive; closing",
                    extra={"client": _client_repr(websocket)},
                )
                await websocket.close(code=status.WS_1000_NORMAL_CLOSURE)
                should_close = False
                break
            except WebSocketDisconnect:
                logger.info(
                    "WebSocket client disconnected",
                    extra={"client": _client_repr(websocket)},
                )
                should_close = False
                break

            try:
                payload = MessageIn.model_validate_json(message)
            except ValueError:
                await _send_error(
                    websocket,
                    ErrorResponse(error="invalid_payload", detail="Invalid JSON payload."),
                )
                continue

            text = payload.text.strip()
            if len(text) == 0:
                await _send_error(
                    websocket,
                    ErrorResponse(error="validation_error", detail="Text must not be empty."),
                )
                continue

            if len(text) > settings.max_text_length:
                await _send_error(
                    websocket,
                    ErrorResponse(
                        error="validation_error",
                        detail=f"Text length exceeds limit of {settings.max_text_length} characters.",
                    ),
                )
                continue

            try:
                reply = await chat_service.complete(text)
            except ChatServiceError as exc:
                await _send_error(
                    websocket,
                    ErrorResponse(
                        error="chat_error",
                        detail=exc.message,
                    ),
                )
                continue

            try:
                audio_bytes = await tts_service.synthesize(reply)
            except TtsServiceError as exc:
                await _send_error(
                    websocket,
                    ErrorResponse(
                        error="tts_error",
                        detail=exc.message,
                    ),
                )
                continue

            await websocket.send_bytes(audio_bytes)
            logger.info(
                "Audio payload delivered",
                extra={
                    "client": _client_repr(websocket),
                    "bytes": len(audio_bytes),
                },
            )
    finally:
        if should_close and websocket.application_state == WebSocketState.CONNECTED:
            with suppress(RuntimeError, WebSocketDisconnect):
                await websocket.close()
        logger.info(
            "WebSocket connection closed",
            extra={"client": _client_repr(websocket)},
        )


async def _send_error(websocket: WebSocket, error: ErrorResponse) -> None:
    """Send a structured error frame."""

    await websocket.send_text(error.model_dump_json())


def _client_repr(websocket: WebSocket) -> str:
    """Render the remote client for logging purposes."""

    client = websocket.client
    if client is None:
        return "unknown"
    return f"{client.host}:{client.port}"
