"""Scoring + explanation flow — ``rps_processed_features`` in, ``possible_fraud`` out.

For each feature vector: call the scoring service, ask the LLM to interpret the
result, and publish an explained verdict.

Replaces ``rps/src/service/llm.py``:

* it imported ``fastapi`` and raised ``HTTPException`` from inside a Pathway UDF
  — an HTTP framework exception in a stream processor, which then got caught by
  a bare ``except`` two frames up and turned into an all-``None`` row;
* the LLM fallback hard-coded ``rps = 0.0`` before computing a risk band, so
  every fallback claimed ``LOW`` regardless of the real score;
* the 27-argument UDF listed every feature by name three times (signature, dict
  literal, call site) — adding a feature meant editing three places;
* ``import re`` sat in the middle of an exception handler.
"""

from __future__ import annotations

import json
from typing import Any

import pathway as pw

from fraudguard.errors import FraudGuardError, ScoringError, UpstreamError
from fraudguard.flows._runtime import FlowContext, flow_main
from fraudguard.io.http import request_json
from fraudguard.llm import client as llm_client
from fraudguard.llm import prompts
from fraudguard.logging import get_logger, log_context
from fraudguard.schemas import FEATURE_COLUMNS, TransactionFeaturesSchema
from fraudguard.scoring import rps_band

log = get_logger("fraudguard.flows.rps_explain")

FLOW_NAME = "rps-explain"

_EXPLANATION_KEYS = ("risk_level", "short_reason", "long_reason", "recommended_action", "tags")


def _call_scorer(features: dict[str, Any]) -> dict[str, float]:
    """Score via the HTTP service, falling back to the in-process engine.

    Running the scorer as a separate service keeps model memory out of the
    stream worker, but there is no reason to fail when it is simply not up.
    """
    from fraudguard.config import get_settings

    url = get_settings().rps_score_url
    try:
        body = request_json("POST", url, service="rps-scorer", json_body={"features": features})
    except UpstreamError as exc:
        log.warning("Scoring service unreachable, scoring in-process", extra={"error": str(exc)})
        from fraudguard.rps import engine

        return engine.score(features).scores_only()

    missing = [key for key in ("p_ml", "anomaly", "evidence", "rps") if key not in body]
    if missing:
        raise ScoringError(f"scoring service response missing {missing}: {body}")
    return {key: float(body[key]) for key in ("p_ml", "anomaly", "evidence", "rps")}


def _fallback_explanation(rps: float, reason: str) -> dict[str, Any]:
    band = rps_band(rps)
    return {
        "risk_level": band,
        "short_reason": f"Explanation unavailable ({reason}); the model places this at {band} risk.",
        "long_reason": (
            "The language model could not be reached, so this explanation was produced by the "
            "deterministic band mapping over the fused risk propensity score. The numeric scores "
            "themselves are unaffected."
        ),
        "recommended_action": "Review the raw scores and fired rules; escalate if the band is HIGH.",
        "tags": ["llm_unavailable", "fallback"],
    }


def _explain(features: dict[str, Any], scores: dict[str, float]) -> dict[str, Any]:
    try:
        payload = llm_client.complete_json(
            prompts.RPS_EXPLANATION_SYSTEM_PROMPT,
            json.dumps({"features": features, "scores": scores}),
            attempts=2,
        )
    except FraudGuardError as exc:
        return _fallback_explanation(scores.get("rps", 0.0), str(exc)[:120])

    # The model occasionally omits a key or returns tags as a string.
    for key in _EXPLANATION_KEYS:
        if key not in payload:
            payload[key] = ["llm_missing_key"] if key == "tags" else f"[missing {key}]"
    if not isinstance(payload["tags"], list):
        payload["tags"] = [str(payload["tags"])]
    # Never let the narrative contradict the arithmetic.
    payload["risk_level"] = str(payload.get("risk_level") or "").upper() or rps_band(
        scores.get("rps", 0.0)
    )
    return payload


@pw.udf(return_type=dict, deterministic=False)
def score_and_explain(user_id: int, full_name: str, features: dict) -> dict:
    """Score a feature vector and attach a natural-language explanation."""
    with log_context(user_id=user_id, subject=full_name):
        try:
            scores = _call_scorer(features)
        except (ScoringError, FraudGuardError) as exc:
            log.error("Scoring failed", extra={"error": str(exc)})
            return {
                "user_id": int(user_id),
                "full_name": full_name,
                "p_ml": 0.0,
                "anomaly": 0.0,
                "evidence": 0.0,
                "rps": 0.0,
                "risk_level": "UNKNOWN",
                "short_reason": "Scoring failed.",
                "long_reason": str(exc)[:500],
                "recommended_action": "Investigate the scoring service; this row was not scored.",
                "tags": json.dumps(["scoring_error"]),
            }

        explanation = _explain(features, scores)
        log.info(
            "Transaction risk scored",
            extra={"rps": round(scores["rps"], 4), "band": explanation["risk_level"]},
        )
        return {
            "user_id": int(user_id),
            "full_name": full_name,
            **{key: float(value) for key, value in scores.items()},
            "risk_level": str(explanation["risk_level"]),
            "short_reason": str(explanation["short_reason"]),
            "long_reason": str(explanation["long_reason"]),
            "recommended_action": str(explanation["recommended_action"]),
            "tags": json.dumps(explanation["tags"]),
        }


def build(context: FlowContext) -> None:
    features = pw.io.kafka.read(
        context.kafka,
        topic=context.topics.rps_features_topic,
        schema=TransactionFeaturesSchema,
        format="json",
        autocommit_duration_ms=context.topics.autocommit_duration_ms,
    )
    pw.io.jsonlines.write(features, context.out("transactions_debug.jsonl"))

    from fraudguard.udfs import as_dict

    with_vector = features.with_columns(
        _vector=as_dict(**{name: features[name] for name in FEATURE_COLUMNS})
    )

    scored = with_vector.select(
        _result=score_and_explain(pw.this.user_id, pw.this.full_name, pw.this._vector)
    )

    verdicts = scored.select(
        user_id=pw.this._result["user_id"].as_int(),
        full_name=pw.this._result["full_name"].as_str(),
        p_ml=pw.this._result["p_ml"].as_float(),
        anomaly=pw.this._result["anomaly"].as_float(),
        evidence=pw.this._result["evidence"].as_float(),
        rps=pw.this._result["rps"].as_float(),
        risk_level=pw.this._result["risk_level"].as_str(),
        short_reason=pw.this._result["short_reason"].as_str(),
        long_reason=pw.this._result["long_reason"].as_str(),
        recommended_action=pw.this._result["recommended_action"].as_str(),
        tags=pw.this._result["tags"].as_str(),
    )

    pw.io.jsonlines.write(verdicts, context.out("rps_output.jsonl"))
    pw.io.kafka.write(
        verdicts,
        context.kafka,
        topic_name=context.topics.fraud_topic,
        format="json",
    )
    context.log.info(
        "Graph built",
        extra={
            "in_topic": context.topics.rps_features_topic,
            "out_topic": context.topics.fraud_topic,
            "score_url": context.settings.rps_score_url,
        },
    )


main = flow_main(FLOW_NAME, build, persistent=True)

if __name__ == "__main__":
    raise SystemExit(main())
