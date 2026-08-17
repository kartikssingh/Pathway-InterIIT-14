"""Database sink — ``db_updates`` topic in, ``Staging_Buffer`` table out.

``Staging_Buffer`` is an insert-only landing table; an ``AFTER INSERT`` trigger
(``infra/postgres/migrations/030_staging_trigger.sql``) fans each row out to
``Users``, ``ToxicityHistory`` and ``UserSanctionMatches``.  Writing to one table
keeps the Pathway sink simple and makes the fan-out transactional.

Changes from the original ``database_update.py``:

* the write was wrapped in ``try/except`` around a *graph construction* call, so
  the handler could never fire — ``pw.io.postgres.write`` only declares the sink;
  errors surface at run time.  The bogus handler (and its ``print("AAAA...")``)
  is gone and real failures now propagate with context.
* ``risk_category`` was cast with ``pw.apply(str, ...)`` on a JSON value, which
  produced ``'"HIGH"'`` (with quotes) in the database.  It is extracted as a
  string properly.
* ``rps_not`` came from ``risk_json["risk_score"]`` while the fallback path
  produced a 0-100 number — the two scales are now both 0-1 (see
  :mod:`fraudguard.scoring`).
* the module ran ``pw.run()`` at import time, so merely importing it started a
  streaming job.
"""

from __future__ import annotations

import pathway as pw

from fraudguard.flows._runtime import FlowContext, flow_main
from fraudguard.schemas import EnrichedEntitySchema
from fraudguard.udfs import (
    coalesce_float,
    now_naive,
    parse_date,
    sha256_hex,
    sha256_signature,
    to_float_safe,
    to_int_safe,
)

FLOW_NAME = "db-sink"

STAGING_TABLE = "Staging_Buffer"


@pw.udf
def _json_str(value) -> str:
    """Read a JSON scalar as a plain Python string.

    ``pw.apply(str, json_value)`` renders the JSON representation (``'"HIGH"'``),
    which is not what a ``VARCHAR`` column wants.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    text = str(value)
    return text.strip('"')


@pw.udf
def _json_float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


@pw.udf
def _json_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes"}
    try:
        return bool(float(value))
    except (TypeError, ValueError):
        return False


def build(context: FlowContext) -> None:
    context.require("POSTGRES_PASSWORD")

    reports = pw.io.kafka.read(
        context.kafka,
        topic=context.topics.db_updates_topic,
        format="json",
        schema=EnrichedEntitySchema,
        autocommit_duration_ms=context.topics.autocommit_duration_ms,
    )

    normalised = reports.with_columns(
        entity_id=to_int_safe(pw.this.entity_id),
        date_of_birth=parse_date(pw.this.date_of_birth),
    )
    pw.io.jsonlines.write(normalised, context.out("entities_debug.jsonl"))

    staging = normalised.select(
        user_id=pw.this.entity_id,
        username=pw.this.applicant_name,
        profile_pic=pw.this.profile_pic,
        # Scores -------------------------------------------------------------
        rps_not=_json_float(pw.this.risk_json["risk_score"]),
        rps_360=0.0,
        news_score=0.0,
        transaction_score=0.0,
        portfolio_score=0.0,
        sanction_score=coalesce_float(pw.this.os_score),
        risk_category=_json_str(pw.this.risk_json["risk_classification"]),
        calculation_trigger="register",
        # Sanctions match ------------------------------------------------------
        match_found=_json_bool(pw.this.risk_json["match_found"]),
        match_confidence=pw.this.os_score,
        matched_entity_name=pw.this.os_entity_name,
        # Identity -------------------------------------------------------------
        uin=pw.this.unique_identification_number,
        uin_hash=sha256_hex(pw.this.unique_identification_number),
        email=pw.this.applicant_email,
        phone=pw.this.applicant_mobile_number,
        date_of_birth=pw.this.date_of_birth,
        address=pw.this.current_address,
        occupation=pw.this.occupation,
        annual_income=to_float_safe(pw.this.annual_income),
        signature_hash=sha256_signature(pw.this.applicant_name, pw.this.entity_id),
        kyc_status="PENDING_VERIFICATION",
        # Left for the operator / downstream jobs to populate ------------------
        credit_score=None,
        blacklisted=None,
        blacklisted_at=None,
        current_rps_not=None,
        current_rps_360=None,
        created_at=now_naive(pw.this.timestamp),
    )

    pw.io.postgres.write(
        staging,
        context.settings.postgres.connection_parts,
        table_name=STAGING_TABLE,
    )
    context.log.info(
        "Graph built",
        extra={
            "in_topic": context.topics.db_updates_topic,
            "table": STAGING_TABLE,
            "database": context.settings.postgres.dbname,
        },
    )


main = flow_main(FLOW_NAME, build, persistent=True)

if __name__ == "__main__":
    raise SystemExit(main())
