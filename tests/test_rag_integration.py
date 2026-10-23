
from unittest.mock import patch

from app.rag_engine.rag_pipeline import answer_regulatory_question


def test_complete_rag_pipeline():
    """Test retrieval, generation, citations, and verification."""

    evidence = [{
        "rule_id": "rule_7",
        "rule_number": "7",
        "title": "Breach notification",
        "document_version": "final_2025",
        "source_file": "test_rule.txt",
        "text": (
            "A Data Fiduciary must notify affected "
            "individuals without delay after a breach."
        ),
        "distance": 0.20,
    }]

    with patch(
        "app.rag_engine.rag_pipeline.retrieve_regulatory_evidence",
        return_value=evidence,
    ):
        with patch(
            "app.rag_engine.rag_pipeline.generate_chat_response",
            return_value=(
                "Affected individuals must be notified "
                "without delay. [Source 1]"
            ),
        ):
            with patch(
                "app.rag_engine.rag_pipeline.verify_claim_against_evidence",
                return_value={
                    "verdict": "SUPPORTED",
                    "raw_response": "SUPPORTED",
                },
            ) as mock_verifier:
                result = answer_regulatory_question(
                    question="When must individuals be notified?",
                    document_version="final_2025",
                    top_k=1,
                )

    assert result["status"] == "generated_requires_review"
    assert len(result["sources"]) == 1
    assert result["sources"][0]["rule_number"] == "7"
    assert "[Source 1]" in result["answer"]
    assert result["verification"]["verdict"] == "SUPPORTED"

    mock_verifier.assert_called_once()

    print("RESULT: RAG INTEGRATION TEST PASSED")
