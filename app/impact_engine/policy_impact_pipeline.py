
"""Preliminary regulatory-to-policy impact matching for saved comparisons.

Run from the project root:
    python -m app.impact_engine.policy_impact_pipeline COMPARISON_ID

Semantic similarity is a retrieval aid, not a legal compliance determination.
"""

import argparse
import json
from pathlib import Path

from app.impact_engine.policy_loader import (
    load_company_policy,
    extract_policy_sections,
)
from app.impact_engine.semantic_matcher import (
    match_regulation_to_policies,
)

BASE_DIR = Path(__file__).resolve().parents[2]


def build_policy_impact_report(comparison_id: str, top_k: int = 3) -> dict:
    if (
        len(comparison_id) != 32
        or any(c not in "0123456789abcdef" for c in comparison_id)
    ):
        raise ValueError(
            "comparison_id must be a 32-character lowercase hex ID"
        )

    comparison_path = (
        BASE_DIR / "data" / "comparisons"
        / f"{comparison_id}_changes.json"
    )

    updated_path = (
        BASE_DIR / "data" / "parsed"
        / f"{comparison_id}_updated.json"
    )

    if not comparison_path.is_file() or not updated_path.is_file():
        raise FileNotFoundError(
            "Saved comparison or updated parsed rules not found "
            "for this comparison ID"
        )

    change_report = json.loads(
        comparison_path.read_text(encoding="utf-8")
    )

    updated = json.loads(
        updated_path.read_text(encoding="utf-8")
    )

    rules = {
        rule["rule_number"]: rule
        for rule in updated["sections"]
    }

    policy_path = (
        BASE_DIR / "data" / "company_policies"
        / "privacy_policy.txt"
    )

    policies = extract_policy_sections(
        load_company_policy(str(policy_path))
    )

    if not policies:
        raise ValueError(
            "No numbered company policy sections found"
        )

    findings = []

    for change in change_report.get("analyzed_rules", []):
        differences = change.get("changes", [])

        if not differences:
            continue

        rule_number = change["final_rule_number"]
        rule = rules.get(rule_number)

        if not rule:
            raise ValueError(
                f"Updated rule {rule_number} is missing from parsed rules"
            )

        # Use the full regulatory rule as semantic context.
        context = f"{rule['title']}. {rule['text']}"

        matches = match_regulation_to_policies(
            context,
            policies,
        )[:top_k]

        findings.append({
            "draft_rule_number": change["draft_rule_number"],
            "final_rule_number": rule_number,
            "regulatory_title": rule["title"],
            "regulatory_context": context,
            "detected_changes": differences,
            "potentially_affected_policies": [
                {
                    "policy_section": match["policy_section"],
                    "similarity_score": match["similarity_score"],
                    "policy_text": policies[match["policy_section"]],
                    "match_method": (
                        "sentence_transformers_semantic_similarity"
                    ),
                }
                for match in matches
            ],
            "assessment_status": "preliminary",
            "requires_human_review": True,
            "impact_level": "not_assessed",
            "note": (
                "Semantic matches are candidates, not confirmed "
                "policy violations or legal conclusions."
            ),
        })

    report = {
        "comparison_id": comparison_id,
        "policy_sections_checked": len(policies),
        "modified_rules_evaluated": len(findings),
        "findings": findings,
        "review_required": True,
    }

    output = (
        BASE_DIR / "data" / "comparisons"
        / f"{comparison_id}_policy_impact.json"
    )

    output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Match saved regulatory changes to company policies"
    )

    parser.add_argument("comparison_id")
    parser.add_argument("--top-k", type=int, default=3)

    args = parser.parse_args()

    if not 1 <= args.top_k <= 8:
        parser.error("--top-k must be between 1 and 8")

    result = build_policy_impact_report(
        args.comparison_id,
        args.top_k,
    )

    print(json.dumps({
        "comparison_id": result["comparison_id"],
        "policy_sections_checked": result["policy_sections_checked"],
        "modified_rules_evaluated": result["modified_rules_evaluated"],
        "matches": [
            {
                "rule": finding["final_rule_number"],
                "title": finding["regulatory_title"],
                "policies": [
                    {
                        "section": policy["policy_section"],
                        "score": policy["similarity_score"],
                    }
                    for policy in finding[
                        "potentially_affected_policies"
                    ]
                ],
            }
            for finding in result["findings"]
        ],
    }, indent=2))
