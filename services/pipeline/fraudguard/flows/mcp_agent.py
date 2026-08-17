"""Agentic validation flow — ``possible_fraud`` in, ``compliance_alerts`` table out.

High-risk transaction verdicts are handed to a CrewAI agent that decides, per
case, whether an external sanctions/PEP check is warranted, calls the MCP tools
if so, and returns a written validation.  The result becomes a compliance alert
for the review queue.

Replaces ``mcp/mcp_client.py``:

* the CrewAI ``MCPClient.__init__`` was monkey-patched at import to force a
  timeout — the same thing the constructor argument does, done in a way that
  breaks on any upstream signature change.  The timeout is passed normally;
* ``os.environ["GOOGLE_API_KEY"] = os.environ["ALT_GOOGLE_API_KEY"]`` raised
  ``KeyError`` at import when the alt key was absent;
* ``try: table.with_columns(agent_udf(...)) except: fallback`` wrapped *graph
  construction*, so the fallback could never run — a UDF failure at run time
  killed the flow.  The fallback now lives inside the UDF, where the call
  actually happens;
* ``make_uuid(user_id)`` ignored its argument and returned a random UUID, so the
  ``entity_id`` on an alert had no relationship to the entity.  It is now a
  deterministic UUID5 derived from the user and the verdict.
"""

from __future__ import annotations

import json
import threading
import uuid
from typing import Any

import pathway as pw

from fraudguard.flows._runtime import FlowContext, flow_main
from fraudguard.llm import prompts
from fraudguard.logging import get_logger, log_context
from fraudguard.risk_updates import update_rps
from fraudguard.schemas import RpsVerdictSchema

log = get_logger("fraudguard.flows.mcp_agent")

FLOW_NAME = "mcp-agent"

ALERTS_TABLE = "compliance_alerts"

#: Only verdicts above this score are worth an agent call.
ESCALATION_THRESHOLD = 0.4

#: Namespace for deterministic alert entity ids.
_ALERT_NAMESPACE = uuid.UUID("6f4d5b6c-2f8f-4d7e-9c1a-5b2e7c9d3a10")

_AGENT: Any | None = None
_AGENT_LOCK = threading.Lock()


def _get_agent() -> Any:
    """Build the CrewAI agent once, wired to the MCP tool server."""
    global _AGENT
    if _AGENT is None:
        with _AGENT_LOCK:
            if _AGENT is None:
                from crewai import Agent
                from crewai.mcp import MCPServerHTTP

                from fraudguard.config import ConfigError, get_settings

                settings = get_settings()
                if not settings.llm.gemini_key:
                    raise ConfigError(
                        "GEMINI_API_KEY (or GOOGLE_API_KEY) is required for the MCP agent."
                    )
                # CrewAI reads the Google credential from the environment.
                import os

                os.environ.setdefault("GOOGLE_API_KEY", settings.llm.gemini_key)

                server = MCPServerHTTP(
                    url=settings.mcp_url,
                    streamable=True,
                    cache_tools_list=True,
                )
                _AGENT = Agent(
                    role="Financial crime risk analyst",
                    goal=(
                        "Decide which sanctions and PEP checks are warranted and validate the "
                        "risk propensity score with the evidence they return."
                    ),
                    backstory=(
                        "A compliance analyst who reviews automated fraud alerts, questions the "
                        "model's reasoning and escalates only what survives external validation."
                    ),
                    mcps=[server],
                )
                log.info("MCP agent ready", extra={"mcp_url": settings.mcp_url})
    return _AGENT


def _fallback_validation(short_reason: str, long_reason: str, recommended_action: str) -> str:
    return (
        f"{short_reason}\n{long_reason}\n"
        f"System recommendation: {recommended_action}\n"
        "VERDICT: INCONCLUSIVE (agent unavailable; no external validation performed)"
    )


