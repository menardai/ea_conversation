"""Logging configuration utilities."""

import json
import logging
import sys
from typing import Any, MutableMapping


class JsonFormatter(logging.Formatter):
    """Formatter that renders log records as JSON lines."""

    def format(self, record: logging.LogRecord) -> str:
        payload: MutableMapping[str, Any] = {
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        for key, value in record.__dict__.items():
            if key.startswith("_") or key in payload:
                continue

            if key in {"args", "msg"}:
                continue

            payload[key] = value

        return json.dumps(payload, default=str)


def configure_logging(level: str) -> None:
    """Configure root logger for structured logging."""

    logging_level = getattr(logging, level.upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging_level)
    root_logger.addHandler(handler)
