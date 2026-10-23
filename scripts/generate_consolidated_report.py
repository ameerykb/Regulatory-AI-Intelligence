
"""Generate a consolidated preliminary regulatory impact report."""

import json
from datetime import datetime, timezone
from pathlib import Path


REPORTS_DIR = Path("data/reports")


def load_json(filename: str) -> dict:
    path = REPORTS_DIR / filename

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def main():
    regulatory_report = load_json(
        "dpdp_2025_evidence_report.json"
    )

    policy_impact_report = load_json(
        "dpdp_2025_policy_impact_report.json"
    )

    impact_evidence_report = load_json(
        "dpdp_2025_impact_evidence_report.json"
    )

    consolidated_report = {
        "report_type": "consolidated_regulatory_impact_report",
        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "regulatory_changes": regulatory_report["changes"],
        "policy_impact_summary": policy_impact_report["summary"],
        "evidence_summary": impact_evidence_report["summary"],
        "review_priority_summary": impact_evidence_report[
            "review_priority_summary"
        ],
        "evidence_records": impact_evidence_report[
            "evidence_records"
        ],
        "manual_review_groups": impact_evidence_report[
            "manual_review_groups"
        ],
        "limitations": impact_evidence_report["limitations"],
    }

    output_path = (
        REPORTS_DIR / "dpdp_2025_consolidated_report.json"
    )

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            consolidated_report,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print("Consolidated report generated successfully!")
    print("Saved to:", output_path)
    print(
        "Regulatory rule pairs:",
        len(consolidated_report["regulatory_changes"]),
    )
    print(
        "Evidence records:",
        len(consolidated_report["evidence_records"]),
    )
    print(
        "Unmatched groups:",
        len(consolidated_report["manual_review_groups"]),
    )


if __name__ == "__main__":
    main()
