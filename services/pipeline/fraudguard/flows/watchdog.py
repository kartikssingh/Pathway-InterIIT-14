"""Periodic re-screening of already-onboarded entities.

Sanctions lists and news coverage change after onboarding, so every known
customer is re-checked on a schedule.  The watchdog answers one question per
entity: *has the public evidence about this person changed since we last looked?*

The original implementation was a Pathway graph run in ``mode="static"``, driven
by a scheduler that shelled out to ``python watcher/watchdog.py`` every cycle,
then compared runs by ``shutil.copytree``-ing ``out/watchdog`` into
``out/watchdog_current`` and ``out/watchdog_prev`` and zipping four independently
parsed lists of JSONL fields together — a comparison that silently mis-paired
entities as soon as one run returned a different number of rows.

Static, one-shot work gains nothing from a streaming engine, so this is plain
Python:

* entities come from Postgres (the system of record) instead of a Kafka replay;
* each run's evidence is stored in the :class:`~fraudguard.io.state.StateStore`
  keyed by entity id, so comparisons are per-entity and cannot mis-pair;
* it is importable, so the scheduler calls it in-process — no subprocess, no
  ten-minute timeout, no directory copying.
"""

from __future__ import annotations

import argparse
import time
from dataclasses import asdict, dataclass, field
from typing import Iterable, Sequence

from fraudguard.enrichment.opensanctions import screen
from fraudguard.enrichment.web_analysis import analyse
from fraudguard.io import postgres
from fraudguard.io.jsonl import append_jsonl
from fraudguard.io.state import StateStore
from fraudguard.logging import configure, get_logger, log_context
from fraudguard.similarity import text_similarity

__all__ = ["WatchTarget", "EntityDelta", "run_watchdog", "main"]

log = get_logger("fraudguard.flows.watchdog")

FLOW_NAME = "watchdog"
STATE_NAMESPACE = "watchdog"

#: Below this cosine similarity the coverage is considered materially changed.
DEFAULT_SIMILARITY_THRESHOLD = 0.90

_TARGET_QUERY = """
    SELECT user_id, username, current_rps_not, date_of_birth, address
    FROM Users
    WHERE blacklisted IS NOT TRUE
      AND username IS NOT NULL
    ORDER BY COALESCE(last_rps_calculation, TIMESTAMP 'epoch') ASC
    LIMIT %s
"""


@dataclass(frozen=True)
class WatchTarget:
    entity_id: str
    name: str
    previous_rps: float = 0.0
    date_of_birth: str | None = None
    address: str | None = None


@dataclass
class EntityDelta:
    """One entity's re-screening outcome."""

    entity_id: str
    name: str
    previous_rps: float
    similarity: float
    changed: bool
    sanction_matches: int
    sanction_score: float | None
    web_prompt_old: str
    web_prompt_new: str
    citations: list[str] = field(default_factory=list)
    checked_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)

    def rag_document(self) -> dict:
        """Payload indexed by the RAG server for the delta re-assessment."""
        return {
            "entity_id": self.entity_id,
            "name": self.name,
            "rps_score": self.previous_rps,
            "web_prompt_old": self.web_prompt_old,
            "web_prompt_new": self.web_prompt_new,
        }


# --------------------------------------------------------------------------- #
# Targets
# --------------------------------------------------------------------------- #


def load_targets(limit: int = 200) -> list[WatchTarget]:
    """The entities due for re-screening, least-recently-checked first."""
    try:
        rows = postgres.fetch_all(_TARGET_QUERY, (limit,))
    except Exception as exc:
        log.error("Could not load watchdog targets", extra={"error": str(exc)})
        return []

    targets = []
    for user_id, username, rps, dob, address in rows:
        targets.append(
            WatchTarget(
                entity_id=str(user_id),
                name=str(username),
                previous_rps=float(rps or 0.0),
                date_of_birth=dob.isoformat() if hasattr(dob, "isoformat") else dob,
                address=address,
            )
        )
    log.info("Loaded watchdog targets", extra={"count": len(targets)})
    return targets


# --------------------------------------------------------------------------- #
# Screening
# --------------------------------------------------------------------------- #


def screen_target(target: WatchTarget, store: StateStore) -> EntityDelta:
    """Re-screen one entity and compare against its previous snapshot."""
    with log_context(entity_id=target.entity_id, subject=target.name):
        sanctions = screen(target.name, target.date_of_birth)
        analysis = analyse(target.name)

        previous = store.load_latest(target.entity_id, default={}) or {}
        old_prompt = str(previous.get("web_prompt", ""))
        new_prompt = analysis.prompt

        similarity = text_similarity(old_prompt, new_prompt) if old_prompt else 0.0
        # A first sighting is not a "change"; there is nothing to compare against.
        changed = bool(old_prompt) and similarity < DEFAULT_SIMILARITY_THRESHOLD

        store.save(
            target.entity_id,
            {
                "name": target.name,
                "web_prompt": new_prompt,
                "citations": analysis.citations,
                "sanction_matches": sanctions.match_count,
                "sanction_score": sanctions.score,
                "sources": analysis.to_dict()["sources"],
            },
            metadata={"similarity_vs_previous": similarity},
        )

        delta = EntityDelta(
            entity_id=target.entity_id,
            name=target.name,
            previous_rps=target.previous_rps,
            similarity=similarity,
            changed=changed,
            sanction_matches=sanctions.match_count,
            sanction_score=sanctions.score,
            web_prompt_old=old_prompt,
            web_prompt_new=new_prompt,
            citations=analysis.citations,
        )
        log.info(
            "Re-screened entity",
            extra={
                "similarity": round(similarity, 4),
                "changed": changed,
                "sanction_matches": sanctions.match_count,
            },
        )
        return delta


def run_watchdog(
    targets: Sequence[WatchTarget] | None = None,
    *,
    limit: int = 200,
    store: StateStore | None = None,
) -> list[EntityDelta]:
    """Re-screen every target and return the per-entity deltas."""
    store = store or StateStore(STATE_NAMESPACE)
    targets = list(targets) if targets is not None else load_targets(limit)

    deltas: list[EntityDelta] = []
    for target in targets:
        try:
            deltas.append(screen_target(target, store))
        except Exception as exc:  # one entity must not abort the sweep
            log.exception(
                "Re-screening failed",
                extra={"entity_id": target.entity_id, "error": str(exc)},
            )

    _write_report(deltas)
    store.prune()
    changed = sum(1 for delta in deltas if delta.changed)
    log.info("Watchdog sweep complete", extra={"screened": len(deltas), "changed": changed})
    return deltas


def _write_report(deltas: Iterable[EntityDelta]) -> None:
    from fraudguard.config import get_settings

    path = get_settings().paths.out / "watchdog_report.jsonl"
    for delta in deltas:
        append_jsonl(path, delta.to_dict())


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Re-screen onboarded entities once.")
    parser.add_argument(
        "--limit", type=int, default=200, help="Maximum entities to re-screen in this sweep."
    )
    parser.add_argument(
        "--name",
        action="append",
        default=[],
        help="Screen an ad-hoc name instead of reading from the database (repeatable).",
    )
    args = parser.parse_args(argv)

    configure(FLOW_NAME)

    targets = (
        [WatchTarget(entity_id=f"adhoc-{index}", name=name) for index, name in enumerate(args.name)]
        if args.name
        else None
    )
    deltas = run_watchdog(targets, limit=args.limit)
    return 0 if deltas or not targets else 1


if __name__ == "__main__":
    raise SystemExit(main())
