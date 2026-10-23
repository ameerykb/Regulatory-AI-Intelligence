
import json
from datetime import datetime, timezone
from pathlib import Path

from app.impact_engine.policy_loader import (
    load_company_policy,
    extract_policy_sections,
)
from app.impact_engine.semantic_matcher import (
    match_change_groups_to_policies,
    summarize_policy_impact,
)


def main():
    source_path = Path(
        "data/reports/dpdp_2025_evidence_report.json"
    )

    output_path = Path(
        "data/reports/dpdp_2025_policy_impact_report.json"
    )

    with source_path.open("r", encoding="utf-8") as file:
        source_report = json.load(file)

    changes = source_report["changes"]

    policy_sections = extract_policy_sections(
        load_company_policy()
    )

    summary = summarize_policy_impact(
        changes,
        policy_sections,
    )

    rule_results = []

    for change in changes:
        groups = match_change_groups_to_policies(
            change,
            policy_sections,
        )

        rule_results.append({
            "draft_rule_number": change["draft_rule_number"],
            "final_rule_number": change["final_rule_number"],
            "change_groups": groups,
        })

    report = {
        "report_type": "preliminary_policy_impact_analysis",
        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "policy_source": "data/company_policies/privacy_policy.txt",
        "summary": summary,
        "rule_results": rule_results,
        "limitations": [
            "Company policy is fictional test data.",
            "Similarity scores do not establish legal impact.",
            "Similarity thresholds are preliminary and unvalidated.",
            "No detected wording group does not prove no regulatory change.",
            "Only aligned regulatory rule pairs are included.",
            "Human legal and policy review is required.",
        ],
    }

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            report,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print("Policy impact report generated successfully!")
    print("Saved to:", output_path)
    print("Aligned rule pairs:", summary["aligned_rule_pairs"])
    print("Total change groups:", summary["total_change_groups"])
    print(
        "Groups requiring manual review:",
        summary["groups_requiring_manual_review"],
    )


if __name__ == "__main__":
    main()
