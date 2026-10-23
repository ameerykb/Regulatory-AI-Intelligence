
"""Tests for the regulatory change report builder."""

from app.report_engine.report_builder import (
    build_regulatory_change_report,
)


def test_build_regulatory_change_report():
    """Build a structured report from evidence-backed changes."""

    evidence_records = [
        {
            "change": {
                "status": "modified",
                "changes": [
                    {
                        "operation": "replace",
                        "draft_text": "old requirement",
                        "final_text": "new requirement",
                    }
                ],
            },
            "draft_evidence": {
                "rule_id": "dpdp_draft_2025_rule_7",
                "rule_number": 7,
                "title": "Breach notification",
                "source_file": "draft.json",
                "text": "Draft rule text",
            },
            "final_evidence": {
                "rule_id": "dpdp_final_2025_rule_7",
                "rule_number": 7,
                "title": "Breach notification",
                "source_file": "final.json",
                "text": "Final rule text",
            },
            "review_status": "requires_human_review",
        }
    ]

    report = build_regulatory_change_report(evidence_records)

    assert report["total_changes"] == 1
    assert report["review_required_count"] == 1

    first = report["changes"][0]

    assert first["draft_rule_number"] == 7
    assert first["final_rule_number"] == 7
    assert first["change_status"] == "modified"
    assert first["change_count"] == 1

    assert first["draft_source"]["text"] == "Draft rule text"
    assert first["final_source"]["text"] == "Final rule text"

    assert first["review_status"] == "requires_human_review"
