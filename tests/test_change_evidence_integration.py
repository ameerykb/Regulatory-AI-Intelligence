
"""Tests for exact regulatory change evidence integration."""

from unittest.mock import patch

from app.rag_engine.change_evidence import (
    retrieve_all_change_evidence,
)


def test_retrieve_all_change_evidence():
    """Each change should receive its own evidence record."""

    changes = [
        {
            "draft_rule_number": 3,
            "final_rule_number": 3,
            "changes": [],
            "review_required": True,
        },
        {
            "draft_rule_number": 7,
            "final_rule_number": 7,
            "changes": [],
            "review_required": True,
        },
    ]

    def fake_retrieve(change, database_path):
        return {
            "change": change,
            "draft_evidence": {
                "rule_number": change["draft_rule_number"],
            },
            "final_evidence": {
                "rule_number": change["final_rule_number"],
            },
            "review_status": "requires_human_review",
        }

    with patch(
        "app.rag_engine.change_evidence.retrieve_exact_change_evidence",
        side_effect=fake_retrieve,
    ) as mock_retriever:

        results = retrieve_all_change_evidence(
            changes=changes,
            database_path="test_vector_db",
        )

    assert len(results) == 2

    assert results[0]["draft_evidence"]["rule_number"] == 3
    assert results[0]["final_evidence"]["rule_number"] == 3

    assert results[1]["draft_evidence"]["rule_number"] == 7
    assert results[1]["final_evidence"]["rule_number"] == 7

    assert all(
        result["review_status"] == "requires_human_review"
        for result in results
    )

    assert mock_retriever.call_count == 2

