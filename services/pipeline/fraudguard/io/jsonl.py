"""JSON Lines helpers.

Three modules used to hand-roll the same "read a .jsonl, skip broken lines"
loop, each with slightly different behaviour.  This is the single implementation.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator

from fraudguard.logging import get_logger

__all__ = ["read_jsonl", "iter_jsonl", "append_jsonl", "write_jsonl", "field_values", "sanitise"]

log = get_logger("fraudguard.jsonl")
_WRITE_LOCKS: dict[str, threading.Lock] = {}
_LOCKS_GUARD = threading.Lock()


def _lock_for(path: Path) -> threading.Lock:
    key = str(path)
    with _LOCKS_GUARD:
        return _WRITE_LOCKS.setdefault(key, threading.Lock())


def sanitise(value: Any) -> Any:
    """Make a value JSON-serialisable (datetimes → ISO strings, sets → lists)."""
    if isinstance(value, dict):
        return {str(k): sanitise(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [sanitise(v) for v in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def iter_jsonl(path: str | os.PathLike[str]) -> Iterator[dict[str, Any]]:
    """Yield each well-formed object in a ``.jsonl`` file; log and skip the rest."""
    file_path = Path(path)
    if not file_path.is_file():
        log.warning("JSONL file not found", extra={"path": str(file_path)})
        return
    with file_path.open("r", encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                log.warning(
                    "Skipping malformed JSONL line",
                    extra={"path": str(file_path), "line": line_no},
                )
                continue
            if isinstance(parsed, dict):
                yield parsed


def read_jsonl(path: str | os.PathLike[str]) -> list[dict[str, Any]]:
    return list(iter_jsonl(path))


def field_values(
    path: str | os.PathLike[str],
    field: str,
    *,
    default: Any = "",
    coerce: Callable[[Any], Any] | None = None,
) -> list[Any]:
    """Project a single field out of every record, with an optional coercion.

    Supports dotted paths (``"risk_json.risk_score"``).
    """
    parts = field.split(".")
    values: list[Any] = []
    for record in iter_jsonl(path):
        cursor: Any = record
        for part in parts:
            cursor = cursor.get(part) if isinstance(cursor, dict) else None
            if cursor is None:
                break
        value = default if cursor is None else cursor
        if coerce is not None:
            try:
                value = coerce(value)
            except (TypeError, ValueError):
                value = coerce(default)
        values.append(value)
    return values


def append_jsonl(path: str | os.PathLike[str], record: Any) -> None:
    """Append one record. Thread-safe within a process; always one line."""
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(sanitise(record), ensure_ascii=False)
    with _lock_for(file_path):
        with file_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")


def write_jsonl(path: str | os.PathLike[str], records: Iterable[Any]) -> None:
    """Atomically replace a file with the given records."""
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(file_path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(sanitise(record), ensure_ascii=False) + "\n")
        os.replace(tmp_name, file_path)
    except BaseException:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise
