"""FastAPI scoring service.

Run with::

    uvicorn fraudguard.rps.service:app --host 0.0.0.0 --port 9000

Replaces ``rps/src/service/api.py``, which was a five-line app with no
validation, no health check, no error handling and no model provenance — a
malformed request produced a 500 with a stack trace, and a missing ``.pkl``
crashed the worker at import time.
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from fraudguard.errors import ScoringError
from fraudguard.logging import configure, get_logger
from fraudguard.rps import engine
from fraudguard.rps.registry import get_registry

log = get_logger("fraudguard.rps.service")

app = FastAPI(
    title="FraudGuard — Risk Propensity Scorer",
    description=(
        "Fuses a supervised model, an anomaly detector and a Bayesian rule engine "
        "into a single risk propensity score."
    ),
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------------- #


class ScoreRequest(BaseModel):
    features: dict[str, Any] = Field(
        ...,
        description="Windowed transaction aggregates keyed by training feature name.",
        json_schema_extra={
            "example": {
                "total_amount_1h": 1200,
                "txn_count_1h": 3,
                "unique_cp_1h": 1,
                "avg_amount_1h": 400,
                "max_amount_1h": 900,
                "min_amount_1h": 100,
                "incoming_outgoing_ratio_7d": 1.2,
            }
        },
    )
    explain: bool = Field(
        default=False, description="Include rule hits and model provenance in the response."
    )


class ScoreResponse(BaseModel):
    p_ml: float
    anomaly: float
    evidence: float
    rps: float
    risk_band: str
    model_version: str
    fired_rules: list[str] | None = None
    rule_hits: dict[str, bool] | None = None
    missing_features: list[str] | None = None


class BatchScoreRequest(BaseModel):
    items: list[ScoreRequest] = Field(..., max_length=500)


# --------------------------------------------------------------------------- #
# Lifecycle & middleware
# --------------------------------------------------------------------------- #


@app.on_event("startup")
def _startup() -> None:
    configure("rps-service")
    try:
        engine.warmup()
    except ScoringError as exc:
        # Start anyway so /healthz can report *why* we are unhealthy instead of
        # the container crash-looping with no diagnostics.
        log.error("Scorer failed to warm up", extra={"error": str(exc)})


@app.middleware("http")
async def _access_log(request: Request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Response-Time-ms"] = f"{(time.perf_counter() - started) * 1000:.1f}"
    log.info(
        "%s %s -> %s",
        request.method,
        request.url.path,
        response.status_code,
        extra={"duration_ms": round((time.perf_counter() - started) * 1000, 2)},
    )
    return response


@app.exception_handler(ScoringError)
async def _scoring_error(_: Request, exc: ScoringError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": "scoring_failed", "detail": str(exc)},
    )


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #


def _to_response(result: engine.RpsResult, explain: bool) -> ScoreResponse:
    payload = ScoreResponse(
        p_ml=result.p_ml,
        anomaly=result.anomaly,
        evidence=result.evidence,
        rps=result.rps,
        risk_band=result.risk_band,
        model_version=result.model_version,
    )
    if explain:
        payload.fired_rules = result.fired_rules
        payload.rule_hits = result.rule_hits
        payload.missing_features = result.missing_features
    return payload


@app.post("/score", response_model=ScoreResponse, summary="Score one feature vector")
def score(request: ScoreRequest) -> ScoreResponse:
    return _to_response(engine.score(request.features), request.explain)


@app.post("/score/batch", summary="Score up to 500 feature vectors")
def score_batch(request: BatchScoreRequest) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    failures = 0
    for index, item in enumerate(request.items):
        try:
            results.append(_to_response(engine.score(item.features), item.explain).model_dump())
        except ScoringError as exc:
            failures += 1
            results.append({"index": index, "error": str(exc)})
    return {"count": len(results), "failures": failures, "results": results}


@app.get("/healthz", summary="Liveness and readiness")
def healthz() -> JSONResponse:
    state = engine.engine_status()
    code = status.HTTP_200_OK if state.get("ready") else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=code, content=state)


@app.get("/model", summary="Model provenance")
def model_info() -> dict[str, Any]:
    return get_registry().summary()


@app.get("/features", summary="Feature contract expected by the model")
def features() -> dict[str, Any]:
    names = get_registry().training_features()
    if not names:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="training_features.json is missing; retrain or restore ml/models/",
        )
    return {"count": len(names), "features": names}
