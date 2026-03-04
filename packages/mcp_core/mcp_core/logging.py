from __future__ import annotations

import logging
import sys
from typing import Any

import orjson


class JsonFormatter(logging.Formatter):
    """Simple JSON formatter for structured logs."""

    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        data: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "request_id"):
            data["request_id"] = record.request_id
        if hasattr(record, "tool_call_id"):
            data["tool_call_id"] = record.tool_call_id
        if hasattr(record, "tool_name"):
            data["tool_name"] = record.tool_name
        if record.exc_info:
            data["exc_info"] = self.formatException(record.exc_info)
        encoded: bytes = orjson.dumps(data)
        return encoded.decode("utf-8")


_configured = False


def configure_root_logger() -> None:
    global _configured
    if _configured:
        return

    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(handler)
    _configured = True


def get_logger(
    name: str, *, request_id: str | None = None, tool_call_id: str | None = None
) -> logging.Logger:
    """Return a logger with optional bound context."""

    configure_root_logger()
    logger = logging.getLogger(name)
    extra: dict[str, Any] = {}
    if request_id is not None:
        extra["request_id"] = request_id
    if tool_call_id is not None:
        extra["tool_call_id"] = tool_call_id

    if not extra:
        return logger

    return logging.LoggerAdapter(logger, extra)  # type: ignore[return-value]
