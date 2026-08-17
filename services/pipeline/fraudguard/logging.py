"""Structured logging for every pipeline flow.

Replaces the mixture of ``print()`` calls and ad-hoc ``logging.basicConfig``
invocations that used to be scattered through the codebase.

* One call — :func:`configure` — sets up console + rotating file handlers.
* ``LOG_JSON=true`` switches the console to newline-delimited JSON, which is what
  a log shipper (Filebeat/Vector/Fluent Bit → Elasticsearch) wants.  This is the
  dependency-free half of roadmap item P0.3.
* :func:`get_logger` returns a logger with a ``bind`` helper for per-record
  context (entity id, flow name, ...) without reaching for a third-party lib.
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import os
import sys
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator, Mapping

__all__ = ["configure", "get_logger", "log_context", "current_context", "timed"]

_CONTEXT: ContextVar[dict[str, Any]] = ContextVar("fraudguard_log_context", default={})
_CONFIGURED = False

_RESERVED = frozenset(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()
) | {"message", "asctime", "taskName"}


class _ContextFilter(logging.Filter):
    """Attach the ambient :func:`log_context` values to every record."""

    def filter(self, record: logging.LogRecord) -> bool:
        for key, value in _CONTEXT.get().items():
            if key not in record.__dict__:
                record.__dict__[key] = value
        return True


class JsonFormatter(logging.Formatter):
    """Newline-delimited JSON, one object per record."""

    def __init__(self, service: str) -> None:
        super().__init__()
        self.service = service

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created))
            + f".{int(record.msecs):03d}Z",
            "level": record.levelname,
            "service": self.service,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = _jsonable(value)
        return json.dumps(payload, ensure_ascii=False, default=str)


def _jsonable(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Mapping):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v) for v in value]
    return str(value)


class ConsoleFormatter(logging.Formatter):
    """Human-readable console output with the bound context appended."""

    DEFAULT_FMT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

    def format(self, record: logging.LogRecord) -> str:
        base = logging.Formatter(self.DEFAULT_FMT, datefmt="%H:%M:%S").format(record)
        extras = {
            key: value
            for key, value in record.__dict__.items()
            if key not in _RESERVED and not key.startswith("_")
        }
        if extras:
            rendered = " ".join(f"{k}={v}" for k, v in sorted(extras.items()))
            base = f"{base}  [{rendered}]"
        return base


def configure(
    service: str,
    *,
    level: str | None = None,
    json_output: bool | None = None,
    log_dir: os.PathLike[str] | str | None = None,
) -> logging.Logger:
    """Configure the root logger once per process and return the service logger."""
    global _CONFIGURED

    # Imported lazily so `configure` can be used before settings are loadable.
    from fraudguard.config import get_settings

    settings = get_settings()
    level = (level or settings.log_level).upper()
    json_output = settings.log_json if json_output is None else json_output
    log_dir = log_dir or settings.paths.logs

    root = logging.getLogger()
    if _CONFIGURED:
        return logging.getLogger(service)

    root.setLevel(level)
    for handler in list(root.handlers):
        root.removeHandler(handler)

    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(JsonFormatter(service) if json_output else ConsoleFormatter())
    console.addFilter(_ContextFilter())
    root.addHandler(console)

    try:
        file_handler = logging.handlers.RotatingFileHandler(
            os.path.join(str(log_dir), f"{service}.log"),
            maxBytes=16 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(JsonFormatter(service))
        file_handler.addFilter(_ContextFilter())
        root.addHandler(file_handler)
    except OSError:  # read-only volume, container without a mount, ...
        root.warning("File logging disabled: %s is not writable", log_dir)

    # These libraries are extremely chatty at DEBUG/INFO.
    for noisy in ("urllib3", "botocore", "boto3", "s3transfer", "httpx", "LiteLLM", "litellm"):
        logging.getLogger(noisy).setLevel(max(logging.WARNING, getattr(logging, level, 20)))

    _CONFIGURED = True
    return logging.getLogger(service)


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger (configure the root first if nobody has)."""
    if not _CONFIGURED:
        configure(name.split(".")[0])
    return logging.getLogger(name)


@contextmanager
def log_context(**values: Any) -> Iterator[None]:
    """Bind key/value pairs onto every log record emitted inside the block."""
    token = _CONTEXT.set({**_CONTEXT.get(), **values})
    try:
        yield
    finally:
        _CONTEXT.reset(token)


def current_context() -> dict[str, Any]:
    return dict(_CONTEXT.get())


@contextmanager
def timed(logger: logging.Logger, operation: str, **values: Any) -> Iterator[dict[str, Any]]:
    """Log the duration and outcome of a block; yields a mutable detail dict."""
    correlation_id = values.pop("correlation_id", None) or uuid.uuid4().hex[:12]
    details: dict[str, Any] = {}
    started = time.perf_counter()
    with log_context(operation=operation, correlation_id=correlation_id, **values):
        try:
            yield details
        except Exception as exc:
            logger.exception(
                "%s failed after %.1f ms: %s",
                operation,
                (time.perf_counter() - started) * 1000,
                exc,
                extra={"outcome": "error", **details},
            )
            raise
        logger.info(
            "%s completed in %.1f ms",
            operation,
            (time.perf_counter() - started) * 1000,
            extra={"outcome": "ok", **details},
        )
