"""External-data enrichment: sanctions screening, adverse media, source reputation.

Submodules are imported on demand rather than re-exported here, so pulling in
``opensanctions`` does not also load the article extractors and the LLM client.
"""

__all__ = ["articles", "ofac", "opensanctions", "reputation", "search", "web_analysis"]
