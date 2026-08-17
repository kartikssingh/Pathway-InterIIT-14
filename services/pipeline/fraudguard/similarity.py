"""Text similarity used to decide whether adverse-media coverage has changed.

The scheduler fitted a fresh ``TfidfVectorizer`` on *two documents* for every
comparison.  With a corpus of two, IDF is degenerate and the result is closer to
a normalised term-overlap than a meaningful TF-IDF cosine — and scikit-learn is
a heavy import for the job.

This module keeps scikit-learn as the preferred implementation (so behaviour is
unchanged where it is installed) and falls back to a dependency-free cosine over
term-frequency vectors, which for a two-document corpus is near-identical.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from functools import lru_cache

__all__ = ["normalise", "text_similarity", "jaccard"]

_TOKEN_RE = re.compile(r"[a-z0-9']+")

# Small, fixed stop-word list — matches sklearn's 'english' closely enough for
# a two-document comparison and avoids the import when sklearn is absent.
_STOP_WORDS = frozenset(
    """
    a about above after again against all am an and any are as at be because been before being
    below between both but by can cannot could did do does doing down during each few for from
    further had has have having he her here hers herself him himself his how i if in into is it
    its itself me more most my myself no nor not of off on once only or other ought our ours
    ourselves out over own same she should so some such than that the their theirs them themselves
    then there these they this those through to too under until up very was we were what when
    where which while who whom why with would you your yours yourself yourselves
    """.split()
)


def normalise(text: str | None) -> str:
    """Lower-case and collapse whitespace."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", str(text).lower()).strip()


def _tokens(text: str) -> list[str]:
    return [token for token in _TOKEN_RE.findall(text) if token not in _STOP_WORDS]


@lru_cache(maxsize=1)
def _sklearn_available() -> bool:
    try:
        import sklearn.feature_extraction.text  # noqa: F401
    except ImportError:
        return False
    return True


def _sklearn_similarity(left: str, right: str) -> float:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    matrix = TfidfVectorizer(stop_words="english", max_features=1000).fit_transform([left, right])
    return float(cosine_similarity(matrix[0:1], matrix[1:2])[0][0])


def _pure_python_similarity(left: str, right: str) -> float:
    left_counts = Counter(_tokens(left))
    right_counts = Counter(_tokens(right))
    if not left_counts or not right_counts:
        return 0.0
    shared = set(left_counts) & set(right_counts)
    dot = sum(left_counts[token] * right_counts[token] for token in shared)
    if not dot:
        return 0.0
    left_norm = math.sqrt(sum(value * value for value in left_counts.values()))
    right_norm = math.sqrt(sum(value * value for value in right_counts.values()))
    return dot / (left_norm * right_norm)


def text_similarity(left: str | None, right: str | None) -> float:
    """Cosine similarity of two documents, rounded to four decimals, in [0, 1]."""
    left_text, right_text = normalise(left), normalise(right)
    if not left_text or not right_text:
        return 0.0
    if left_text == right_text:
        return 1.0
    try:
        score = _sklearn_similarity(left_text, right_text) if _sklearn_available() else (
            _pure_python_similarity(left_text, right_text)
        )
    except Exception:
        score = _pure_python_similarity(left_text, right_text)
    return round(max(0.0, min(1.0, score)), 4)


def jaccard(left: str | None, right: str | None) -> float:
    """Set overlap of the significant tokens — a coarser change signal."""
    left_tokens = set(_tokens(normalise(left)))
    right_tokens = set(_tokens(normalise(right)))
    if not left_tokens or not right_tokens:
        return 0.0
    return round(len(left_tokens & right_tokens) / len(left_tokens | right_tokens), 4)
