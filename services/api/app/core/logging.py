"""Structured request-scoped logging for the API."""

from __future__ import annotations

import json
import logging
import logging.handlers
import sys
import time
from contextvars import ContextVar
from typing import Any

__all__ = ["configure", "get_logger", "request_id_var", "bind_request"]

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
_extra_var: ContextVar[dict[str, Any]] = ContextVar("log_extra", default={})
_CONFIGURED = False

_RESERVED = frozenset(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()
) | {"message", "asctime", "taskName"}


class _ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        for key, value in _extra_var.get().items():
            record.__dict__.setdefault(key, value)
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created))
            + f".{int(record.msecs):03d}Z",
            "level": record.levelname,
            "service": "compliance-api",
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value if isinstance(value, (str, int, float, bool)) else str(value)
        return json.dumps(payload, ensure_ascii=False, default=str)


class ConsoleFormatter(logging.Formatter):
    FMT = "%(asctime)s | %(levelname)-8s | %(request_id)s | %(name)s | %(message)s"

    def format(self, record: logging.LogRecord) -> str:
        return logging.Formatter(self.FMT, datefmt="%H:%M:%S").format(record)


def configure(level: str = "INFO", *, json_output: bool = False) -> logging.Logger:
    global _CONFIGURED
    root = logging.getLogger()
    if _CONFIGURED:
        return logging.getLogger("api")

    root.setLevel(level)
    for handler in list(root.handlers):
        root.removeHandler(handler)

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(JsonFormatter() if json_output else ConsoleFormatter())
    console.addFilter(_ContextFilter())
    root.addHandler(console)

    # Uvicorn's own access log duplicates our middleware, and SQLAlchemy is noisy.
    logging.getLogger("uvicorn.access").disabled = True
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    _CONFIGURED = True
    return logging.getLogger("api")


def get_logger(name: str) -> logging.Logger:
    if not _CONFIGURED:
        configure()
    return logging.getLogger(name)


def bind_request(**values: Any) -> None:
    """Attach key/value pairs to every log record for the rest of this request."""
    _extra_var.set({**_extra_var.get(), **values})
