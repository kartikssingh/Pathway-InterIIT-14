"""Article fetching and storage.

Formerly ``scraping_test_new.py`` + ``compliance_data_reader.py``.

Two correctness fixes carried over from the original:

* the scraper appended to a single shared ``out/scraped_web_articles.jsonl`` and
  the reader then read *the whole file*, so an entity was scored against every
  other entity's articles.  Articles are now keyed by subject and only that
  subject's articles are returned.
* ``newspaper``/``news-please`` are optional imports; a missing extractor no
  longer prevents the module from importing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Iterator

from fraudguard.io.jsonl import append_jsonl, iter_jsonl, sanitise
from fraudguard.logging import get_logger

__all__ = ["Article", "fetch_articles", "store_articles", "load_articles", "articles_path"]

log = get_logger("fraudguard.articles")


@dataclass
class Article:
    url: str
    text: str = ""
    subject: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    fetched_at: str = ""

    @property
    def title(self) -> str:
        return str(self.metadata.get("title") or "")

    @property
    def ok(self) -> bool:
        return bool(self.text) and "error" not in self.metadata

    def to_dict(self) -> dict[str, Any]:
        return sanitise(
            {
                "url": self.url,
                "subject": self.subject,
                "text": self.text,
                "metadata": self.metadata,
                "fetched_at": self.fetched_at or datetime.utcnow().isoformat(),
            }
        )

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Article":
        return cls(
            url=str(payload.get("url") or ""),
            text=str(payload.get("text") or ""),
            subject=str(payload.get("subject") or ""),
            metadata=dict(payload.get("metadata") or {}),
            fetched_at=str(payload.get("fetched_at") or ""),
        )


def articles_path(name: str = "scraped_web_articles.jsonl") -> Path:
    from fraudguard.config import get_settings

    return get_settings().paths.out / name


# --------------------------------------------------------------------------- #
# Fetching
# --------------------------------------------------------------------------- #


def _extract_with_newsplease(url: str) -> Article | None:
    try:
        from newsplease import NewsPlease
    except ImportError:
        return None
    try:
        article = NewsPlease.from_url(url)
    except Exception:
        return None
    if not article or not getattr(article, "text", None):
        return None
    return Article(
        url=url,
        text=article.text,
        metadata={
            "title": article.title,
            "authors": list(article.authors or []),
            "date_publish": article.date_publish,
            "source_domain": article.source_domain,
            "extractor": "news-please",
        },
    )


def _extract_with_newspaper(url: str) -> Article | None:
    try:
        from newspaper import Article as NewspaperArticle
    except ImportError:
        return None
    try:
        article = NewspaperArticle(url)
        article.download()
        article.parse()
    except Exception:
        return None
    if not article.text:
        return None
    return Article(
        url=url,
        text=article.text,
        metadata={
            "title": article.title,
            "authors": list(article.authors or []),
            "date_publish": article.publish_date,
            "extractor": "newspaper",
        },
    )


def fetch_articles(urls: Iterable[str], *, subject: str = "") -> Iterator[Article]:
    """Fetch and extract each URL, falling back between extractors."""
    for url in urls:
        if not url:
            continue
        log.debug("Fetching article", extra={"url": url})
        article = _extract_with_newsplease(url) or _extract_with_newspaper(url)
        if article is None:
            log.info("Article extraction failed", extra={"url": url})
            article = Article(url=url, metadata={"error": "extraction failed"})
        article.subject = subject
        article.fetched_at = datetime.utcnow().isoformat()
        yield article


def store_articles(articles: Iterable[Article], *, path: Path | None = None) -> int:
    """Append articles to the shared corpus; returns how many were written."""
    target = path or articles_path()
    count = 0
    for article in articles:
        append_jsonl(target, article.to_dict())
        count += 1
    return count


def load_articles(
    *,
    subject: str | None = None,
    path: Path | None = None,
    only_ok: bool = True,
) -> list[Article]:
    """Read the corpus back, optionally filtered to a single subject.

    ``subject=None`` returns everything (matching the historical behaviour); pass
    a subject to get only that entity's evidence.
    """
    target = path or articles_path()
    wanted = (subject or "").strip().lower()
    articles: list[Article] = []
    for payload in iter_jsonl(target):
        article = Article.from_dict(payload)
        if only_ok and not article.ok:
            continue
        if wanted and article.subject.strip().lower() != wanted:
            continue
        articles.append(article)
    return articles


def collect_for_subject(
    subject: str,
    urls: Iterable[str],
    *,
    path: Path | None = None,
) -> list[Article]:
    """Fetch, persist and return the articles for one subject in a single pass."""
    fetched = list(fetch_articles(urls, subject=subject))
    store_articles(fetched, path=path)
    return [article for article in fetched if article.ok]
