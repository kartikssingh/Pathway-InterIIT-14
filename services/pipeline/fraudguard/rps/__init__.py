"""Risk Propensity Score: inference engine, model registry and HTTP service.

``engine`` loads pickled models on first use and ``service`` needs FastAPI, so
import the submodule you need rather than the package.
"""

__all__ = ["cli", "engine", "registry", "service"]
