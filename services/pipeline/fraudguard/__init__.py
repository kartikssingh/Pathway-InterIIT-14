"""FraudGuard — the streaming KYC / AML compliance pipeline.

Layers, bottom up:

``config`` / ``logging`` / ``errors``
    Process-wide settings, structured logging and the exception hierarchy.
``io``
    Adapters: pooled HTTP, pooled Postgres, JSON Lines, durable state.
``llm``
    One shared chat client, content guardrails and the prompt templates.
``enrichment``
    External data: OpenSanctions, OFAC, adverse-media search, source reputation.
``scoring`` / ``features`` / ``similarity``
    Deterministic risk arithmetic, the transaction feature builder and the
    change-detection metric.
``rps``
    Model registry, inference engine and the HTTP scoring service.
``flows``
    The runnable Pathway dataflows.

Start a flow with ``python -m fraudguard <flow>``; ``python -m fraudguard --list``
shows what is available.
"""

__version__ = "2.0.0"

__all__ = ["__version__"]
