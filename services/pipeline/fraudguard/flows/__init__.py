"""Runnable dataflows.

Each module exposes ``build(context)`` (declares the Pathway graph) and ``main()``
(owns the run loop).  Start them with ``python -m fraudguard <flow>``.
"""

__all__ = [
    "kyc_ocr",
    "kyc_enrichment",
    "db_sink",
    "rps_features",
    "rps_explain",
    "mcp_server",
    "mcp_agent",
    "rag_server",
    "watchdog",
]
