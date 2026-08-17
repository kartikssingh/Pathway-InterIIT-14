"""Transaction feature flow — Debezium CDC in, ``rps_processed_features`` out.

Every committed row on ``public.transactions`` triggers a fresh point-in-time
feature vector for that user, which is published for the scoring/explanation
flow to consume.

Replaces ``rps/src/WatchDog.py``.  Besides the windowing bugs documented in
:mod:`fraudguard.features`, that module also:

* opened one global psycopg2 cursor at import and used it from inside UDFs
  (Pathway runs UDFs concurrently; a shared cursor is not thread-safe);
* wrote the score back to ``Users.rps_360`` from inside the "call the API" UDF,
  mixing a side effect into what looked like a pure lookup — and swallowed every
  failure as ``0.0``, which is indistinguishable from a genuinely clean user;
* built ``feat_json`` from only the 16 float columns, so the eight ``txn_count``/
  ``unique_cp`` features the model expects were always imputed as zero.
"""

from __future__ import annotations

import pathway as pw

from fraudguard.features import build_feature_vector, lookup_username
from fraudguard.flows._runtime import FlowContext, flow_main
from fraudguard.logging import get_logger, log_context
from fraudguard.schemas import (
    FEATURE_FLOAT_COLUMNS,
    FEATURE_INT_COLUMNS,
    TransactionSchema,
)

log = get_logger("fraudguard.flows.rps_features")

FLOW_NAME = "rps-features"


@pw.udf(return_type=dict, deterministic=False)
def compute_features(user_id: int) -> dict:
    """Point-in-time feature vector plus the display name, for one user."""
    with log_context(user_id=user_id):
        features = build_feature_vector(int(user_id))
        payload: dict = {"user_id": int(user_id), "full_name": lookup_username(int(user_id))}
        payload.update(features)
        log.debug(
            "Features computed",
            extra={"txn_count_30d": features.get("txn_count_30d", 0)},
        )
        return payload


def build(context: FlowContext) -> None:
    context.require("POSTGRES_PASSWORD")

    transactions = pw.io.debezium.read(
        context.kafka,
        topic_name=context.topics.transactions_cdc_topic,
        schema=TransactionSchema,
        autocommit_duration_ms=context.topics.autocommit_duration_ms,
    )
    pw.io.jsonlines.write(transactions, context.out("cdc_transactions.jsonl"))

    # One vector per affected user; duplicate events for the same user in the
    # same commit collapse here rather than triggering four identical queries.
    per_user = transactions.groupby(pw.this.user_id).reduce(
        user_id=pw.this.user_id,
        last_transaction_id=pw.reducers.latest(pw.this.transaction_id),
        last_amount=pw.reducers.latest(pw.this.amount),
    )

    enriched = per_user.with_columns(_features=compute_features(pw.this.user_id))

    # Counts stay integral and amounts stay floating point, matching
    # TransactionFeaturesSchema on the consuming side.
    features = enriched.select(
        user_id=pw.this._features["user_id"].as_int(),
        full_name=pw.this._features["full_name"].as_str(),
        **{name: pw.this._features[name].as_float() for name in FEATURE_FLOAT_COLUMNS},
        **{name: pw.this._features[name].as_int() for name in FEATURE_INT_COLUMNS},
    )

    pw.io.jsonlines.write(features, context.out("rps_features.jsonl"))
    pw.io.kafka.write(
        features,
        context.kafka,
        topic_name=context.topics.rps_features_topic,
        format="json",
    )
    context.log.info(
        "Graph built",
        extra={
            "in_topic": context.topics.transactions_cdc_topic,
            "out_topic": context.topics.rps_features_topic,
        },
    )


main = flow_main(FLOW_NAME, build, persistent=True)

if __name__ == "__main__":
    raise SystemExit(main())
