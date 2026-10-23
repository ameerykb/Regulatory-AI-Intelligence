


def create_impact_evidence(
    change: dict,
    group: dict,
    policy_match: dict,
    policy_sections: dict,
) -> dict:
    """Create preliminary evidence with regulatory source validation."""

    policy_title = policy_match["policy_section"]

    policy_text = policy_sections.get(
        policy_title,
        ""
    )

    evidence = {
        "draft_rule_number": change["draft_rule_number"],
        "final_rule_number": change["final_rule_number"],
        "regulatory_sources": {
            "draft": change.get("draft_source", {}),
            "final": change.get("final_source", {}),
        },
        "group_number": group["group_number"],
        "changed_texts": group["changed_texts"],
        "regulatory_context": group["regulatory_context"],
        "policy_section": policy_title,
        "policy_text": policy_text,
        "similarity_score": policy_match["similarity_score"],
        "similarity_label": policy_match["similarity_label"],
        "evidence_status": "automatically_generated",
        "assessment_status": "preliminary",
        "requires_human_review": True,
    }

    
    evidence["source_validation"] = validate_regulatory_sources(
        evidence
    )

    evidence["policy_validation"] = validate_policy_evidence(
        evidence
    )

    return evidence





def validate_regulatory_sources(evidence: dict) -> dict:
    """Check whether regulatory source metadata is complete."""

    sources = evidence.get("regulatory_sources", {})

    required_fields = [
        "rule_id",
        "source_file",
        "text",
    ]

    validation = {}

    for source_type in ["draft", "final"]:
        source = sources.get(source_type, {})

        missing_fields = [
            field
            for field in required_fields
            if not isinstance(source.get(field), str)
            or not source.get(field).strip()
        ]

        validation[source_type] = {
            "valid": len(missing_fields) == 0,
            "missing_fields": missing_fields,
        }

    validation["all_sources_valid"] = (
        validation["draft"]["valid"]
        and validation["final"]["valid"]
    )

    return validation


def validate_policy_evidence(evidence: dict) -> dict:
    """Check whether matched company policy evidence is complete."""

    policy_section = evidence.get("policy_section", "")
    policy_text = evidence.get("policy_text", "")

    section_valid = (
        isinstance(policy_section, str)
        and bool(policy_section.strip())
    )

    text_valid = (
        isinstance(policy_text, str)
        and bool(policy_text.strip())
    )

    return {
        "policy_section_valid": section_valid,
        "policy_text_valid": text_valid,
        "all_policy_evidence_valid": (
            section_valid and text_valid
        ),
    }



def generate_rule_evidence(
    change: dict,
    rule_result: dict,
    policy_sections: dict,
) -> list[dict]:
    """Generate preliminary evidence for a regulatory rule pair."""

    evidence_records = []

    for group in rule_result.get("change_groups", []):
        for match in group.get("filtered_policy_matches", []):
            evidence = create_impact_evidence(
                change,
                group,
                match,
                policy_sections,
            )

            
            evidence["review_recommendation"] = (
                generate_review_recommendation(evidence)
            )

            evidence_records.append(evidence)


    return evidence_records



def summarize_impact_evidence(
    regulatory_changes: list[dict],
    rule_results: list[dict],
    policy_sections: dict,
) -> dict:
    """Summarize preliminary evidence across aligned regulatory rules."""

    if len(regulatory_changes) != len(rule_results):
        raise ValueError("Regulatory and impact report counts do not match.")

    summary = {
        "aligned_rule_pairs": len(regulatory_changes),
        "total_evidence_records": 0,
        "low_match_groups_requiring_review": 0,
        "rule_pairs_without_evidence": 0,
    }

    for change, rule_result in zip(regulatory_changes, rule_results):
        if (
            str(change["draft_rule_number"]) != str(rule_result["draft_rule_number"])
            or str(change["final_rule_number"]) != str(rule_result["final_rule_number"])
        ):
            raise ValueError("Regulatory rule pair mismatch.")

        records = generate_rule_evidence(
            change,
            rule_result,
            policy_sections,
        )

        summary["total_evidence_records"] += len(records)

        if not records:
            summary["rule_pairs_without_evidence"] += 1

        summary["low_match_groups_requiring_review"] += sum(
            1
            for group in rule_result["change_groups"]
            if not group["filtered_policy_matches"]
        )

    return summary



def generate_review_recommendation(evidence: dict) -> dict:
    """Generate a preliminary human-review recommendation."""

    policy_section = evidence.get("policy_section", "")
    similarity_label = evidence.get("similarity_label", "")

    if similarity_label == "stronger_semantic_match":
        priority = "review_first"
        reason = (
            "The regulatory change and company policy show a "
            "relatively stronger semantic relationship."
        )

    elif similarity_label == "moderate_semantic_match":
        priority = "standard_review"
        reason = (
            "The regulatory change and company policy show a "
            "moderate semantic relationship."
        )

    else:
        priority = "manual_assessment"
        reason = (
            "The relationship between the regulatory change "
            "and company policy requires manual assessment."
        )

    return {
        "policy_section": policy_section,
        "review_priority": priority,
        "recommendation": (
            "Compare the changed regulatory wording with "
            f"company policy section '{policy_section}'. "
            "Determine whether the policy requires clarification, "
            "revision, or no action. Record the supporting rationale."
        ),
        "reason": reason,
        "recommendation_status": "preliminary",
        "requires_human_approval": True,
    }



def summarize_review_priorities(evidence_records: list[dict]) -> dict:
    """Count preliminary recommendations by workflow review priority."""

    summary = {
        "total_recommendations": 0,
        "review_first": 0,
        "standard_review": 0,
        "manual_assessment": 0,
        "missing_recommendations": 0,
    }

    for evidence in evidence_records:
        recommendation = evidence.get("review_recommendation")

        if not isinstance(recommendation, dict):
            summary["missing_recommendations"] += 1
            continue

        summary["total_recommendations"] += 1

        priority = recommendation.get("review_priority")

        if priority in (
            "review_first",
            "standard_review",
            "manual_assessment",
        ):
            summary[priority] += 1
        else:
            summary["manual_assessment"] += 1

    return summary




