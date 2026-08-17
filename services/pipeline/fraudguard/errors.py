"""Exception hierarchy shared by the pipeline.

Every failure mode the flows care about is one of these, so callers can decide
between "skip this record" and "stop the flow" instead of catching bare
``Exception`` (which the original code did in ~30 places, swallowing bugs).
"""

from __future__ import annotations

__all__ = [
    "FraudGuardError",
    "ConfigurationError",
    "UpstreamError",
    "RateLimitedError",
    "ScoringError",
    "GuardrailViolation",
    "ParseError",
]


class FraudGuardError(Exception):
    """Base class for all pipeline errors."""


class ConfigurationError(FraudGuardError):
    """Missing or invalid configuration."""


class UpstreamError(FraudGuardError):
    """A third-party API failed (OpenSanctions, OFAC, OTX, Google, an LLM, ...)."""

    def __init__(self, service: str, message: str, *, status_code: int | None = None) -> None:
        super().__init__(f"{service}: {message}")
        self.service = service
        self.status_code = status_code


class RateLimitedError(UpstreamError):
    """An upstream returned 429 / quota exceeded."""


class ScoringError(FraudGuardError):
    """The RPS model could not produce a score for a feature vector."""


class GuardrailViolation(FraudGuardError):
    """Generated or ingested text failed a safety guardrail."""


class ParseError(FraudGuardError):
    """A model or connector returned a payload we could not interpret."""
