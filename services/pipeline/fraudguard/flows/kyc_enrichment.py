"""KYC enrichment flow — ``entities`` topic in, ``db_updates`` topic out.

For every applicant published by the OCR flow this graph:

1. screens the name against OpenSanctions,
2. searches for adverse media, fetches and rates each article,
3. asks the compliance LLM for a risk verdict,
4. computes the same verdict deterministically and records the deviation,
5. publishes the enriched report to Kafka and to append-only JSONL audit files.

Structural changes from the original ``main.py``:

* the LLM prompt builder was invoked **twice per row** — once for the system
  prompt and once for the user prompt — doubling every scrape, every OTX lookup
  and every authenticity call.  It now runs once and both halves are read from
  the result.
* the enrichment stage is a single UDF, so an entity's evidence is gathered once
  and shared by the prompt, the deterministic score and the audit record.
* an LLM failure produced an unparseable row that crashed the downstream parse;
  it now falls back to the deterministic score with ``verdict_source`` recorded.
"""

from __future__ import annotations

import time
from typing import Any

import pathway as pw

from fraudguard import scoring
from fraudguard.enrichment.opensanctions import screen
from fraudguard.enrichment.web_analysis import analyse
from fraudguard.errors import FraudGuardError
from fraudguard.flows._runtime import FlowContext, flow_main
from fraudguard.llm import client as llm_client
from fraudguard.llm import prompts
from fraudguard.logging import get_logger, log_context
from fraudguard.schemas import EntitySchema
from fraudguard.udfs import _extract_json_and_summary

log = get_logger("fraudguard.flows.kyc")

FLOW_NAME = "kyc-enrichment"


@pw.udf(return_type=dict, deterministic=False)
def assess_entity(
    entity_id: str,
    applicant_name: str,
    date_of_birth: str,
    nationality: str,
    face_match_urls: list[str],
    annual_income: str,
    occupation: str,
    sources_of_income: list[str],
    marital_status: str,
    current_address: str,
) -> dict:
    """Screen, research and score one applicant.

    Returns a flat dict so the Pathway graph can project the columns it needs
    without re-running any of the expensive I/O.
    """
    with log_context(entity_id=entity_id, subject=applicant_name):
        started = time.perf_counter()

        sanctions = screen(applicant_name, date_of_birth, nationality, applicant_name)
        web = analyse(applicant_name, face_match_urls or [])

        reference = scoring.assess(
            entity_name=applicant_name,
            sanction_matches=sanctions.match_count,
            match_confidence=sanctions.score,
            articles=web.evidence,
        )

        verdict = reference.to_risk_json()
        summary = reference.summary
        verdict_source = "deterministic"
        audit: dict[str, Any] = {}
        llm_text = ""

        user_prompt = prompts.compliance_user_prompt(
            name=applicant_name,
            top_match=sanctions.entity_name,
            score=sanctions.score,
            web_notes=web.prompt,
            nationality=nationality,
            occupation=occupation,
            annual_income=annual_income,
            marital_status=marital_status,
            current_address=current_address,
            sources_of_income=sources_of_income,
        )

        try:
            llm_text = llm_client.complete(
                prompts.COMPLIANCE_SYSTEM_PROMPT, user_prompt, validate_output=False
            )
            parsed, parsed_summary = _extract_json_and_summary(llm_text)
            if parsed.get("risk_score") is not None:
                verdict = {
                    "risk_score": scoring.clamp01(parsed.get("risk_score")),
                    "risk_classification": str(
                        parsed.get("risk_classification") or reference.risk_classification
                    ).upper(),
                    "match_found": bool(parsed.get("match_found", reference.match_found)),
                }
                summary = parsed_summary or reference.summary
                verdict_source = "llm"
                audit = scoring.deviation(verdict, reference)
                if not audit["within_tolerance"]:
                    log.warning("LLM score deviates from the deterministic reference", extra=audit)
        except FraudGuardError as exc:
            log.warning(
                "Compliance LLM unavailable, using the deterministic verdict",
                extra={"error": str(exc)[:300]},
            )
            audit = {"llm_error": str(exc)[:300]}

        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        log.info(
            "Entity assessed",
            extra={
                "risk_score": verdict["risk_score"],
                "band": verdict["risk_classification"],
                "source": verdict_source,
                "articles": len(web.findings),
                "sanction_matches": sanctions.match_count,
                "duration_ms": elapsed_ms,
            },
        )

        return {
            "os_entity_id": sanctions.entity_id,
            "os_entity_name": sanctions.entity_name,
            "os_score": sanctions.score,
            "os_match_count": sanctions.match_count,
            "os_error": sanctions.error,
            "web_prompt": web.prompt,
            "citations": web.citations,
            "web_sources": web.to_dict()["sources"],
            "risk_json": verdict,
            "summary": summary,
            "verdict_source": verdict_source,
            "score_audit": audit,
            "reference_score": reference.to_dict(),
            "llm_text": llm_text,
            "duration_ms": elapsed_ms,
        }


