"""Read-only MCP surface for the Revenue Intelligence Council."""

from __future__ import annotations

import sys
from pathlib import Path

from mcp.server import MCPServer

sys.path.insert(0, str(Path(__file__).parent / "src"))

from salescout.council import CouncilRequest, execute, get_run  # noqa: E402


server = MCPServer(
    "revenue-intelligence-council",
    description="Evidence-backed account analysis with no email or CRM mutation tools.",
)


@server.tool()
def get_capabilities() -> dict:
    """Describe the council and its non-negotiable safety boundary."""
    return {
        "mode": "synthetic replay",
        "tools": ["analyze_account", "read_run"],
        "external_mutations": "not exposed",
        "approvals": "REST-only review state; MCP remains read-only",
    }


@server.tool()
def analyze_account(scenario: str, idempotency_key: str) -> dict:
    """Analyze one named synthetic account and return a draft-only record."""
    return execute(CouncilRequest(
        scenario=scenario,
        mode="replay",
        idempotency_key=idempotency_key,
    )).model_dump(mode="json")


@server.tool()
def read_run(run_id: str) -> dict:
    """Read a previously-created replay run from this process."""
    record = get_run(run_id)
    if not record:
        raise ValueError("run not found in this MCP process")
    return record.model_dump(mode="json")


if __name__ == "__main__":
    server.run()