@pw.udf(deterministic=False)
def validate_with_agent(
    full_name: str,
    rps: float,
    risk_level: str,
    anomaly: float,
    p_ml: float,
    evidence: float,
    tags: str,
    short_reason: str,
    long_reason: str,
    recommended_action: str,
) -> str:
    """Run the agent for one case; degrade to the model's own reasoning on failure."""
    with log_context(subject=full_name, rps=round(float(rps), 4)):
        try:
            parsed_tags = json.loads(tags) if tags else []
        except (json.JSONDecodeError, TypeError):
            parsed_tags = [tags] if tags else []

        prompt = prompts.mcp_agent_prompt(
            full_name=full_name,
            risk_level=risk_level,
            anomaly=float(anomaly),
            rps=float(rps),
            p_ml=float(p_ml),
            evidence=float(evidence),
            tags=parsed_tags,
            short_reason=short_reason,
            long_reason=long_reason,
            recommended_action=recommended_action,
        )
        try:
            result = _get_agent().kickoff(prompt)
            text = getattr(result, "raw", None) or str(result)
            log.info("Agent validation complete", extra={"chars": len(text)})
            return text
        except Exception as exc:
            log.warning("Agent validation failed", extra={"error": str(exc)[:300]})
            return _fallback_validation(short_reason, long_reason, recommended_action)


@pw.udf
def alert_title(full_name: str) -> str:
    return f"Compliance alert for {full_name}"


@pw.udf
def alert_entity_id(user_id: int, rps: float) -> str:
    """Stable identifier for this (user, score) alert."""
    return str(uuid.uuid5(_ALERT_NAMESPACE, f"{user_id}:{rps:.6f}"))


@pw.udf
def severity_from_level(risk_level: str) -> str:
    """Map the model's band onto the ``compliance_alerts`` CHECK constraint.

    The table only accepts low/medium/high/critical; the pipeline emits
    LOW/MEDIUM/HIGH, and the original wrote them through unchanged, so every
    insert violated the constraint and the alert was lost.
    """
    mapping = {"LOW": "low", "MEDIUM": "medium", "HIGH": "high", "CRITICAL": "critical"}
    return mapping.get(str(risk_level).strip().upper(), "medium")


@pw.udf
def tags_to_text(tags: str) -> str:
    try:
        return ", ".join(json.loads(tags))
    except (json.JSONDecodeError, TypeError):
        return str(tags or "")


def build(context: FlowContext) -> None:
    context.require("POSTGRES_PASSWORD")

    verdicts = pw.io.kafka.read(
        context.kafka,
        topic=context.topics.fraud_topic,
        format="json",
        schema=RpsVerdictSchema,
        autocommit_duration_ms=context.topics.autocommit_duration_ms,
    )

    escalated = verdicts.filter(pw.this.rps > ESCALATION_THRESHOLD)

    validated = escalated.with_columns(
        standing_rps=update_rps(pw.this.user_id, pw.this.rps),
        validation=validate_with_agent(
            pw.this.full_name,
            pw.this.rps,
            pw.this.risk_level,
            pw.this.anomaly,
            pw.this.p_ml,
            pw.this.evidence,
            pw.this.tags,
            pw.this.short_reason,
            pw.this.long_reason,
            pw.this.recommended_action,
        ),
    )

    pw.io.jsonlines.write(validated, context.out("agent_validations.jsonl"))

    alerts = validated.select(
        user_id=pw.this.user_id,
        alert_type="transaction_alert",
        triggered_by="transaction_monitoring_system",
        source="fraudguard-mcp-agent",
        title=alert_title(pw.this.full_name),
        description=pw.this.validation,
        severity=severity_from_level(pw.this.risk_level),
        priority=severity_from_level(pw.this.risk_level),
        status="active",
        rps360=pw.this.rps,
        entity_id=alert_entity_id(pw.this.user_id, pw.this.rps),
        entity_type="user",
        alert_metadata=tags_to_text(pw.this.tags),
    )

    pw.io.postgres.write(alerts, context.settings.postgres.connection_parts, table_name=ALERTS_TABLE)
    context.log.info(
        "Graph built",
        extra={
            "in_topic": context.topics.fraud_topic,
            "table": ALERTS_TABLE,
            "threshold": ESCALATION_THRESHOLD,
        },
    )


main = flow_main(FLOW_NAME, build, persistent=True)

if __name__ == "__main__":
    raise SystemExit(main())
