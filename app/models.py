"""Pydantic models shared across application layers."""

from pydantic import BaseModel, Field


class MessageIn(BaseModel):
    """Incoming WebSocket payload."""

    text: str = Field(min_length=1, description="User supplied text prompt.")


class ErrorResponse(BaseModel):
    """Error frame returned to WebSocket clients."""

    error: str
    detail: str | None = None
