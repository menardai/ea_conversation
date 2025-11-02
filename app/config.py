"""Application settings loaded from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly typed application configuration."""

    openai_api_key: str = Field(alias="OPENAI_API_KEY")
    chat_model: str = Field(default="gpt-4o-mini", alias="CHAT_MODEL")
    tts_model: str = Field(default="tts-1", alias="TTS_MODEL")
    tts_voice: str = Field(default="alloy", alias="TTS_VOICE")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    log_level: Literal["debug", "info", "warning", "error", "critical"] = Field(
        default="info", alias="LOG_LEVEL"
    )
    port: int = Field(default=8000, alias="PORT")
    max_text_length: int = Field(default=1000, alias="MAX_TEXT_LENGTH")
    ws_inactivity_timeout: float = Field(
        default=30.0, alias="WS_INACTIVITY_TIMEOUT", description="Seconds"
    )
    chat_timeout: float = Field(default=10.0, alias="CHAT_TIMEOUT")
    tts_timeout: float = Field(default=20.0, alias="TTS_TIMEOUT")

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


@lru_cache
def get_settings() -> Settings:
    """Return a cached instance of settings."""

    return Settings()
