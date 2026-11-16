"""Conservative preliminary regulatory impact classification."""


def classify_preliminary_impact(
    detected_changes: list[dict],
    policy_matches: list[dict],
) -> dict:
    """
    Produce a preliminary impact assessment.

    Policy similarity and change counts alone cannot establish
    regulatory impact severity. Human review remains mandatory.
    """
    if not detected_changes:
        reason = (
            "No detected regulatory changes were supplied. "
            "Impact severity cannot be assessed."
        )
    elif not policy_matches:
        reason = (
            "Regulatory changes were detected, but no company policy "
            "met the preliminary relevance threshold. "
            "Manual review is required."
        )
    else:
        reason = (
            "Potentially relevant company policies were identified. "
            "The significance of the regulatory changes and their "
            "operational implications require further assessment."
        )

    return {
        "impact_level": "not_assessed",
        "impact_reason": reason,
        "assessment_status": "preliminary",
        "requires_human_review": True,
    }
