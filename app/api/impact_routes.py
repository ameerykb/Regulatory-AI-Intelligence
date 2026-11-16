
"""Phase 5: Regulatory impact API and report exports."""

import json
import re
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.impact_engine.phase4_impact import assess

router = APIRouter(prefix="/impact", tags=["Policy Impact"])

ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = ROOT / "data" / "comparisons"


def validate_id(comparison_id: str):
    if not re.fullmatch(r"[0-9a-f]{32}", comparison_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid comparison ID",
        )
    return comparison_id


def report_path(comparison_id: str):
    validate_id(comparison_id)
    return REPORT_DIR / f"{comparison_id}_phase4_impact.json"


def load_report(comparison_id: str):
    path = report_path(comparison_id)

    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Impact report not found. Run analysis first.",
        )

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise HTTPException(
            status_code=500,
            detail="Saved report could not be read.",
        )


def markdown_report(report):
    lines = [
        "# Regulatory Policy Impact Assessment",
        "",
        f"Comparison ID: {report['comparison_id']}",
        "",
        f"Policy sections checked: {report['policy_sections_checked']}",
        "",
        f"Modified rules: {report['modified_rules_evaluated']}",
        "",
        f"AI status: {report.get('ai_status', 'unknown')}",
        "",
        "**Preliminary analysis ? human review required.**",
        "",
    ]

    for finding in report.get("findings", []):
        lines.extend([
            f"## Rule {finding['final_rule_number']}: "
            f"{finding['rule_title']}",
            "",
            "### Regulatory evidence",
            "",
            finding["regulatory_evidence"]["text"],
            "",
            "### Detected changes",
            "",
        ])

        for change in finding.get("detected_changes", []):
            lines.extend([
                f"- Operation: {change.get('operation', 'unknown')}",
                f"  - Previous: {change.get('draft_text', '')}",
                f"  - Updated: {change.get('final_text', '')}",
            ])

        lines.extend([
            "",
            "### Preliminary impact assessment",
            "",
            f"Impact level: {finding.get('impact_level', 'not_assessed')}",
            "",
            f"Assessment status: {finding.get('assessment_status', 'unknown')}",
            "",
            f"Policy match status: {finding.get('policy_match_status', 'unknown')}",
            "",
            f"Reason: {finding.get('impact_reason', 'Not available.')}",
            "",
            "### Potentially affected policies",
            "",
        ])

        if not finding.get("potential_policy_matches"):
            lines.extend([
                "No company policy met the preliminary relevance threshold.",
                "Manual review is required.",
                "",
            ])

        for match in finding.get("potential_policy_matches", []):
            lines.extend([
                f"#### {match['policy_section']}",
                "",
                f"Ranking score: {match['ranking_score']}",
                "",
                match["policy_text"],
                "",
            ])

        lines.extend([
            "### AI preliminary explanation",
            "",
            finding.get(
                "ai_preliminary_explanation",
                "AI explanation unavailable.",
            ),
            "",
            "Human review required: Yes",
            "",
        ])

    lines.extend([
        "---",
        "",
        report.get(
            "disclaimer",
            "This is not a legal compliance determination.",
        ),
    ])

    return "\n".join(lines) + "\n"


@router.post("/{comparison_id}/analyze")
def analyze_impact(comparison_id: str):
    validate_id(comparison_id)

    try:
        report, output = assess(comparison_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Comparison files not found",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        )
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Impact analysis failed. Check server logs.",
        )

    return {
        "status": "completed",
        "comparison_id": comparison_id,
        "ai_status": report["ai_status"],
        "modified_rules_evaluated": report["modified_rules_evaluated"],
        "report_file": output.name,
        "review_required": True,
    }


@router.get("/{comparison_id}")
def get_impact(comparison_id: str):
    return load_report(comparison_id)


@router.get("/{comparison_id}/download")
def download_impact(
    comparison_id: str,
    format: Literal["json", "md"] = "json",
):
    report = load_report(comparison_id)

    if format == "json":
        return FileResponse(
            path=report_path(comparison_id),
            media_type="application/json",
            filename=f"{comparison_id}_impact.json",
        )

    output = REPORT_DIR / f"{comparison_id}_impact.md"
    output.write_text(
        markdown_report(report),
        encoding="utf-8",
    )

    return FileResponse(
        path=output,
        media_type="text/markdown",
        filename=f"{comparison_id}_impact.md",
    )
