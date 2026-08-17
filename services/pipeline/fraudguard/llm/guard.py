"""Guardrails wrapper that degrades gracefully.

``guardrails-ai`` plus its hub validators are a heavy, optional install.  The old
code imported ``guardrails.hub.ToxicLanguage`` at module scope in five files, so
the entire pipeline refused to start if the hub packages were absent — and every
call site then re-implemented "try validate / except / print".

Here the guard is built lazily and once; if it cannot be constructed the pipeline
logs a single warning and continues in *permissive* mode.  Set
``GUARDRAILS_ENABLED=false`` to skip it deliberately.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any

from fraudguard.logging import get_logger

__all__ = ["GuardResult", "validate", "validate_all", "is_active"]

log = get_logger("fraudguard.guard")

_GUARD: Any | None = None
_GUARD_READY = False
_GUARD_LOCK = threading.Lock()


@dataclass(frozen=True)
class GuardResult:
    ok: bool
    reason: str | None = None

    def __bool__(self) -> bool:  # pragma: no cover - trivial
        return self.ok


def _build_guard() -> Any | None:
    from fraudguard.config import get_settings

    settings = get_settings().llm
    if not settings.guardrails_enabled:
        log.info("Guardrails disabled by configuration")
        return None
    try:
        from guardrails import Guard, OnFailAction
        from guardrails.hub import ProfanityFree, ToxicLanguage
    except Exception as exc:
        log.warning(
            "Guardrails unavailable — content validation is disabled. "
            "Install with: pip install guardrails-ai && "
            "guardrails hub install hub://guardrails/toxic_language",
            extra={"error": str(exc)},
        )
        return None

    try:
        return Guard().use_many(
            ToxicLanguage(
                threshold=settings.toxicity_threshold,
                validation_method="sentence",
                on_fail=OnFailAction.EXCEPTION,
            ),
            ProfanityFree(on_fail=OnFailAction.EXCEPTION),
        )
    except Exception as exc:
        log.warning("Guardrails validators failed to load", extra={"error": str(exc)})
        return None


def _guard() -> Any | None:
    global _GUARD, _GUARD_READY
    if not _GUARD_READY:
        with _GUARD_LOCK:
            if not _GUARD_READY:
                _GUARD = _build_guard()
                _GUARD_READY = True
    return _GUARD


def is_active() -> bool:
    """True when real validation is happening."""
    return _guard() is not None


def validate(text: str | None, *, label: str = "text") -> GuardResult:
    """Validate one string. Never raises — inspect the result instead."""
    if not text:
        return GuardResult(True)
    guard = _guard()
    if guard is None:
        return GuardResult(True)
    try:
        guard.validate(text)
        return GuardResult(True)
    except Exception as exc:
        log.warning("Guardrail violation", extra={"label": label, "error": str(exc)[:300]})
        return GuardResult(False, str(exc))


def validate_all(**named_texts: str | None) -> GuardResult:
    """Validate several strings; return the first failure."""
    for label, text in named_texts.items():
        result = validate(text, label=label)
        if not result.ok:
            return result
    return GuardResult(True)