def build(context: FlowContext) -> None:
    context.require("OS_API_KEY")

    entities = pw.io.kafka.read(
        context.kafka,
        topic=context.topics.entities_topic,
        format="json",
        schema=EntitySchema,
        autocommit_duration_ms=context.topics.autocommit_duration_ms,
    )
    pw.io.jsonlines.write(entities, context.out("raw_ingest.jsonl"))

    assessed = entities.with_columns(
        _assessment=assess_entity(
            pw.this.entity_id,
            pw.this.applicant_name,
            pw.this.date_of_birth,
            pw.this.nationality,
            pw.this.face_match_urls,
            pw.this.annual_income,
            pw.this.occupation,
            pw.this.sources_of_income,
            pw.this.marital_status,
            pw.this.current_address,
        )
    ).with_columns(
        os_entity_id=pw.this._assessment["os_entity_id"],
        os_entity_name=pw.this._assessment["os_entity_name"],
        os_score=pw.this._assessment["os_score"],
        os_match_count=pw.this._assessment["os_match_count"],
        citations=pw.this._assessment["citations"],
        risk_json=pw.this._assessment["risk_json"],
        summary=pw.this._assessment["summary"],
        score_audit=pw.this._assessment["score_audit"],
        timestamp=time.time(),
    )

    # Audit trail: one append-only file per stage, exactly as before but with the
    # raw completion kept out of the operational stream.
    pw.io.jsonlines.write(
        assessed.select(
            entity_id=pw.this.entity_id,
            name=pw.this.applicant_name,
            os_entity_id=pw.this.os_entity_id,
            os_entity_name=pw.this.os_entity_name,
            os_score=pw.this.os_score,
            os_match_count=pw.this.os_match_count,
            os_error=pw.this._assessment["os_error"],
        ),
        context.out("opensanctions_results.jsonl"),
    )
    pw.io.jsonlines.write(
        assessed.select(
            entity_id=pw.this.entity_id,
            name=pw.this.applicant_name,
            web_prompt=pw.this._assessment["web_prompt"],
            sources=pw.this._assessment["web_sources"],
            citations=pw.this.citations,
        ),
        context.out("web_analysis_debug.jsonl"),
    )
    pw.io.jsonlines.write(
        assessed.select(
            entity_id=pw.this.entity_id,
            name=pw.this.applicant_name,
            verdict_source=pw.this._assessment["verdict_source"],
            llm_text=pw.this._assessment["llm_text"],
            reference_score=pw.this._assessment["reference_score"],
            score_audit=pw.this.score_audit,
            duration_ms=pw.this._assessment["duration_ms"],
        ),
        context.out("llm_debug.jsonl"),
    )

    report = assessed.without("_assessment")
    pw.io.jsonlines.write(report, context.out("reports.jsonl"))

    latest = report.groupby(pw.this.entity_id).reduce(
        entity_id=pw.this.entity_id,
        name=pw.reducers.latest(pw.this.applicant_name),
        os_entity_name=pw.reducers.latest(pw.this.os_entity_name),
        os_score=pw.reducers.latest(pw.this.os_score),
        risk_json=pw.reducers.latest(pw.this.risk_json),
        summary=pw.reducers.latest(pw.this.summary),
        citations=pw.reducers.latest(pw.this.citations),
        score_audit=pw.reducers.latest(pw.this.score_audit),
        timestamp=pw.reducers.max(pw.this.timestamp),
    )
    pw.io.fs.write(latest, filename=context.out("latest.jsonl"), format="json")

    pw.io.kafka.write(
        report,
        context.kafka,
        topic_name=context.topics.db_updates_topic,
        format="json",
    )
    context.log.info(
        "Graph built",
        extra={
            "in_topic": context.topics.entities_topic,
            "out_topic": context.topics.db_updates_topic,
        },
    )


main = flow_main(FLOW_NAME, build, persistent=True)

if __name__ == "__main__":
    raise SystemExit(main())
