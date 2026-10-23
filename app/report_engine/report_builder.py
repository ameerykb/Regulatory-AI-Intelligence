
"""
Build structured, evidence-backed regulatory change reports.
"""

from typing import Any


def build_regulatory_change_report(
    evidence_records: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Convert evidence-backed changes into a structured report.

    Args:
        evidence_records: Results from retrieve_all_change_evidence.

    Returns:
        A report containing a summary and individual change records.
    """
    if not isinstance(evidence_records, list):
        raise ValueError("Evidence records must be a list.")

    report_items = []

    for record in evidence_records:
        change = record["change"]
        draft = record["draft_evidence"]
        final = record["final_evidence"]

        report_item = {
            "draft_rule_number": draft["rule_number"],
            "final_rule_number": final["rule_number"],
            "draft_title": draft["title"],
            "final_title": final["title"],
            "change_status": change["status"],
            "change_count": len(change["changes"]),
            "detected_changes": change["changes"],
            "draft_source": {
                "rule_id": draft["rule_id"],
                "source_file": draft["source_file"],
                "text": draft["text"],
            },
            "final_source": {
                "rule_id": final["rule_id"],
                "source_file": final["source_file"],
                "text": final["text"],
            },
            "review_status": record["review_status"],
        }

        report_items.append(report_item)

    return {
        "report_type": "regulatory_change_evidence_report",
        "total_changes": len(report_items),
        "review_required_count": sum(
            item["review_status"] == "requires_human_review"
            for item in report_items
        ),
        "changes": report_items,
    }
