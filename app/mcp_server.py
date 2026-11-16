
"""Local MCP tools for Regulatory AI Intelligence."""

import json
import re
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from app.impact_engine.phase4_impact import assess
from app.impact_engine.semantic_matcher import get_semantic_model

# Initialize ML dependencies in the main thread before
# MCP begins handling requests in worker threads.
get_semantic_model()

mcp = FastMCP("Regulatory AI Intelligence")

ROOT = Path(__file__).resolve().parents[1]
COMPARISONS = ROOT / "data" / "comparisons"


def validate_id(comparison_id: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{32}", comparison_id):
        raise ValueError(
            "Comparison ID must contain exactly 32 lowercase "
            "hexadecimal characters."
        )
    return comparison_id


def read_json(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(
            "Requested comparison or report does not exist."
        )

    return json.loads(path.read_text(encoding="utf-8"))


@mcp.tool()
def get_regulatory_comparison(comparison_id: str) -> dict:
    """Retrieve detected regulatory changes for a saved comparison."""
    comparison_id = validate_id(comparison_id)

    path = COMPARISONS / f"{comparison_id}_changes.json"
    return read_json(path)


@mcp.tool()
async def analyze_policy_impact(comparison_id: str) -> dict:
    """Run local AI-assisted policy impact analysis for a comparison."""
    import asyncio

    comparison_id = validate_id(comparison_id)

    report, output = await asyncio.to_thread(
        assess, comparison_id
    )

    return {
        "comparison_id": comparison_id,
        "ai_status": report["ai_status"],
        "modified_rules_evaluated": (
            report["modified_rules_evaluated"]
        ),
        "policy_sections_checked": (
            report["policy_sections_checked"]
        ),
        "report_file": output.name,
        "review_required": True,
    }


@mcp.tool()
def get_policy_impact_report(comparison_id: str) -> dict:
    """Retrieve a previously generated policy impact report."""
    comparison_id = validate_id(comparison_id)

    path = (
        COMPARISONS /
        f"{comparison_id}_phase4_impact.json"
    )

    return read_json(path)


if __name__ == "__main__":
    mcp.run(transport="stdio")
