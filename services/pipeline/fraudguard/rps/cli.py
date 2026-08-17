"""Launcher for the RPS scoring service."""

from __future__ import annotations

import argparse
from typing import Sequence

from fraudguard.logging import configure


def main(argv: Sequence[str] | None = None) -> int:
    from fraudguard.config import get_settings

    settings = get_settings()
    parser = argparse.ArgumentParser(description="Run the RPS scoring HTTP service.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=settings.rps_api_port)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--reload", action="store_true", help="Auto-reload on code changes.")
    args = parser.parse_args(argv)

    log = configure("rps-service")
    log.info("Starting scorer", extra={"host": args.host, "port": args.port})

    import uvicorn

    uvicorn.run(
        "fraudguard.rps.service:app",
        host=args.host,
        port=args.port,
        workers=1 if args.reload else args.workers,
        reload=args.reload,
        log_config=None,  # our logging is already configured
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
