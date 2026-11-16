from app.impact_engine.phase4_impact import (
    filter_relevant_candidates,
)


def test_weak_policy_matches_are_rejected():
    candidates = [
        {
            "policy_section": "Consent Management",
            "ranking_score": 0.1818,
        },
        {
            "policy_section": "Data Retention",
            "ranking_score": 0.22,
        },
    ]

    result = filter_relevant_candidates(candidates)

    assert result == []


def test_relevant_policy_matches_are_retained():
    candidates = [
        {
            "policy_section": "Breach Notification",
            "ranking_score": 0.72,
        },
        {
            "policy_section": "Security Controls",
            "ranking_score": 0.48,
        },
        {
            "policy_section": "Consent Management",
            "ranking_score": 0.18,
        },
    ]

    result = filter_relevant_candidates(candidates)

    assert len(result) == 2
    assert result[0]["policy_section"] == "Breach Notification"
    assert result[1]["policy_section"] == "Security Controls"


def test_threshold_boundary():
    candidates = [
        {"policy_section": "Policy A", "ranking_score": 0.35},
        {"policy_section": "Policy B", "ranking_score": 0.3499},
    ]

    result = filter_relevant_candidates(candidates)

    assert len(result) == 1
    assert result[0]["policy_section"] == "Policy A"


def test_top_k_limit():
    candidates = [
        {"policy_section": "A", "ranking_score": 0.80},
        {"policy_section": "B", "ranking_score": 0.70},
        {"policy_section": "C", "ranking_score": 0.60},
    ]

    result = filter_relevant_candidates(candidates, top_k=2)

    assert len(result) == 2
    assert result[0]["policy_section"] == "A"
    assert result[1]["policy_section"] == "B"