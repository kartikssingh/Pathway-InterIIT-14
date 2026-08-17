"""Risk Propensity Score inference.

Fuses four signals into a single score:

1. ``p_ml``    — supervised CatBoost probability of fraud;
2. ``anomaly`` — scaled Isolation-Forest decision function;
3. ``evidence``— Bayesian posterior from deterministic rule hits;
4. ``rps``     — logistic-regression fusion of the three.

The **models and the training code are untouched**: this module only loads the
artefacts produced by ``ml/train_pipeline.sh`` and calls them.  The rule engine,
evidence and prior helpers are imported from ``ml/`` exactly as the training
pipeline uses them, so inference and training can never diverge.

What changed relative to the old ``rps/src/service/rps_engine.py``:

* models were loaded at *import* time from a hard-coded ``rps/src/`` relative
  path, so importing the module from any other working directory crashed;
  loading is now lazy, thread-safe and rooted at the configured ``ml/`` dir;
* ``logit()`` divided by ``(1 - eps)`` instead of ``(1 - x)`` — a genuine bug
  that made the fusion input wrong for every request.  Fixed, with the original
  behaviour available behind ``RPS_LEGACY_LOGIT=true`` for score comparability
  with previously stored results;
* every score now carries the model version, the rule hits and the feature
  vector actually used, so decisions are explainable and auditable.
"""

from __future__ import annotations

import math
import os
import sys
import threading
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

from fraudguard.errors import ScoringError
from fraudguard.logging import get_logger
from fraudguard.rps.registry import get_registry
from fraudguard.scoring import rps_band

__all__ = ["RpsResult", "score", "warmup", "engine_status"]

log = get_logger("fraudguard.rps.engine")

_LOCK = threading.Lock()
_LOADED = False
_STATE: dict[str, Any] = {}

#: The original implementation's logit; kept for reproducing historical scores.
_LEGACY_LOGIT = os.environ.get("RPS_LEGACY_LOGIT", "").lower() in {"1", "true", "yes"}


@dataclass
class RpsResult:
    p_ml: float
    anomaly: float
    evidence: float
    rps: float
    risk_band: str
    model_version: str
    rule_hits: dict[str, bool] = field(default_factory=dict)
    fired_rules: list[str] = field(default_factory=list)
    missing_features: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def scores_only(self) -> dict[str, float]:
        """The four numbers the rest of the pipeline consumes."""
        return {
            "p_ml": self.p_ml,
            "anomaly": self.anomaly,
            "evidence": self.evidence,
            "rps": self.rps,
        }


def _ml_root() -> Path:
    from fraudguard.config import get_settings

    return Path(get_settings().paths.ml_root)


def _load() -> dict[str, Any]:
    """Load models and rule helpers once, under a lock."""
    global _LOADED
    if _LOADED:
        return _STATE

    with _LOCK:
        if _LOADED:
            return _STATE

        import joblib

        registry = get_registry()
        registry.log_startup()
        missing = registry.missing()
        if missing:
            raise ScoringError(
                "Cannot start the scorer, missing model artefacts: " + ", ".join(missing)
            )

        root = _ml_root()
        # ``ml/`` holds the untouched training package; its modules import each
        # other as top-level names (``from rules.rule_engine import ...``), so it
        # goes on the path rather than being rewritten.
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))

        from rules.compute_prior import compute_prior  # noqa: E402  (path-dependent)
        from rules.evidence import compute_evidence  # noqa: E402
        from rules.rule_engine import evaluate_rules  # noqa: E402

        import json

        try:
            loaded = {
                "p_ml": joblib.load(root / "models/p_ml_model.pkl"),
                "anomaly": joblib.load(root / "models/anomaly_model.pkl"),
                "anomaly_scaler": joblib.load(root / "models/anomaly_scaler.pkl"),
                "fusion": joblib.load(root / "models/fusion_model.pkl"),
                "lr_dict": json.loads((root / "models/lr_dict.json").read_text()),
                "features": registry.training_features(),
                "prior": float(compute_prior(root / "data/processed/features.parquet")),
                "evaluate_rules": evaluate_rules,
                "compute_evidence": compute_evidence,
                "model_version": registry.version,
            }
        except ModuleNotFoundError as exc:
            # A pickled estimator pulls in the library that produced it.
            raise ScoringError(
                f"Cannot unpickle a model: {exc}. Install the training-time "
                "dependencies (see requirements.txt — catboost, scikit-learn)."
            ) from exc
        except Exception as exc:
            raise ScoringError(f"Model artefacts could not be loaded: {exc}") from exc

        _STATE.update(loaded)
        _LOADED = True
        log.info(
            "RPS engine loaded",
            extra={
                "model_version": _STATE["model_version"],
                "features": len(_STATE["features"]),
                "prior": round(_STATE["prior"], 6),
            },
        )
    return _STATE


