"""Adaptive scheduler for the re-screening watchdog.

Runs a sweep, and for every entity whose adverse-media coverage moved, asks the
RAG server to re-derive the risk score from the *delta* between the old and new
evidence, then persists the new score.

The polling interval is adaptive (AIMD): it shrinks multiplicatively when a
sweep finds changes and grows after several quiet sweeps, so a busy period is
sampled densely without hammering the search APIs when nothing is happening.

Rewritten from ``watcher/scheduler.py``:

* the watchdog ran as a subprocess with a hard 10-minute kill; it is now called
  in-process and each entity is independently error-isolated;
* ``T`` and ``consecutive_no_write`` were module-level globals mutated from a
  nested branch, and the interval was only ever updated *inside* the per-entity
  loop — a sweep with zero entities never adjusted it;
* the comparison logic (four independent JSONL reads zipped together) lives in
  the watchdog now, keyed per entity;
* a single Postgres connection and cursor were opened at import and reused
  forever; the pooled helpers are used instead;
* ``CHECK_INTERVAL_SECONDS = 10`` was dead code sitting next to the real
  ``T = 10 * 60`` it was meant to configure.
"""

from __future__ import annotations

import argparse
import signal
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Sequence

from fraudguard.errors import FraudGuardError, UpstreamError
from fraudguard.flows.watchdog import EntityDelta, run_watchdog
from fraudguard.io import postgres
from fraudguard.io.http import request_json
from fraudguard.io.jsonl import append_jsonl
from fraudguard.llm import prompts
from fraudguard.logging import configure, get_logger, log_context
from fraudguard.scoring import clamp01
from fraudguard.udfs import _extract_json_and_summary

__all__ = ["AdaptiveInterval", "SchedulerConfig", "run_forever", "main"]

log = get_logger("fraudguard.scheduler")

FLOW_NAME = "watchdog-scheduler"

_UPDATE_SQL = """
    UPDATE Users
       SET current_rps_not = %s,
           last_rps_calculation = NOW()
     WHERE user_id = %s
"""

_HISTORY_SQL = """
    INSERT INTO ToxicityHistory (user_id, rps_not, news_score, calculation_trigger, calculated_at)
    VALUES (%s, %s, %s, %s, NOW())
"""


@dataclass
class SchedulerConfig:
    min_interval_s: float = 10 * 60
    max_interval_s: float = 120 * 60
    initial_interval_s: float = 10 * 60
    decrease_factor: float = 0.7  # multiplicative decrease when changes are found
    increase_factor: float = 1.2  # multiplicative increase when quiet
    quiet_sweeps_before_backoff: int = 3
    targets_per_sweep: int = 200
    rag_timeout_s: int = 60


class AdaptiveInterval:
    """AIMD controller for the sweep interval."""

    def __init__(self, config: SchedulerConfig) -> None:
        self.config = config
        self.value = config.initial_interval_s
        self._quiet_sweeps = 0

    def register(self, *, changes_found: bool) -> float:
        cfg = self.config
        if changes_found:
            self._quiet_sweeps = 0
            self.value = max(cfg.min_interval_s, self.value * cfg.decrease_factor)
        else:
            self._quiet_sweeps += 1
            if self._quiet_sweeps >= cfg.quiet_sweeps_before_backoff:
                self._quiet_sweeps = 0
                self.value = min(cfg.max_interval_s, self.value * cfg.increase_factor)
        return self.value


# --------------------------------------------------------------------------- #
# Re-assessment
# --------------------------------------------------------------------------- #


def reassess(delta: EntityDelta, *, rag_url: str, timeout_s: int) -> float | None:
    """Ask the RAG server for an updated score; ``None`` if it could not answer."""
    prompt = prompts.watchdog_delta_prompt(
        entity_id=delta.entity_id,
        name=delta.name,
        previous_rps=delta.previous_rps,
        old_notes=delta.web_prompt_old or "(no previous coverage)",
        new_notes=delta.web_prompt_new,
    )
    try:
        body = request_json(
            "POST", rag_url, service="rag", json_body={"prompt": prompt}, timeout=timeout_s
        )
    except UpstreamError as exc:
        log.warning("RAG re-assessment failed", extra={"entity_id": delta.entity_id, "error": str(exc)})
        return None

    answer = str(body.get("response") or body.get("answer") or "")
    payload, _summary = _extract_json_and_summary(answer)
    raw = payload.get("risk_score")
    if raw is None:
        log.warning("RAG returned no risk_score", extra={"entity_id": delta.entity_id})
        return None

    score = clamp01(raw)
    # A hard zero from the model is treated as "no opinion" rather than "cleared".
    return score if score > 0 else None


def persist_score(entity_id: str, score: float, news_score: float) -> bool:
    try:
        updated = postgres.execute(_UPDATE_SQL, (score, int(entity_id)))
        if updated:
            postgres.execute(
                _HISTORY_SQL, (int(entity_id), score, news_score, "watchdog_rescreen")
            )
        return bool(updated)
    except Exception as exc:  # a non-numeric id or any DB failure
        log.error("Could not persist score", extra={"entity_id": entity_id, "error": str(exc)})
        return False


