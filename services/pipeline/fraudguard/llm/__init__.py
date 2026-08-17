"""LLM access: one shared client, content guardrails and the prompt templates.

``prompts`` is dependency-free; ``client`` needs Pathway and ``guard`` needs
guardrails-ai, so nothing is re-exported here.
"""

__all__ = ["client", "guard", "prompts"]
