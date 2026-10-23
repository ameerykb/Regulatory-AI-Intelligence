
import json
from datetime import datetime, timezone
from pathlib import Path

from app.impact_engine.evidence_analyzer import (
    generate_rule_evidence,
    summarize_impact_evidence,
    summarize_review_priorities,
)
from app.impact_engine.policy_loader import (
    load_company_policy,
    extract_policy_sections,
)


def main():
    reports_folder = Path("data/reports")

    regulatory_path = reports_folder / "dpdp_2025_evidence_report.json"
    impact_path = reports_folder / "dpdp_2025_policy_impact_report.json"
    output_path = reports_folder / "dpdp_2025_impact_evidence_report.json"

    with regulatory_path.open("r", encoding="utf-8") as file:
        regulatory_report = json.load(file)

    with impact_path.open("r", encoding="utf-8") as file:
        impact_report = json.load(file)

    changes = regulatory_report["changes"]
    rule_results = impact_report["rule_results"]

    policy_sections = extract_policy_sections(
        load_company_policy()
    )

    summary = summarize_impact_evidence(
        changes,
        rule_results,
        policy_sections,
    )

    evidence_records = []
    manual_review_groups = []

    for change, rule_result in zip(changes, rule_results):
        evidence_records.extend(
            generate_rule_evidence(
                change,
                rule_result,
                policy_sections,
            )
        )

        for group in rule_result["change_groups"]:
            if not group["filtered_policy_matches"]:
                manual_review_groups.append({
                    "draft_rule_number": change["draft_rule_number"],
                    "final_rule_number": change["final_rule_number"],
                    "group_number": group["group_number"],
                    "changed_texts": group["changed_texts"],
                    "review_reason": group["review_reason"],
                })

    
    review_priority_summary = summarize_review_priorities(
        evidence_records
    )

    report = {
        "report_type": "preliminary_regulatory_impact_evidence",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        
        "review_priority_summary": review_priority_summary,

        "evidence_records": evidence_records,
        "manual_review_groups": manual_review_groups,
        "limitations": [
            "Company policy is fictional test data.",
            "Evidence records are automatically generated.",
            "Source validation checks completeness, not authenticity.",
            "Similarity scores do not establish legal impact.",
            "Low-match groups require manual review.",
            "Rule pairs without evidence are not necessarily unaffected.",
            "Human legal and policy review is required.",
        ],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2, ensure_ascii=False)

    print("Impact evidence report generated successfully!")
    print("Saved to:", output_path)
    print("Evidence records:", len(evidence_records))
    print("Manual review groups:", len(manual_review_groups))
    print("Rule pairs without evidence:", summary["rule_pairs_without_evidence"])


if __name__ == "__main__":
    main()
