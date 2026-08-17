"""Single entry point for chat completions.

Three files used to build their own ``llms.LiteLLMChat`` at import time (crashing
if ``MISTRAL_KEY`` was unset, even for flows that never call an LLM) and each
re-implemented the "run the model through a one-row Pathway table and dig the
string back out of ``pw.debug.table_to_dicts``" trick — with two different,
fragile extraction strategies.

:func:`complete` does it once, lazily, with retries and a robust extractor.
:func:`complete_json` adds fence-stripping and JSON recovery.
"""

from __future__ import annotations

import json
import re
import threading
import time
from typing import Any

from fraudguard.errors import GuardrailViolation, ParseError, UpstreamError
from fraudguard.llm import guard
from fraudguard.logging import get_logger

__all__ = ["complete", "complete_json", "chat_model", "embedder", "strip_code_fences"]

log = get_logger("fraudguard.llm")

_MODEL: Any | None = None
_MODEL_LOCK = threading.Lock()

_FENCE_RE = re.compile(r"```(?:json|JSON)?\s*(.*?)```", re.DOTALL)
_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def chat_model() -> Any:
    """The shared :class:`pathway.xpacks.llm.llms.LiteLLMChat` instance."""
    global _MODEL
    if _MODEL is None:
        with _MODEL_LOCK:
            if _MODEL is None:
                from pathway.udfs import DiskCache, ExponentialBackoffRetryStrategy
                from pathway.xpacks.llm import llms

                from fraudguard.config import ConfigError, get_settings

                settings = get_settings().llm
                if not settings.mistral_key:
                    raise ConfigError("MISTRAL_KEY is required for LLM-backed flows.")
                _MODEL = llms.LiteLLMChat(
                    model=settings.chat_model,
                    api_key=settings.mistral_key,
                    retry_strategy=ExponentialBackoffRetryStrategy(
                        max_retries=settings.max_retries
                    ),
                    cache_strategy=DiskCache(),
                )
                log.info("Chat model ready", extra={"model": settings.chat_model})
    return _MODEL


def embedder() -> Any:
    """The shared LiteLLM embedder used by the RAG server."""
    from pathway.udfs import DiskCache
    from pathway.xpacks.llm.embedders import LiteLLMEmbedder

    from fraudguard.config import ConfigError, get_settings

    settings = get_settings().llm
    if not settings.embedding_api_key:
        raise ConfigError("EMBEDDING_API_KEY (or MISTRAL_KEY) is required for the RAG server.")
    return LiteLLMEmbedder(
        model=settings.embedding_model,
        api_key=settings.embedding_api_key,
        cache_strategy=DiskCache(),
    )


def _extract_first_string(value: Any) -> str | None:
    """Depth-first search for the first string in Pathway's nested result structure.

    ``pw.debug.table_to_dicts`` returns ``(pointers, {column: {pointer: value}})``
    in some versions and a plain dict in others; indexing by position broke
    whenever the shape changed.
    """
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for item in value.values():
            found = _extract_first_string(item)
            if found:
                return found
    elif isinstance(value, (list, tuple)):
        for item in value:
            found = _extract_first_string(item)
            if found:
                return found
    return None


def _invoke(system_prompt: str, user_prompt: str) -> str:
    import pathway as pw

    model = chat_model()
    queries = pw.debug.table_from_rows(
        pw.schema_from_types(questions=list[dict]),
        rows=[
            (
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        ],
    )
    responses = queries.select(raw_result=model(pw.this.questions))
    text = _extract_first_string(pw.debug.table_to_dicts(responses))
    if not text:
        raise ParseError("Could not extract a completion from the Pathway result table")
    return text


def complete(
    system_prompt: str,
    user_prompt: str,
    *,
    validate_input: bool = True,
    validate_output: bool = False,
    attempts: int = 3,
) -> str:
    """Run a chat completion and return the raw text.

    Raises :class:`GuardrailViolation` when the prompts (or, optionally, the
    response) fail content validation, and :class:`UpstreamError` when the model
    cannot be reached after ``attempts`` tries.
    """
    if validate_input:
        result = guard.validate_all(system_prompt=system_prompt, user_prompt=user_prompt)
        if not result.ok:
            raise GuardrailViolation(result.reason or "prompt failed content validation")

    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            text = _invoke(system_prompt, user_prompt)
            break
        except Exception as exc:  # LiteLLM raises a wide variety of exception types
            last_error = exc
            wait = min(2**attempt, 30)
            log.warning(
                "LLM call failed, retrying",
                extra={"attempt": attempt, "wait_s": wait, "error": str(exc)[:200]},
            )
            if attempt < attempts:
                time.sleep(wait)
    else:
        raise UpstreamError("llm", f"all {attempts} attempts failed: {last_error}")

    if validate_output:
        result = guard.validate(text, label="completion")
        if not result.ok:
            raise GuardrailViolation(result.reason or "completion failed content validation")
    return text


def strip_code_fences(text: str) -> str:
    """Remove ```json fences and surrounding prose."""
    match = _FENCE_RE.search(text)
    return (match.group(1) if match else text).strip()


def complete_json(
    system_prompt: str,
    user_prompt: str,
    *,
    attempts: int = 3,
    **kwargs: Any,
) -> dict[str, Any]:
    """Run a completion and parse the response as a JSON object."""
    text = complete(system_prompt, user_prompt, attempts=attempts, **kwargs)
    return parse_json_object(text)


def parse_json_object(text: str) -> dict[str, Any]:
    """Best-effort recovery of a JSON object from a model response."""
    candidate = strip_code_fences(text)
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        match = _OBJECT_RE.search(candidate)
        if not match:
            raise ParseError(f"No JSON object in model output: {candidate[:200]}") from None
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise ParseError(f"Invalid JSON in model output: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ParseError("Model returned JSON that is not an object")
    return parsed
