"""Fusing a new transaction-side score into a user's standing risk.

Formerly ``post_aggregator.py``, which opened a global psycopg2 connection and
cursor at import time, printed on every path and returned the *old* score from a
function whose purpose was to apply the new one.

The rule itself is unchanged:

* below a floor (``rps_not <= 0.2``) the standing score is *replaced* by the new
  transaction score — a near-clean profile should not be dragged up by the union
  of two small numbers;
* above the floor the two independent signals are combined probabilistically:
  ``1 - (1 - standing)(1 - incoming)``.

Every update also writes a ``ToxicityHistory`` row, so the score has an audit
trail rather than being silently overwritten.
"""

from __future__ import annotations

from dataclasses import dataclass

import pathway as pw

from fraudguard.io import postgres
from fraudguard.logging import get_logger
from fraudguard.scoring import clamp01, combine_independent

__all__ = ["RiskUpdate", "apply_transaction_score", "update_rps"]

log = get_logger("fraudguard.risk_updates")

#: Standing scores at or below this are replaced rather than combined.
REPLACEMENT_FLOOR = 0.2

_READ_SQL = "SELECT current_rps_not, current_rps_360 FROM Users WHERE user_id = %s"
_UPDATE_SQL = """
    UPDATE Users
       SET current_rps_not = %s,
           current_rps_360 = %s,
           last_rps_calculation = NOW()
     WHERE user_id = %s
"""
_HISTORY_SQL = """
    INSERT INTO ToxicityHistory
        (user_id, rps_not, rps_360, transaction_score, calculation_trigger, calculated_at)
    VALUES (%s, %s, %s, %s, %s, NOW())
"""


@dataclass(frozen=True)
class RiskUpdate:
    user_id: int
    previous_rps_not: float
    previous_rps_360: float
    incoming_rps_360: float
    new_rps_not: float
    applied: bool
    reason: str = ""


def apply_transaction_score(
    user_id: int,
    incoming_rps_360: float,
    *,
    trigger: str = "transaction_monitoring",
) -> RiskUpdate:
    """Fold a new transaction risk score into the user's standing risk."""
    incoming = clamp01(incoming_rps_360)

    try:
        row = postgres.fetch_one(_READ_SQL, (int(user_id),))
    except Exception as exc:
        log.error("Could not read current risk", extra={"user_id": user_id, "error": str(exc)})
        return RiskUpdate(int(user_id), 0.0, 0.0, incoming, incoming, False, str(exc)[:200])

    if row is None:
        log.warning("Unknown user; risk update skipped", extra={"user_id": user_id})
        return RiskUpdate(int(user_id), 0.0, 0.0, incoming, incoming, False, "user not found")

    previous_not = clamp01(row[0])
    previous_360 = clamp01(row[1])

    if previous_not <= REPLACEMENT_FLOOR:
        new_not = incoming
        reason = f"standing score {previous_not:.3f} at or below floor; replaced"
    else:
        new_not = clamp01(combine_independent(previous_not, incoming))
        reason = "combined as independent signals"

    try:
        postgres.execute(_UPDATE_SQL, (new_not, incoming, int(user_id)))
        postgres.execute(
            _HISTORY_SQL, (int(user_id), new_not, incoming, incoming, trigger)
        )
    except Exception as exc:
        log.error("Could not persist risk update", extra={"user_id": user_id, "error": str(exc)})
        return RiskUpdate(
            int(user_id), previous_not, previous_360, incoming, new_not, False, str(exc)[:200]
        )

    log.info(
        "Standing risk updated",
        extra={
            "user_id": user_id,
            "previous_rps_not": round(previous_not, 4),
            "incoming_rps_360": round(incoming, 4),
            "new_rps_not": round(new_not, 4),
            "rule": reason,
        },
    )
    return RiskUpdate(int(user_id), previous_not, previous_360, incoming, new_not, True, reason)


@pw.udf(deterministic=False)
def update_rps(user_id: int, incoming_rps_360: float) -> float:
    """Pathway UDF returning the *new* standing score.

    The original returned the pre-update value, so the column named ``rps0``
    always lagged one event behind what was actually stored.
    """
    return apply_transaction_score(int(user_id), float(incoming_rps_360)).new_rps_not
