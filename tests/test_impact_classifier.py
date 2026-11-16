from app.impact_engine.impact_classifier import classify_preliminary_impact


def test_no_policy_match_remains_unassessed():
    result = classify_preliminary_impact(
        detected_changes=[{
            "operation": "replace",
            "draft_text": "Old requirement",
            "final_text": "New requirement",
        }],
        policy_matches=[],
    )

    assert result["impact_level"] == "not_assessed"
    assert result["requires_human_review"] is True


def test_policy_similarity_alone_does_not_determine_severity():
    result = classify_preliminary_impact(
        detected_changes=[{
            "operation": "replace",
            "draft_text": "Previous wording",
            "final_text": "Updated wording",
        }],
        policy_matches=[{
            "policy_section": "Security Safeguards",
            "ranking_score": 0.95,
        }],
    )

    assert result["impact_level"] == "not_assessed"
    assert result["requires_human_review"] is True


def test_empty_changes_are_not_classified_as_low_impact():
    result = classify_preliminary_impact(
        detected_changes=[],
        policy_matches=[],
    )

    assert result["impact_level"] == "not_assessed"
    assert result["requires_human_review"] is True
