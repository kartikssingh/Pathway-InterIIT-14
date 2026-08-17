"""Shared runtime plumbing for Pathway flows.

Each flow used to repeat the same twenty lines: load ``.env``, build the rdkafka
dict, make ``out/``, set the licence key, decide on a persistence backend, call
``pw.run``.  They also all shared ``group.id=0``, so two flows consuming the same
topic silently split its partitions between them.
"""

from __future__ import annotations

import signal
import sys
from pathlib import Path
from typing import Any, Callable

from fraudguard.config import Settings, get_settings
from fraudguard.logging import configure, get_logger

__all__ = ["FlowContext", "flow_main", "set_license", "persistence_for"]


class FlowContext:
    """Everything a flow needs, built once."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.log = configure(name)
        self.settings: Settings = get_settings()
        self.paths = self.settings.paths

    # -- convenience ------------------------------------------------------- #

    @property
    def kafka(self) -> dict[str, str]:
        """rdkafka settings with a consumer group unique to this flow."""
        return self.settings.kafka.rdkafka(group_suffix=self.name)

    @property
    def topics(self):
        return self.settings.kafka

    def out(self, filename: str) -> str:
        return str(self.paths.out / filename)

    def state_dir(self, subdir: str | None = None) -> Path:
        path = self.paths.state / (subdir or self.name)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def require(self, *keys: str) -> None:
        from fraudguard.config import require

        require(self.settings, keys)


def set_license(context: FlowContext) -> None:
    """Apply the Pathway licence key when one is configured.

    Flows that need Scale features (the MCP server) should call this; the rest
    run fine on Pathway Community.
    """
    if not context.settings.pathway_license:
        context.log.info("No PW_LICENSE set; running on Pathway Community features")
        return
    import pathway as pw

    pw.set_license_key(context.settings.pathway_license)
    context.log.info("Pathway licence applied")


def persistence_for(context: FlowContext, subdir: str | None = None) -> Any:
    """Filesystem persistence config so a restart resumes instead of replaying."""
    import pathway as pw

    backend = pw.persistence.Backend.filesystem(str(context.state_dir(subdir)))
    return pw.persistence.Config(backend)


def flow_main(
    name: str,
    build: Callable[[FlowContext], None],
    *,
    persistent: bool = False,
    needs_license: bool = False,
    monitoring: bool = False,
) -> Callable[[], int]:
    """Wrap a graph builder into a ``main()`` with logging, signals and error handling.

    ``build`` receives the context and declares the Pathway graph; this function
    owns the run loop.
    """

    def main() -> int:
        import pathway as pw

        context = FlowContext(name)
        log = context.log
        log.info(
            "Starting flow",
            extra={
                "flow": name,
                "env": context.settings.env,
                "out_dir": str(context.paths.out),
                "bootstrap": context.settings.kafka.bootstrap_servers,
            },
        )

        def _shutdown(signum: int, _frame: Any) -> None:
            log.info("Received signal, shutting down", extra={"signal": signum})
            from fraudguard.io.postgres import close_pool

            close_pool()
            sys.exit(0)

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                signal.signal(sig, _shutdown)
            except ValueError:  # not on the main thread
                pass

        if needs_license:
            set_license(context)

        try:
            build(context)
        except Exception as exc:
            log.exception("Failed to build the dataflow: %s", exc)
            return 2

        kwargs: dict[str, Any] = {
            "monitoring_level": pw.MonitoringLevel.AUTO
            if monitoring
            else pw.MonitoringLevel.NONE
        }
        if persistent:
            kwargs["persistence_config"] = persistence_for(context)

        try:
            pw.run(**kwargs)
        except KeyboardInterrupt:
            log.info("Interrupted by user")
            return 130
        except Exception as exc:
            log.exception("Flow crashed: %s", exc)
            return 1
        finally:
            from fraudguard.io.postgres import close_pool

            close_pool()

        log.info("Flow finished", extra={"flow": name})
        return 0

    main.__name__ = f"{name}_main"
    return main
