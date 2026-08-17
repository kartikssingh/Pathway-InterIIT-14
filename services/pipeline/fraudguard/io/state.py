"""Durable checkpoint / state storage (roadmap item P1.2).

Flows previously kept run state in throwaway directories (``out/watchdog_prev``
copied with ``shutil.copytree``) with no retention policy and no way to inspect
what a previous run saw.  :class:`StateStore` gives every flow a small, audited,
compressed, append-only history keyed by name, plus retention pruning.

Deliberately dependency-free — no boto3 import at module scope — so the pipeline
runs the same with or without cloud credentials.  An S3 mirror can be layered on
by passing ``uploader=``.
"""

from __future__ import annotations

import gzip
import json
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterator

from fraudguard.io.jsonl import sanitise
from fraudguard.logging import get_logger

__all__ = ["StateStore", "StateEntry"]

log = get_logger("fraudguard.state")

_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class StateEntry:
    key: str
    timestamp: datetime
    path: Path
    metadata: dict[str, Any]

    def load(self) -> Any:
        return _read(self.path).get("data")


def _read(path: Path) -> dict[str, Any]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:  # type: ignore[operator]
        return json.load(handle)


class StateStore:
    """Versioned snapshots on the local filesystem.

    >>> store = StateStore("watchdog")
    >>> store.save("web_analysis", {"entity_id": "42", "prompt": "..."})
    >>> store.load_latest("web_analysis")
    {'entity_id': '42', 'prompt': '...'}
    """

    def __init__(
        self,
        namespace: str,
        *,
        root: Path | None = None,
        retention_days: int = 30,
        compress: bool = True,
        uploader: Callable[[Path, str], None] | None = None,
    ) -> None:
        from fraudguard.config import get_settings

        base = root or get_settings().paths.state
        self.namespace = namespace
        self.root = Path(base) / namespace
        self.root.mkdir(parents=True, exist_ok=True)
        self.retention_days = retention_days
        self.compress = compress
        self._uploader = uploader

    # -- writing ---------------------------------------------------------- #

    def save(self, key: str, data: Any, *, metadata: dict[str, Any] | None = None) -> Path:
        """Persist a snapshot and return the file it was written to."""
        now = datetime.now(timezone.utc)
        stamp = now.strftime("%Y%m%dT%H%M%S%f")
        suffix = ".json.gz" if self.compress else ".json"
        path = self.root / f"{_slug(key)}__{stamp}{suffix}"

        payload = {
            "schema_version": _SCHEMA_VERSION,
            "namespace": self.namespace,
            "key": key,
            "timestamp": now.isoformat(),
            "metadata": sanitise(metadata or {}),
            "data": sanitise(data),
        }

        opener = gzip.open if self.compress else open
        with opener(path, "wt", encoding="utf-8") as handle:  # type: ignore[operator]
            json.dump(payload, handle, ensure_ascii=False)

        if self._uploader is not None:
            remote_key = f"{self.namespace}/{_slug(key)}/{now:%Y/%m/%d}/{path.name}"
            try:
                self._uploader(path, remote_key)
            except Exception as exc:  # never let a backup failure break the flow
                log.warning("State backup failed", extra={"key": key, "error": str(exc)})

        log.debug("State saved", extra={"key": key, "path": str(path)})
        return path

    # -- reading ---------------------------------------------------------- #

    def entries(self, key: str | None = None) -> list[StateEntry]:
        """All snapshots, newest first."""
        pattern = f"{_slug(key)}__*" if key else "*__*"
        found: list[StateEntry] = []
        for path in self.root.glob(pattern):
            if path.suffix not in {".gz", ".json"}:
                continue
            try:
                payload = _read(path)
            except (OSError, json.JSONDecodeError, EOFError):
                log.warning("Unreadable state file", extra={"path": str(path)})
                continue
            found.append(
                StateEntry(
                    key=payload.get("key", ""),
                    timestamp=datetime.fromisoformat(payload["timestamp"]),
                    path=path,
                    metadata=payload.get("metadata", {}),
                )
            )
        return sorted(found, key=lambda entry: entry.timestamp, reverse=True)

    def load_latest(self, key: str, default: Any = None) -> Any:
        for entry in self.entries(key):
            return entry.load()
        return default

    def load_previous(self, key: str, default: Any = None) -> Any:
        """The snapshot before the most recent one — what "did anything change?" needs."""
        entries = self.entries(key)
        if len(entries) < 2:
            return default
        return entries[1].load()

    def history(self, key: str, limit: int = 20) -> Iterator[Any]:
        for entry in self.entries(key)[:limit]:
            yield entry.load()

    # -- housekeeping ------------------------------------------------------ #

    def prune(self, *, keep_last: int = 5) -> int:
        """Delete snapshots older than the retention window, always keeping the newest N."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.retention_days)
        removed = 0
        by_key: dict[str, list[StateEntry]] = {}
        for entry in self.entries():
            by_key.setdefault(entry.key, []).append(entry)
        for entries in by_key.values():
            for entry in entries[keep_last:]:
                if entry.timestamp < cutoff:
                    entry.path.unlink(missing_ok=True)
                    removed += 1
        if removed:
            log.info("Pruned state snapshots", extra={"removed": removed})
        return removed

    def disk_usage_bytes(self) -> int:
        return sum(p.stat().st_size for p in self.root.rglob("*") if p.is_file())


def _slug(value: str | None) -> str:
    if not value:
        return "state"
    return "".join(char if char.isalnum() or char in "-_" else "-" for char in value)


def unix_millis() -> int:
    """Pathway's ``time`` column expects epoch milliseconds."""
    return int(time.time() * 1000)
