"""Custom exceptions shared across services."""

from dataclasses import dataclass


@dataclass(eq=False)
class ServiceError(Exception):
    """Base exception for service layer failures."""

    message: str
    code: str = "service_error"
    status_code: int | None = None

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.message


class ChatServiceError(ServiceError):
    """Raised when ChatService fails to return a response."""

    code = "chat_error"


class TtsServiceError(ServiceError):
    """Raised when TtsService fails to return audio content."""

    code = "tts_error"
