"""SQLAlchemy models.

Importing this package registers every table on ``Base.metadata``; several
modules relied on that side effect while only four models were listed here, so
relationship resolution failed depending on import order.
"""

from app.models import (
    admin,
    alert,
    audit_log,
    system_health,
    system_metrics,
    toxicity_history,
    transaction,
    user,
    user_sanction_match,
)

__all__ = [
    "admin",
    "alert",
    "audit_log",
    "system_health",
    "system_metrics",
    "toxicity_history",
    "transaction",
    "user",
    "user_sanction_match",
]
