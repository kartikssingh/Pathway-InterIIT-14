"""Pathway schemas shared by every flow.

``EntitiesSchema`` used to be copy-pasted into ``main.py`` and ``watchdog.py``
and the two copies had already drifted (the watchdog version was missing
``profile_pic``), which meant the watchdog silently failed to deserialise
messages produced by the OCR flow.  One definition, one contract.
"""

from __future__ import annotations

import pathway as pw

__all__ = [
    "EntitySchema",
    "EnrichedEntitySchema",
    "TransactionSchema",
    "TransactionFeaturesSchema",
    "RpsVerdictSchema",
    "RagInputSchema",
    "FEATURE_COLUMNS",
    "FEATURE_FLOAT_COLUMNS",
    "FEATURE_INT_COLUMNS",
]


class EntitySchema(pw.Schema):
    """A KYC applicant as published to the ``entities`` topic by the OCR flow.

    No primary key: Pathway streaming sources must not declare one.
    """

    entity_id: str
    profile_pic: str
    face_match_urls: list[str]

    # Identity
    applicant_name: str  # first + middle + last, single-space separated
    date_of_birth: str
    gender: str
    marital_status: str
    nationality: str

    # Financial & contact
    annual_income: str
    applicant_email: str
    applicant_mobile_number: str
    occupation: str
    sources_of_income: list[str]

    # Addresses
    current_address: str
    permanent_address: str
    residential_status: str

    # Identification numbers
    passport_number: str
    unique_identification_number: str

    # Family
    father_name: str
    mother_name: str


class EnrichedEntitySchema(EntitySchema):
    """The enriched report published to ``db_updates`` and consumed by the DB sink."""

    # OpenSanctions
    os_entity_id: str | None
    os_entity_name: str | None
    os_score: float | None
    os_match_count: int | None

    # Adverse media
    citations: list[str] | None

    # Verdict
    risk_json: dict
    summary: str | None
    score_audit: dict | None
    timestamp: float


class TransactionSchema(pw.Schema):
    """Rows arriving from Debezium CDC on ``public.transactions``."""

    transaction_id: str
    user_id: int
    txn_timestamp: str
    amount: float
    currency: str
    txn_type: str
    counterparty_id: str
    is_fraud: int


#: Window aggregates the RPS model was trained on, in training order.
FEATURE_FLOAT_COLUMNS: tuple[str, ...] = (
    "total_amount_1h",
    "avg_amount_1h",
    "max_amount_1h",
    "min_amount_1h",
    "total_amount_24h",
    "avg_amount_24h",
    "max_amount_24h",
    "min_amount_24h",
    "total_amount_7d",
    "avg_amount_7d",
    "max_amount_7d",
    "min_amount_7d",
    "total_amount_30d",
    "avg_amount_30d",
    "max_amount_30d",
    "min_amount_30d",
    "incoming_outgoing_ratio_7d",
)

FEATURE_INT_COLUMNS: tuple[str, ...] = (
    "txn_count_1h",
    "unique_cp_1h",
    "txn_count_24h",
    "unique_cp_24h",
    "txn_count_7d",
    "unique_cp_7d",
    "txn_count_30d",
    "unique_cp_30d",
)

FEATURE_COLUMNS: tuple[str, ...] = FEATURE_FLOAT_COLUMNS + FEATURE_INT_COLUMNS


class TransactionFeaturesSchema(pw.Schema):
    """Per-user windowed features published to ``rps_processed_features``."""

    user_id: int
    full_name: str

    total_amount_1h: float
    txn_count_1h: int
    unique_cp_1h: int
    avg_amount_1h: float
    max_amount_1h: float
    min_amount_1h: float

    total_amount_24h: float
    txn_count_24h: int
    unique_cp_24h: int
    avg_amount_24h: float
    max_amount_24h: float
    min_amount_24h: float

    total_amount_7d: float
    txn_count_7d: int
    unique_cp_7d: int
    avg_amount_7d: float
    max_amount_7d: float
    min_amount_7d: float

    total_amount_30d: float
    txn_count_30d: int
    unique_cp_30d: int
    avg_amount_30d: float
    max_amount_30d: float
    min_amount_30d: float

    incoming_outgoing_ratio_7d: float


class RpsVerdictSchema(pw.Schema):
    """Scored + explained transactions published to ``possible_fraud``."""

    user_id: int
    full_name: str
    p_ml: float
    anomaly: float
    evidence: float
    rps: float
    risk_level: str
    short_reason: str
    long_reason: str
    recommended_action: str
    tags: str


class RagInputSchema(pw.Schema):
    """Documents indexed by the re-screening RAG server."""

    entity_id: str
    name: str
    rps_score: float
    web_prompt_old: str
    web_prompt_new: str
