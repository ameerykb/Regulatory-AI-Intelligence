
"""Tests for the regulatory change evidence connector."""

from unittest.mock import call, patch

from app.rag_engine.change_evidence import retrieve_change_evidence


def test_retrieve_change_evidence():
    """Retrieve separate draft and final evidence records."""

    draft_evidence = [
        {
            "rule_id": "dpdp_draft_2025_rule_7",
            "rule_number": 7,
            "title": "Intimation of personal data breach",
            "document_version": "draft_2025",
            "source_file": "dpdp_draft_2025_sections.json",
            "text": "Draft breach notification requirements.",
            "distance": 0.45,
        }
    ]

    final_evidence = [
        {
            "rule_id": "dpdp_final_2025_rule_7",
            "rule_number": 7,
            "title": "Intimation of personal data breach",
            "document_version": "final_2025",
            "source_file": "dpdp_final_2025_sections.json",
            "text": "Final breach notification requirements.",
            "distance": 0.33,
        }
    ]

    with patch(
        "app.rag_engine.change_evidence.retrieve_regulatory_evidence",
        side_effect=[draft_evidence, final_evidence],
    ) as mock_retriever:

        result = retrieve_change_evidence(
            query="What changed in breach notification requirements?",
            top_k=1,
            database_path="data/test_vector_db",
        )

    assert result["query"] == (
        "What changed in breach notification requirements?"
    )

    assert result["draft_evidence"] == draft_evidence
    assert result["final_evidence"] == final_evidence
    assert result["review_status"] == "requires_human_review"

    assert mock_retriever.call_count == 2

    mock_retriever.assert_has_calls(
        [
            call(
                query="What changed in breach notification requirements?",
                document_version="draft_2025",
                top_k=1,
                database_path="data/test_vector_db",
            ),
            call(
                query="What changed in breach notification requirements?",
                document_version="final_2025",
                top_k=1,
                database_path="data/test_vector_db",
            ),
        ]
    )
