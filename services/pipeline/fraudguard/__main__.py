"""Unified entry point: ``python -m fraudguard <command> [args...]``.

The pipeline used to be nine loose scripts, each started with its own
``python3 path/to/file.py`` incantation that only worked from one specific
working directory.  One dispatcher means one documented way to start anything,
and ``--list`` is the authoritative inventory.
"""

from __future__ import annotations

import argparse
import importlib
import sys
from dataclasses import dataclass
from typing import Callable, Sequence


@dataclass(frozen=True)
class Command:
    name: str
    module: str
    summary: str
    requires: str = ""


COMMANDS: tuple[Command, ...] = (
    Command(
        "kyc-ocr",
        "fraudguard.flows.kyc_ocr",
        "Watch S3 for KYC PDFs, extract fields and publish applicants.",
        "AWS + Google Document AI credentials",
    ),
    Command(
        "kyc-enrichment",
        "fraudguard.flows.kyc_enrichment",
        "Screen applicants, research adverse media and score them.",
        "OS_API_KEY, MISTRAL_KEY",
    ),
    Command(
        "db-sink",
        "fraudguard.flows.db_sink",
        "Persist enriched reports into Postgres via Staging_Buffer.",
        "POSTGRES_PASSWORD",
    ),
    Command(
        "rps-features",
        "fraudguard.flows.rps_features",
        "Build per-user transaction features from Debezium CDC.",
        "POSTGRES_PASSWORD, Debezium",
    ),
    Command(
        "rps-explain",
        "fraudguard.flows.rps_explain",
        "Score feature vectors and attach an LLM explanation.",
        "the scorer on SCORE_URL",
    ),
    Command(
        "mcp-server",
        "fraudguard.flows.mcp_server",
        "Serve the OFAC / PEP / adverse-media checks as MCP tools.",
        "PW_LICENSE",
    ),
    Command(
        "mcp-agent",
        "fraudguard.flows.mcp_agent",
        "Validate high-risk verdicts with an agent and raise alerts.",
        "GEMINI_API_KEY, the MCP server",
    ),
    Command(
        "rag-server",
        "fraudguard.flows.rag_server",
        "Serve delta re-assessment questions over the watchdog corpus.",
        "MISTRAL_KEY",
    ),
    Command(
        "watchdog",
        "fraudguard.flows.watchdog",
        "Re-screen onboarded entities once and report what changed.",
        "POSTGRES_PASSWORD, OS_API_KEY",
    ),
    Command(
        "scheduler",
        "fraudguard.scheduler.watchdog_scheduler",
        "Run the watchdog continuously on an adaptive interval.",
        "the RAG server",
    ),
    Command(
        "scorer",
        "fraudguard.rps.cli",
        "Run the RPS scoring HTTP service (uvicorn).",
        "ml/models artefacts",
    ),
    Command(
        "doctor",
        "fraudguard.doctor",
        "Check configuration, connectivity and model artefacts.",
    ),
)

_BY_NAME = {command.name: command for command in COMMANDS}


def _print_commands() -> None:
    width = max(len(command.name) for command in COMMANDS)
    print("Available commands:\n")
    for command in COMMANDS:
        print(f"  {command.name.ljust(width)}  {command.summary}")
        if command.requires:
            print(f"  {' ' * width}  needs: {command.requires}")
    print("\nRun a command with:  python -m fraudguard <command> [--help]")


def _resolve(command: Command) -> Callable[..., int]:
    module = importlib.import_module(command.module)
    entry = getattr(module, "main", None)
    if entry is None:
        raise SystemExit(f"{command.module} does not define main()")
    return entry


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    parser = argparse.ArgumentParser(
        prog="python -m fraudguard",
        description="FraudGuard streaming compliance pipeline.",
        add_help=False,
    )
    parser.add_argument("command", nargs="?", help="Which flow to run.")
    parser.add_argument("--list", action="store_true", help="List the available commands.")
    parser.add_argument("-h", "--help", action="store_true", help="Show this message.")
    known, rest = parser.parse_known_args(argv)

    if known.list or (known.help and not known.command) or not known.command:
        parser.print_help()
        print()
        _print_commands()
        return 0 if (known.list or known.help) else 1

    command = _BY_NAME.get(known.command)
    if command is None:
        print(f"Unknown command: {known.command}\n", file=sys.stderr)
        _print_commands()
        return 2

    entry = _resolve(command)
    if known.help:
        rest.append("--help")

    # Flow ``main()`` functions built by ``flow_main`` take no arguments; the
    # CLI-style ones accept an argv list.  Decide by signature rather than by
    # catching TypeError, which would also swallow errors raised inside the flow.
    import inspect

    takes_argv = bool(inspect.signature(entry).parameters)
    if rest and not takes_argv:
        print(f"'{command.name}' takes no arguments (got {rest})", file=sys.stderr)
        return 2
    return int((entry(rest) if takes_argv else entry()) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