def warmup() -> None:
    """Load everything eagerly (called on API start-up so the first request is fast)."""
    _load()


def engine_status() -> dict[str, Any]:
    """Health payload for ``/healthz``."""
    try:
        state = _load()
    except ScoringError as exc:
        return {"ready": False, "error": str(exc)}
    return {
        "ready": True,
        "model_version": state["model_version"],
        "feature_count": len(state["features"]),
        "prior": state["prior"],
        "legacy_logit": _LEGACY_LOGIT,
    }


def _logit(value: float, eps: float = 1e-9) -> float:
    clipped = min(max(value, eps), 1.0 - eps)
    if _LEGACY_LOGIT:
        # Reproduces the original (incorrect) expression: log(x / (1 - eps)).
        return math.log(clipped / (1.0 - eps))
    return math.log(clipped / (1.0 - clipped))


def _frame(features: Mapping[str, Any], expected: list[str]) -> tuple[pd.DataFrame, list[str]]:
    """Align an arbitrary feature dict to the training columns."""
    supplied = {key: value for key, value in features.items() if key in expected}
    missing = [column for column in expected if column not in supplied]
    frame = pd.DataFrame([supplied])
    frame = frame.reindex(columns=expected, fill_value=0)
    numeric = frame.apply(pd.to_numeric, errors="coerce").fillna(0.0)
    return numeric, missing


def score(features: Mapping[str, Any]) -> RpsResult:
    """Score one feature vector.

    Raises :class:`ScoringError` if the models cannot be loaded or the vector is
    unusable; never returns a silently-zero score.
    """
    if not isinstance(features, Mapping) or not features:
        raise ScoringError("features must be a non-empty mapping")

    state = _load()
    expected: list[str] = state["features"]
    frame, missing = _frame(features, expected)

    if missing and len(missing) == len(expected):
        raise ScoringError(
            "None of the expected training features were supplied; "
            f"expected e.g. {expected[:5]}"
        )
    if missing:
        log.warning(
            "Scoring with imputed features",
            extra={"missing_count": len(missing), "missing": missing[:10]},
        )

    try:
        p_ml = float(state["p_ml"].predict_proba(frame)[0][1])
        raw_anomaly = float(state["anomaly"].decision_function(frame)[0])
        anomaly = float(state["anomaly_scaler"].transform([[raw_anomaly]])[0][0])
    except Exception as exc:
        raise ScoringError(f"model inference failed: {exc}") from exc

    row = frame.iloc[0]
    rule_hits = {
        name: bool(value) for name, value in state["evaluate_rules"](row).items()
    }
    evidence = float(state["compute_evidence"](rule_hits, state["lr_dict"], state["prior"]))

    fusion_input = np.array([_logit(p_ml), _logit(anomaly), evidence]).reshape(1, -1)
    try:
        rps = float(state["fusion"].predict_proba(fusion_input)[0][1])
    except Exception as exc:
        raise ScoringError(f"fusion model failed: {exc}") from exc

    return RpsResult(
        p_ml=p_ml,
        anomaly=anomaly,
        evidence=evidence,
        rps=rps,
        risk_band=rps_band(rps),
        model_version=state["model_version"],
        rule_hits=rule_hits,
        fired_rules=sorted(name for name, hit in rule_hits.items() if hit),
        missing_features=missing,
    )
