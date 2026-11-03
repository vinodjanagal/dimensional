"""Centralized structured logging configuration."""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from logging.config import dictConfig
from typing import Any


request_id_var: ContextVar[str | None] = ContextVar(
    "request_id",
    default=None,
)


class JsonFormatter(logging.Formatter):
    """Format log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = (
            datetime.fromtimestamp(record.created, tz=timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z")
        )

        log_entry: dict[str, Any] = {
            "timestamp": timestamp,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        request_id = request_id_var.get()
        if request_id is not None:
            log_entry["request_id"] = request_id

        # Include structured fields supplied through logging's `extra` argument.
        _STANDARD_FIELDS = frozenset(logging.makeLogRecord({}).__dict__.keys())
        _EXCLUDED = _STANDARD_FIELDS | {
            "timestamp",
            "level",
            "logger",
            "message",
            "asctime",
            "request_id",
        }

        for key, value in record.__dict__.items():
            if key not in _EXCLUDED and not key.startswith("_"):
                log_entry[key] = value

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


def configure_logging(log_level: str = "INFO") -> None:
    """Configure consistent JSON logging for the application."""

    resolved_level = getattr(logging, log_level.upper(), None)

    if not isinstance(resolved_level, int):
        raise ValueError(f"Invalid logging level: {log_level!r}")

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "()": JsonFormatter,
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "stream": sys.stdout,
                    "formatter": "json",
                },
            },
            "root": {
                "level": resolved_level,
                "handlers": ["console"],
            },
            "loggers": {
                # Route server logs through the same JSON formatter.
                "uvicorn": {
                    "handlers": [],
                    "level": resolved_level,
                    "propagate": True,
                },
                "uvicorn.error": {
                    "handlers": [],
                    "level": resolved_level,
                    "propagate": True,
                },
                "uvicorn.access": {
                    "handlers": [],
                    "level": resolved_level,
                    "propagate": False,
                },
                # ARQ runs in a separate process, but uses the same
                # logging configuration when configure_logging() is called.
                "arq": {
                    "handlers": [],
                    "level": resolved_level,
                    "propagate": True,
                },
            },
        }
    )
