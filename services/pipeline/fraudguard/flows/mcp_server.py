"""MCP tool server.

Exposes the compliance checks as Model Context Protocol tools so an agent can
call them on demand:

* ``ofac_call``  — OFAC sanctions screening for a name;
* ``pep_call``   — Politically Exposed Person screening for a name;
* ``news_call``  — adverse-media search and rating for a name.

Replaces ``mcp/mcp_server.py``:

* the screening logic was inlined in the server module and duplicated
  ``open_sanctions.py`` almost line for line; both now call
  :mod:`fraudguard.enrichment`;
* ``news_call`` was registered but commented out, leaving a dead branch;
* the request schema demanded ``score: float`` and ``explanation: str`` for
  every tool even though only ``name`` was ever read;
* ``pw.set_license_key(os.environ["PW_LICENSE"])`` at import raised ``KeyError``
  when the variable was absent instead of a usable message.
"""

from __future__ import annotations

import pathway as pw

from fraudguard.enrichment.ofac import ofac_screen
from fraudguard.enrichment.opensanctions import os_lookup
from fraudguard.enrichment.web_analysis import run_web_analysis_detailed
from fraudguard.flows._runtime import FlowContext, flow_main
from fraudguard.logging import get_logger

log = get_logger("fraudguard.flows.mcp_server")

FLOW_NAME = "mcp-server"

MCP_HOST = "MCP_HOST"
MCP_PORT = "MCP_PORT"


class NameRequest(pw.Schema):
    """Every tool takes a single subject name."""

    name: str


def _build_tools() -> object:
    from pathway.xpacks.llm.mcp_server import McpServable, McpServer

    class ComplianceTools(McpServable):
        """Sanctions, PEP and adverse-media checks."""

        def ofac_call(self, request: pw.Table) -> pw.Table:
            """Check whether `name` appears on the OFAC sanctions lists."""
            return request.select(result=ofac_screen(request.name))

        def pep_call(self, request: pw.Table) -> pw.Table:
            """Check whether `name` is a Politically Exposed Person or sanctioned entity."""
            return request.select(result=os_lookup(request.name))

        def news_call(self, request: pw.Table) -> pw.Table:
            """Search and rate adverse media about `name`."""
            return request.select(result=run_web_analysis_detailed(request.name))

        def register_mcp(self, server: McpServer) -> None:
            for tool_name, handler in (
                ("ofac_call", self.ofac_call),
                ("pep_call", self.pep_call),
                ("news_call", self.news_call),
            ):
                server.tool(tool_name, request_handler=handler, schema=NameRequest)
                log.info("Registered MCP tool", extra={"tool": tool_name})

    return ComplianceTools()


def build(context: FlowContext) -> None:
    import os

    from pathway.xpacks.llm.mcp_server import PathwayMcp

    host = os.environ.get(MCP_HOST, "0.0.0.0")
    port = int(os.environ.get(MCP_PORT, "8123"))

    PathwayMcp(
        name="fraudguard-compliance",
        transport="streamable-http",
        host=host,
        port=port,
        serve=[_build_tools()],
    )
    context.log.info("MCP server listening", extra={"host": host, "port": port})


main = flow_main(FLOW_NAME, build, needs_license=True)

if __name__ == "__main__":
    raise SystemExit(main())
