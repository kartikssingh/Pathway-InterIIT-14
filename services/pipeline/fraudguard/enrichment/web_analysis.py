"""Adverse-media analysis: search → fetch → reputation → LLM authenticity → prompt.

This replaces ``run_web_analysis`` in the old ``llm_output.py``, which was a
200-line function that searched, scraped, called three reputation APIs, invoked
an LLM per article, parsed the reply and rendered a prompt — all inside a single
``try``/``except: continue``.

Fixes carried over:

* the subject name was interpolated straight into ``re.search`` — any entity with
  a ``.``, ``(`` or ``+`` in their name either over-matched or raised
  ``re.error`` and silently dropped all their evidence.  Matching is now literal
  and diacritic-insensitive.
* every entity was scored against the *entire* shared article corpus.
* the LLM reply was indexed positionally (``output[1][...]``), which broke on
  Pathway versions that return a different tuple shape.
* a guardrail failure on one article aborted that article's contribution without
  any record; failures are now counted and reported.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Sequence

import pathway as pw

from fraudguard import scoring
from fraudguard.enrichment.articles import Article, collect_for_subject, load_articles
from fraudguard.enrichment.reputation import ReputationSignals, assess_source
from fraudguard.enrichment.search import find_adverse_links
from fraudguard.errors import FraudGuardError
from fraudguard.llm import client as llm_client
from fraudguard.llm import prompts
from fraudguard.logging import get_logger

__all__ = ["WebAnalysis", "analyse", "run_web_analysis", "NO_EVIDENCE"]

log = get_logger("fraudguard.web_analysis")

#: How many articles are rendered into the compliance prompt.
TOP_N_ARTICLES = 3


@dataclass
class ArticleFinding:
    article: Article
    signals: ReputationSignals
    authenticity: float
    reasoning: str = ""

    @property
    def evidence(self) -> scoring.ArticleEvidence:
        return scoring.ArticleEvidence(
            url=self.article.url,
            title=self.article.title,
            authenticity=self.authenticity,
            excerpt=self.article.text[:400],
        )

    def sort_key(self) -> tuple[float, bool, int]:
        return (self.authenticity, self.signals.has_history, self.signals.threat_pulses)


@dataclass
class WebAnalysis:
    subject: str
    prompt: str
    citations: list[str] = field(default_factory=list)
    findings: list[ArticleFinding] = field(default_factory=list)
    articles_considered: int = 0
    guardrail_rejections: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def evidence(self) -> list[scoring.ArticleEvidence]:
        return [finding.evidence for finding in self.findings]

    def as_tuple(self) -> tuple[str, list[str]]:
        """Backwards-compatible ``(prompt, citations)`` shape for Pathway flows."""
        return self.prompt, self.citations

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject": self.subject,
            "prompt": self.prompt,
            "citations": self.citations,
            "articles_considered": self.articles_considered,
            "articles_used": len(self.findings),
            "guardrail_rejections": self.guardrail_rejections,
            "errors": self.errors,
            "sources": [
                {
                    "url": finding.article.url,
                    "title": finding.article.title,
                    "authenticity": finding.authenticity,
                    "reasoning": finding.reasoning,
                    **finding.signals.to_dict(),
                }
                for finding in self.findings
            ],
        }


NO_EVIDENCE = "No relevant adverse media found."


# --------------------------------------------------------------------------- #
# Name matching
# --------------------------------------------------------------------------- #


def _fold(text: str) -> str:
    """Lower-case and strip diacritics so 'José' matches 'Jose'."""
    normalised = unicodedata.normalize("NFKD", text or "")
    return "".join(char for char in normalised if not unicodedata.combining(char)).lower()


def _mentions(name: str, *haystacks: str) -> bool:
    """Literal, accent-insensitive name match (no regex injection)."""
    needle = _fold(name).strip()
    if not needle:
        return False
    pattern = re.compile(r"\b" + re.escape(needle).replace(r"\ ", r"\s+") + r"\b")
    return any(pattern.search(_fold(text or "")) for text in haystacks)


# --------------------------------------------------------------------------- #
# Per-article scoring
# --------------------------------------------------------------------------- #


def _rate_article(article: Article, signals: ReputationSignals) -> tuple[float, str]:
    """Ask the LLM how authentic an article looks; fall back to content signals."""
    user_prompt = prompts.article_authenticity_user_prompt(
        url=article.url,
        text=article.text[:500],
        alexa_rank=signals.alexa_rank,
        akamai_rank=signals.akamai_rank,
        content_signal_score=signals.content_score,
        has_domain_history=signals.has_history,
    )
    try:
        payload = llm_client.complete_json(
            prompts.ARTICLE_AUTHENTICITY_SYSTEM_PROMPT, user_prompt, attempts=2
        )
    except FraudGuardError as exc:
        log.info(
            "Falling back to content signals for authenticity",
            extra={"url": article.url, "error": str(exc)[:200]},
        )
        return signals.content_score, "LLM unavailable; scored from page structure signals."

    score = scoring.clamp01(payload.get("authenticity_score", signals.content_score))
    reasoning = str(payload.get("reasoning") or "").strip()
    return score, reasoning


def _render_prompt(subject: str, findings: Sequence[ArticleFinding]) -> tuple[str, list[str]]:
    if not findings:
        return f"{NO_EVIDENCE} (subject: {subject})", []

    citations = [f"- [{index + 1}] {f.article.url}" for index, f in enumerate(findings)]
    blocks = []
    for index, finding in enumerate(findings, start=1):
        signals = finding.signals
        blocks.append(
            f"--- Article {index} ---\n"
            f"Title: {finding.article.title or 'Untitled'}\n"
            f"URL: {finding.article.url}\n"
            f"Authenticity Score: {finding.authenticity:.2f}"
            + (f" (Reasoning: {finding.reasoning})" if finding.reasoning else "")
            + "\n"
            f"(Archive history: {signals.has_history}, AlienVault: {signals.alexa_rank}, "
            f"OTX pulses: {signals.threat_pulses}, "
            f"OTX tags: {', '.join(signals.threat_tags) or 'none'})\n"
            f"Snippet: {finding.article.text[:200].strip()}..."
        )
    return f"Web findings for **{subject}**:\n\n" + "\n\n".join(blocks), citations


# --------------------------------------------------------------------------- #
# Entry points
# --------------------------------------------------------------------------- #


def analyse(
    subject: str,
    extra_urls: Sequence[str] | None = None,
    *,
    scrape: bool = True,
    top_n: int = TOP_N_ARTICLES,
) -> WebAnalysis:
    """Full adverse-media analysis for one subject."""
    subject = (subject or "").strip()
    if not subject:
        return WebAnalysis(subject="", prompt="No name provided.")

    from fraudguard.llm import guard

    analysis = WebAnalysis(subject=subject, prompt="")

    if scrape:
        urls = find_adverse_links(subject)
        urls.extend(url for url in (extra_urls or []) if url)
        articles = collect_for_subject(subject, urls)
    else:
        articles = load_articles(subject=subject)

    if not articles:
        analysis.prompt = f"{NO_EVIDENCE} (subject: {subject})"
        return analysis

    findings: list[ArticleFinding] = []
    for article in articles:
        analysis.articles_considered += 1
        if not _mentions(subject, article.title, article.text[:1000]):
            continue

        verdict = guard.validate(article.text[:2000], label="article")
        if not verdict.ok:
            analysis.guardrail_rejections += 1
            continue

        try:
            signals = assess_source(article.url)
            authenticity, reasoning = _rate_article(article, signals)
        except Exception as exc:  # one bad article must not sink the entity
            analysis.errors.append(f"{article.url}: {exc}")
            log.warning("Article analysis failed", extra={"url": article.url, "error": str(exc)})
            continue

        findings.append(
            ArticleFinding(
                article=article, signals=signals, authenticity=authenticity, reasoning=reasoning
            )
        )

    findings.sort(key=ArticleFinding.sort_key, reverse=True)
    analysis.findings = findings[:top_n]
    analysis.prompt, analysis.citations = _render_prompt(subject, analysis.findings)

    log.info(
        "Web analysis complete",
        extra={
            "subject": subject,
            "considered": analysis.articles_considered,
            "used": len(analysis.findings),
            "rejected": analysis.guardrail_rejections,
        },
    )
    return analysis


@pw.udf(return_type=tuple[str, list[str]], deterministic=False)
def run_web_analysis(subject: str, face_match_urls: list[str] | None = None) -> tuple[str, list[str]]:
    """Pathway UDF returning ``(prompt_text, citations)``."""
    return analyse(subject, face_match_urls or []).as_tuple()


@pw.udf(return_type=dict, deterministic=False)
def run_web_analysis_detailed(
    subject: str, face_match_urls: list[str] | None = None
) -> dict:
    """Pathway UDF returning the full analysis, including per-source signals."""
    return analyse(subject, face_match_urls or []).to_dict()
