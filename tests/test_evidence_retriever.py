"""Tests for regulatory evidence retrieval."""

from unittest.mock import patch

from app.rag_engine.evidence_retriever import (
    retrieve_regulatory_evidence,
)


def test_retrieve_regulatory_evidence():
    """Convert semantic search results into source evidence."""

    fake_results = [
        {
            "id": "dpdp_final_2025_rule_7",
            "text": "The Data Fiduciary shall notify affected individuals.",
            "distance": 0.329,
            "metadata": {
                "rule_number": 7,
                "title": "Intimation of personal data breach",
                "document_version": "final_2025",
                "source_file": "dpdp_final_2025_sections.json",
            },
        }
    ]

    with patch(
        "app.rag_engine.evidence_retriever.search_regulatory_rules",
        return_value=fake_results,
    ) as mock_search:

        evidence = retrieve_regulatory_evidence(
            query="What happens after a personal data breach?",
            document_version="final_2025",
            top_k=1,
        )

    assert len(evidence) == 1

    result = evidence[0]

    assert result["rule_id"] == "dpdp_final_2025_rule_7"
    assert result["rule_number"] == 7
    assert result["document_version"] == "final_2025"
    assert result["source_file"] == "dpdp_final_2025_sections.json"
    assert result["distance"] == 0.329
    assert "notify affected individuals" in result["text"]

    mock_search.assert_called_once_with(
        query="What happens after a personal data breach?",
        top_k=1,
        database_path="data/vector_db",
        document_version="final_2025",
    )