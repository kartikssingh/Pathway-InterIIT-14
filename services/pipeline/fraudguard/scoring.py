"""Deterministic reference implementation of the compliance risk score.

The prompt in :mod:`fraudguard.llm.prompts` asks the model to follow an exact
algorithm.  Previously nothing verified that it did, and when the LLM was
unavailable the flow emitted an unusable placeholder built from the raw
OpenSanctions score alone.

This module implements that algorithm in Python so it can serve three purposes:

1. **Fallback** — the pipeline always produces a defensible score.
2. **Audit** — regulators can be shown the exact arithmetic behind a decision.
3. **Drift detection** — :func:`deviation` compares the model's answer with the
   deterministic one, which is what feeds the ``llm_score_drift`` metric.

The weights and thresholds are the single source of truth; the prompt text
documents them, this code executes them.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Mapping, Sequence

__all__ = [
    "RiskBand",
    "RiskAssessment",
    "ArticleEvidence",
    "SEVERITY_BY_TYPE",
    "WEIGHTS",
    "classify",
    "sanction_score",
    "web_evidence_score",
    "assess",
    "deviation",
    "probabilistic_union",
]

# --------------------------------------------------------------------------- #
# Contract constants — mirrored verbatim in llm/prompts.py
# --------------------------------------------------------------------------- #

SEVERITY_BY_TYPE: dict[str, float] = {
    "official_sanction": 1.00,
    "conviction": 0.95,
    "indictment": 0.85,
    "charges": 0.85,
    "regulatory_fine": 0.70,
    "credible_allegation": 0.60,
    "negative_media": 0.30,
    "rumour": 0.10,
    "other": 0.20,
}

WEIGHTS: dict[str, float] = {"sanctions": 0.60, "web_evidence": 0.30, "match_confidence": 0.10}

#: Number of confirmed sanctions treated as maximum sanctions risk.
SANCTION_SATURATION = 5

#: Lower bound of each band, highest first.
BAND_THRESHOLDS: tuple[tuple[float, str], ...] = (
    (0.750, "CRITICAL"),
    (0.500, "HIGH"),
    (0.250, "MEDIUM"),
    (0.000, "LOW"),
)

#: Keyword hints used to infer an article type when one was not supplied.
_TYPE_HINTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("official_sanction", ("sanction", "ofac", "sdn list", "asset freeze", "designated")),
    ("conviction", ("convicted", "conviction", "found guilty", "sentenced", "jailed")),
    ("indictment", ("indicted", "indictment", "charged", "charges filed", "arrest warrant")),
    ("regulatory_fine", ("fined", "penalty", "regulatory action", "sebi", "rbi order")),
    ("credible_allegation", ("investigation", "probe", "raid", "summoned", "accused")),
    ("negative_media", ("controversy", "criticised", "scandal", "backlash")),
    ("rumour", ("rumour", "rumor", "allegedly", "unconfirmed", "speculation")),
)


class RiskBand:
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    ALL = (LOW, MEDIUM, HIGH, CRITICAL)


@dataclass(frozen=True)
class ArticleEvidence:
    """One piece of adverse-media evidence."""

    url: str = ""
    title: str = ""
    authenticity: float = 0.0
    article_type: str | None = None
    excerpt: str = ""

    @property
    def severity(self) -> float:
        kind = (self.article_type or "").strip().lower()
        if kind in SEVERITY_BY_TYPE:
            return SEVERITY_BY_TYPE[kind]
        return SEVERITY_BY_TYPE[infer_article_type(f"{self.title} {self.excerpt}")]

    @property
    def score(self) -> float:
        return clamp01(self.authenticity) * self.severity


@dataclass(frozen=True)
class RiskAssessment:
    risk_score: float
    risk_classification: str
    match_found: bool
    sanction_score: float
    web_evidence_score: float
    match_confidence: float
    contributing_articles: int
    strongest_driver: str
    summary: str
    components: dict[str, float] = field(default_factory=dict)

    def to_risk_json(self) -> dict[str, Any]:
        """The compact shape written to Kafka and Postgres."""
        return {
            "risk_score": self.risk_score,
            "risk_classification": self.risk_classification,
            "match_found": self.match_found,
        }

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# --------------------------------------------------------------------------- #
# Primitives
# --------------------------------------------------------------------------- #


def clamp01(value: Any) -> float:
    """Coerce anything to a float in [0, 1]; unparseable input becomes 0.0."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    if math.isnan(number) or math.isinf(number):
        return 0.0
    return max(0.0, min(1.0, number))


def parse_confidence(value: Any) -> float:
    """Parse a match confidence given as 0-1, a 0-100 number, or an "85%" string."""
    if value is None:
        return 0.0
    if isinstance(value, str):
        text = value.strip().rstrip("%")
        try:
            number = float(text)
        except ValueError:
            return 0.0
        if value.strip().endswith("%") or number > 1:
            number /= 100.0
        return clamp01(number)
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    if number > 1:
        number /= 100.0
    return clamp01(number)


def infer_article_type(text: str) -> str:
    lowered = (text or "").lower()
    for kind, hints in _TYPE_HINTS:
        if any(hint in lowered for hint in hints):
            return kind
    return "other"