def process_sweep(deltas: Sequence[EntityDelta], config: SchedulerConfig, rag_url: str) -> int:
    """Re-assess and persist every changed entity; returns how many were updated."""
    from fraudguard.config import get_settings

    changed = [delta for delta in deltas if delta.changed]
    if not changed:
        log.info("No coverage changes this sweep", extra={"screened": len(deltas)})
        return 0

    settings = get_settings()
    audit_path = settings.paths.out / "rescreen_audit.jsonl"
    rag_dir = settings.paths.state / "rag_documents"
    rag_dir.mkdir(parents=True, exist_ok=True)

    updated = 0
    for delta in changed:
        with log_context(entity_id=delta.entity_id, subject=delta.name):
            log.info("Coverage changed", extra={"similarity": delta.similarity})
            # Publish the before/after evidence for the RAG server to index.
            append_jsonl(rag_dir / f"entity_{delta.entity_id}.jsonl", delta.rag_document())
            score = reassess(delta, rag_url=rag_url, timeout_s=config.rag_timeout_s)
            record = {
                "entity_id": delta.entity_id,
                "name": delta.name,
                "similarity": delta.similarity,
                "previous_rps": delta.previous_rps,
                "new_rps": score,
                "sanction_matches": delta.sanction_matches,
                "citations": delta.citations,
                "checked_at": delta.checked_at,
            }
            if score is not None and persist_score(delta.entity_id, score, delta.sanction_score or 0.0):
                updated += 1
                record["persisted"] = True
                log.info("Risk score updated", extra={"new_rps": score})
            else:
                record["persisted"] = False
            append_jsonl(audit_path, record)
    return updated


# --------------------------------------------------------------------------- #
# Loop
# --------------------------------------------------------------------------- #

_STOP = False


def _handle_signal(signum: int, _frame) -> None:
    global _STOP
    _STOP = True
    log.info("Stop requested", extra={"signal": signum})


def run_forever(config: SchedulerConfig | None = None, *, max_sweeps: int | None = None) -> int:
    from fraudguard.config import get_settings

    config = config or SchedulerConfig()
    settings = get_settings()
    interval = AdaptiveInterval(config)

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, _handle_signal)
        except ValueError:
            pass

    log.info(
        "Watchdog scheduler started",
        extra={
            "initial_interval_min": round(config.initial_interval_s / 60, 1),
            "bounds_min": f"{config.min_interval_s / 60:.0f}-{config.max_interval_s / 60:.0f}",
            "rag_url": settings.rag_url,
        },
    )

    sweeps = 0
    try:
        while not _STOP and (max_sweeps is None or sweeps < max_sweeps):
            sweeps += 1
            started = time.perf_counter()
            try:
                deltas = run_watchdog(limit=config.targets_per_sweep)
                updated = process_sweep(deltas, config, settings.rag_url)
            except FraudGuardError as exc:
                log.error("Sweep failed", extra={"sweep": sweeps, "error": str(exc)})
                deltas, updated = [], 0

            next_interval = interval.register(changes_found=updated > 0)
            log.info(
                "Sweep %s complete in %.1fs — next in %.1f min",
                sweeps,
                time.perf_counter() - started,
                next_interval / 60,
                extra={
                    "screened": len(deltas),
                    "updated": updated,
                    "next_run": (datetime.now() + timedelta(seconds=next_interval)).isoformat(
                        timespec="seconds"
                    ),
                },
            )

            if max_sweeps is not None and sweeps >= max_sweeps:
                break

            # Sleep in short slices so SIGTERM is honoured promptly.
            deadline = time.time() + next_interval
            while not _STOP and time.time() < deadline:
                time.sleep(min(5.0, max(0.0, deadline - time.time())))
    finally:
        postgres.close_pool()

    log.info("Scheduler stopped", extra={"sweeps": sweeps})
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Adaptive watchdog scheduler.")
    parser.add_argument("--min-interval", type=float, default=600, help="Floor, in seconds.")
    parser.add_argument("--max-interval", type=float, default=7200, help="Ceiling, in seconds.")
    parser.add_argument("--interval", type=float, default=600, help="Starting interval, seconds.")
    parser.add_argument("--targets", type=int, default=200, help="Entities per sweep.")
    parser.add_argument("--once", action="store_true", help="Run a single sweep and exit.")
    args = parser.parse_args(argv)

    configure(FLOW_NAME)
    config = SchedulerConfig(
        min_interval_s=args.min_interval,
        max_interval_s=args.max_interval,
        initial_interval_s=args.interval,
        targets_per_sweep=args.targets,
    )
    return run_forever(config, max_sweeps=1 if args.once else None)


if __name__ == "__main__":
    raise SystemExit(main())
