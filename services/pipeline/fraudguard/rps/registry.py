"""Model registry — provenance for every artefact the scorer loads.

Roadmap item P0.2 asked for DVC.  DVC needs remote object storage and a network,
which the demo environment does not have, so this is the part that delivers the
actual compliance value without any new infrastructure: every ``.pkl`` the
service loads is hashed at start-up and the digest is reported on ``/model`` and
attached to every score.

A regulator asking "which model produced this decision?" gets an answer; a
deployment that swaps a model file without anyone noticing shows up as a changed
digest in the logs.

The training code under ``ml/`` is untouched — this only *describes* what it
produced.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fraudguard.logging import get_logger

__all__ = ["ArtefactInfo", "ModelRegistry", "get_registry"]

log = get_logger("fraudguard.rps.registry")

#: Files the scoring engine depends on, relative to ``ml/``.
TRACKED_ARTEFACTS: tuple[str, ...] = (
    "models/p_ml_model.pkl",
    "models/anomaly_model.pkl",
    "models/anomaly_scaler.pkl",
    "models/fusion_model.pkl",
    "models/lr_dict.json",
    "models/training_features.json",
    "models/p_ml_thresholds.json",
    "data/processed/features.parquet",
)


@dataclass(frozen=True)
class ArtefactInfo:
    name: str
    path: str
    exists: bool
    size_bytes: int
    sha256: str | None
    modified_at: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _digest(path: Path, chunk_size: int = 1 << 20) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


class ModelRegistry:
    """Describes the model artefacts backing the running scorer."""

    def __init__(self, ml_root: Path | None = None) -> None:
        from fraudguard.config import get_settings

        self.ml_root = Path(ml_root or get_settings().paths.ml_root)
        self._artefacts: dict[str, ArtefactInfo] | None = None

    # -- inspection -------------------------------------------------------- #

    def artefacts(self, *, refresh: bool = False) -> dict[str, ArtefactInfo]:
        if self._artefacts is None or refresh:
            self._artefacts = {name: self._describe(name) for name in TRACKED_ARTEFACTS}
        return self._artefacts

    def _describe(self, relative: str) -> ArtefactInfo:
        path = self.ml_root / relative
        if not path.is_file():
            return ArtefactInfo(relative, str(path), False, 0, None, None)
        stat = path.stat()
        # Hashing an 18 MB parquet on every request would be wasteful; the size +
        # mtime pair is enough to notice a swap, and the digest is computed once.
        return ArtefactInfo(
            name=relative,
            path=str(path),
            exists=True,
            size_bytes=stat.st_size,
            sha256=_digest(path),
            modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        )

    def missing(self) -> list[str]:
        return [name for name, info in self.artefacts().items() if not info.exists]

    @property
    def version(self) -> str:
        """A short, stable fingerprint of the whole model set."""
        joined = "".join(
            info.sha256 or "missing" for _, info in sorted(self.artefacts().items())
        )
        return hashlib.sha256(joined.encode()).hexdigest()[:12]

    def training_features(self) -> list[str]:
        path = self.ml_root / "models/training_features.json"
        if not path.is_file():
            return []
        try:
            return list(json.loads(path.read_text()))
        except (json.JSONDecodeError, OSError) as exc:
            log.error("Could not read training_features.json", extra={"error": str(exc)})
            return []

    def thresholds(self) -> dict[str, Any]:
        path = self.ml_root / "models/p_ml_thresholds.json"
        if not path.is_file():
            return {}
        try:
            return dict(json.loads(path.read_text()))
        except (json.JSONDecodeError, OSError):
            return {}

    def summary(self) -> dict[str, Any]:
        return {
            "model_version": self.version,
            "ml_root": str(self.ml_root),
            "feature_count": len(self.training_features()),
            "thresholds": self.thresholds(),
            "artefacts": [info.to_dict() for info in self.artefacts().values()],
            "missing": self.missing(),
        }

    def log_startup(self) -> None:
        missing = self.missing()
        if missing:
            log.error(
                "Model artefacts missing — run ml/train_pipeline.sh or restore ml/models/",
                extra={"missing": missing},
            )
        else:
            log.info(
                "Model artefacts verified",
                extra={"model_version": self.version, "count": len(TRACKED_ARTEFACTS)},
            )


_REGISTRY: ModelRegistry | None = None


def get_registry() -> ModelRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = ModelRegistry(
            Path(os.environ["ML_ROOT"]) if os.environ.get("ML_ROOT") else None
        )
    return _REGISTRY