def probabilistic_union(scores: Iterable[float]) -> float:
    """1 - prod(1 - s) — the probability that at least one signal is real."""
    product = 1.0
    for score in scores:
        product *= 1.0 - clamp01(score)
    return clamp01(1.0 - product)


def sanction_score(match_count: Any) -> float:
    """min(N / 5, 1.0), with N parsed leniently from ints, floats or text."""
    count = _parse_int(match_count)
    return clamp01(count / SANCTION_SATURATION)


def _parse_int(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return max(0, int(value))
    digits = "".join(char for char in str(value) if char.isdigit())
    return int(digits) if digits else 0


def web_evidence_score(articles: Sequence[ArticleEvidence]) -> float:
    return probabilistic_union(article.score for article in articles)


def classify(score: float) -> str:
    for threshold, band in BAND_THRESHOLDS:
        if score >= threshold:
            return band
    return RiskBand.LOW


# --------------------------------------------------------------------------- #
# Full assessment
# --------------------------------------------------------------------------- #


def assess(
    *,
    entity_name: str = "",
    sanction_matches: Any = 0,
    match_confidence: Any = None,
    articles: Sequence[ArticleEvidence] | None = None,
) -> RiskAssessment:
    """Compute the deterministic risk assessment for one entity."""
    articles = list(articles or [])

    s_score = sanction_score(sanction_matches)
    w_score = web_evidence_score(articles)
    m_score = parse_confidence(match_confidence)

    contributions = {
        "sanctions": s_score * WEIGHTS["sanctions"],
        "web_evidence": w_score * WEIGHTS["web_evidence"],
        "match_confidence": m_score * WEIGHTS["match_confidence"],
    }
    total = round(clamp01(sum(contributions.values())), 3)
    driver = max(contributions, key=lambda key: contributions[key])
    band = classify(total)

    summary = (
        f"Parsed {_parse_int(sanction_matches)} OpenSanctions match(es) giving a "
        f"sanction_score of {s_score:.3f}; {len(articles)} contributing article(s) giving a "
        f"web_evidence_score of {w_score:.3f}; match_confidence of {m_score:.3f}. Applying "
        f"final_risk_score = sanction_score*{WEIGHTS['sanctions']} + "
        f"web_evidence_score*{WEIGHTS['web_evidence']} + "
        f"match_confidence*{WEIGHTS['match_confidence']} yields {total:.3f} "
        f"({band}). The strongest driver is {driver.replace('_', ' ')}."
    )
    if entity_name:
        summary = f"Deterministic assessment for {entity_name}: " + summary

    return RiskAssessment(
        risk_score=total,
        risk_classification=band,
        match_found=total > 0,
        sanction_score=round(s_score, 3),
        web_evidence_score=round(w_score, 3),
        match_confidence=round(m_score, 3),
        contributing_articles=len(articles),
        strongest_driver=driver,
        summary=summary,
        components={key: round(value, 4) for key, value in contributions.items()},
    )


def from_opensanctions_score(score: Any) -> RiskAssessment:
    """Fallback used when only an OpenSanctions match score is available."""
    confidence = clamp01(score)
    # A single strong name match is treated as one confirmed sanctions hit.
    matches = 1 if confidence > 0 else 0
    return assess(sanction_matches=matches, match_confidence=confidence)


def deviation(model_output: Mapping[str, Any], reference: RiskAssessment) -> dict[str, Any]:
    """Compare an LLM's answer with the deterministic reference.

    Returned by the flows as ``score_audit`` so drift is visible in the data
    rather than only in a log line.
    """
    model_score = clamp01(model_output.get("risk_score"))
    model_band = str(model_output.get("risk_classification", "")).upper()
    delta = round(model_score - reference.risk_score, 3)
    return {
        "model_risk_score": model_score,
        "reference_risk_score": reference.risk_score,
        "delta": delta,
        "abs_delta": abs(delta),
        "model_classification": model_band,
        "reference_classification": reference.risk_classification,
        "classification_agrees": model_band == reference.risk_classification,
        "within_tolerance": abs(delta) <= 0.15,
    }


# --------------------------------------------------------------------------- #
# Transaction-side risk banding (RPS)
# --------------------------------------------------------------------------- #

#: RPS thresholds are much tighter than the KYC bands: the fusion model's output
#: distribution is heavily skewed towards zero for legitimate accounts.
RPS_BAND_THRESHOLDS: tuple[tuple[float, str], ...] = (
    (0.30, RiskBand.HIGH),
    (0.15, RiskBand.MEDIUM),
    (0.00, RiskBand.LOW),
)


def rps_band(rps: float) -> str:
    """Map a fused risk propensity score to a band."""
    value = clamp01(rps)
    for threshold, band in RPS_BAND_THRESHOLDS:
        if value >= threshold:
            return band
    return RiskBand.LOW


def combine_independent(current: float, incoming: float) -> float:
    """Probabilistic union of two independent risk signals: 1 - (1-x)(1-y)."""
    return probabilistic_union((current, incoming))
