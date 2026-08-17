"""Point-in-time transaction feature builder.

The RPS model is trained on per-user windowed aggregates (1 h / 24 h / 7 d / 30 d).
The streaming flow used to compute them with ``trx.windowby(trx.ts, ...)``, which
had three defects that made the served features disagree with the trained ones:

* the windows were **not partitioned by user** — ``groupby(trx.user_id)`` was
  assigned to an unused variable and ``windowby`` was given no ``instance``, so
  every aggregate mixed all users in the window together;
* ``unique_cp_*`` used ``pw.reducers.any(counterparty_id)``, which returns *one
  arbitrary counterparty id*, not a distinct count — and that id (a string) was
  then coerced to an int and fed to the model as a feature;
* the four window tables were joined on that same arbitrary id.

Computing the vector with one parameterised SQL statement against the system of
record is both correct and simpler: ``FILTER (WHERE ...)`` gives every window in
a single pass, ``COUNT(DISTINCT ...)`` is a real distinct count, and the result
matches how the training snapshots were generated.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fraudguard.io import postgres
from fraudguard.logging import get_logger
from fraudguard.schemas import FEATURE_COLUMNS, FEATURE_INT_COLUMNS

__all__ = ["build_feature_vector", "lookup_username", "FEATURE_SQL"]

log = get_logger("fraudguard.features")

_WINDOWS: tuple[tuple[str, str], ...] = (
    ("1h", "1 hour"),
    ("24h", "24 hours"),
    ("7d", "7 days"),
    ("30d", "30 days"),
)


def _window_projection(suffix: str, interval: str) -> str:
    """The six aggregates for one window, as SQL select-list entries."""
    window = f"txn_timestamp >= NOW() - INTERVAL '{interval}'"
    return f"""
        COALESCE(SUM(amount)   FILTER (WHERE {window}), 0.0) AS total_amount_{suffix},
        COALESCE(COUNT(*)      FILTER (WHERE {window}), 0)   AS txn_count_{suffix},
        COALESCE(COUNT(DISTINCT counterparty_id)
                               FILTER (WHERE {window}), 0)   AS unique_cp_{suffix},
        COALESCE(AVG(amount)   FILTER (WHERE {window}), 0.0) AS avg_amount_{suffix},
        COALESCE(MAX(amount)   FILTER (WHERE {window}), 0.0) AS max_amount_{suffix},
        COALESCE(MIN(amount)   FILTER (WHERE {window}), 0.0) AS min_amount_{suffix}"""


FEATURE_SQL = f"""
WITH outgoing AS (
    SELECT {",".join(_window_projection(suffix, interval) for suffix, interval in _WINDOWS)},
        COALESCE(SUM(amount) FILTER (WHERE txn_timestamp >= NOW() - INTERVAL '7 days'), 0.0)
            AS outgoing_7d
    FROM Transactions
    WHERE user_id = %(user_id)s
),
incoming AS (
    SELECT COALESCE(SUM(amount) FILTER (WHERE txn_timestamp >= NOW() - INTERVAL '7 days'), 0.0)
            AS incoming_7d
    FROM Transactions
    WHERE counterparty_id = %(user_id)s
)
SELECT outgoing.*,
       incoming.incoming_7d,
       CASE WHEN outgoing.outgoing_7d > 0
            THEN incoming.incoming_7d / outgoing.outgoing_7d
            ELSE 0.0
       END AS incoming_outgoing_ratio_7d
FROM outgoing CROSS JOIN incoming
"""

_USERNAME_SQL = "SELECT username FROM Users WHERE user_id = %s"


@dataclass(frozen=True)
class FeatureVector:
    user_id: int
    values: dict[str, float]

    def as_model_input(self) -> dict[str, float]:
        """Only the columns the model was trained on, in training order."""
        return {name: self.values.get(name, 0) for name in FEATURE_COLUMNS}


def _coerce(name: str, value: Any) -> float | int:
    if value is None:
        return 0 if name in FEATURE_INT_COLUMNS else 0.0
    try:
        return int(value) if name in FEATURE_INT_COLUMNS else float(value)
    except (TypeError, ValueError):
        return 0 if name in FEATURE_INT_COLUMNS else 0.0


def build_feature_vector(user_id: int) -> dict[str, float]:
    """Compute the model's feature vector for one user, as of now.

    Returns an all-zero vector (never raises) when the database is unreachable,
    so a transient outage degrades the score rather than killing the flow — the
    caller can spot it because every value is zero.
    """
    try:
        with postgres.cursor(dict_rows=True) as cur:
            cur.execute(FEATURE_SQL, {"user_id": user_id})
            row = cur.fetchone()
    except Exception as exc:
        log.error("Feature query failed", extra={"user_id": user_id, "error": str(exc)})
        return {name: _coerce(name, None) for name in FEATURE_COLUMNS}

    if not row:
        log.info("No transactions for user", extra={"user_id": user_id})
        return {name: _coerce(name, None) for name in FEATURE_COLUMNS}

    return {name: _coerce(name, row.get(name)) for name in FEATURE_COLUMNS}


def lookup_username(user_id: int) -> str:
    try:
        row = postgres.fetch_one(_USERNAME_SQL, (user_id,))
    except Exception as exc:
        log.warning("Username lookup failed", extra={"user_id": user_id, "error": str(exc)})
        return "Unknown"
    return str(row[0]) if row and row[0] else "Unknown"
