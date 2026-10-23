"""Automated tests for the Regulatory AI Intelligence System."""

import pytest

from app.rag_engine.structured_claim_extractor import (
    extract_structured_claims,
)
from app.rag_engine.langgraph_workflow import (
    run_regulatory_workflow,
)


# --------------------------------------------------
# TEST 1: Citation extraction
# --------------------------------------------------

def test_citation_extraction():
    answer = """
    A Data Fiduciary must notify affected individuals [Source 1].
    """

    claims = extract_structured_claims(answer)

    assert len(claims) == 1
    assert claims[0]["source_numbers"] == [1]


# --------------------------------------------------
# TEST 2: Detect uncited claims
# --------------------------------------------------

def test_uncited_claim_detection():
    answer = """
    A Data Fiduciary must notify affected individuals.
    """

    claims = extract_structured_claims(answer)

    assert len(claims) == 1
    assert claims[0]["source_numbers"] == []


# --------------------------------------------------
# TEST 3: Nested regulatory requirements
# --------------------------------------------------

def test_nested_claim_extraction():
    answer = """
    A Data Fiduciary must:

    1. Notify the affected Data Principal:
       - Provide a description of the breach [Source 1].
       - Explain the likely consequences [Source 1].
    """

    claims = extract_structured_claims(answer)

    assert len(claims) == 2
    assert all(claim["source_numbers"] == [1] for claim in claims)


# --------------------------------------------------
# TEST 4: LangGraph review routing
# --------------------------------------------------

def test_langgraph_review_routing(monkeypatch):
    import app.rag_engine.langgraph_workflow as workflow

    def mock_rag_pipeline(question, document_version, top_k):
        return {
            "question": question,
            "answer": "A regulatory requirement [Source 1].",
            "sources": [],
            "status": "generated_requires_review",
            "claim_verification": {
                "total_claims": 1,
                "total_cited_claims": 1,
                "total_uncited_claims": 0,
                "claims": [],
            },
        }

    monkeypatch.setattr(
        workflow,
        "answer_regulatory_question",
        mock_rag_pipeline,
    )

    result = run_regulatory_workflow(
        question="What are the requirements?"
    )

    assert result["status"] == "generated_requires_review"

    assert (
        result["workflow"]["review_status"]
        == "human_review_required"
    )

    assert "assess_verification" in (
        result["workflow"]["execution_path"]
    )


# --------------------------------------------------
# TEST 5: Missing evidence routing
# --------------------------------------------------

def test_missing_evidence_routing(monkeypatch):
    import app.rag_engine.langgraph_workflow as workflow

    def mock_rag_pipeline(question, document_version, top_k):
        return {
            "question": question,
            "answer": "No regulatory evidence was retrieved.",
            "sources": [],
            "status": "insufficient_evidence",
        }

    monkeypatch.setattr(
        workflow,
        "answer_regulatory_question",
        mock_rag_pipeline,
    )

    result = run_regulatory_workflow(
        question="What is the requirement?"
    )

    assert (
        result["workflow"]["review_status"]
        == "blocked_or_insufficient"
    )

    assert "handle_blocked_result" in (
        result["workflow"]["execution_path"]
    )


# --------------------------------------------------
# TEST 6: Invalid question
# --------------------------------------------------

def test_invalid_question():
    with pytest.raises(ValueError):
        run_regulatory_workflow(question="")


# --------------------------------------------------
# TEST 7: Invalid document version
# --------------------------------------------------

def test_invalid_document_version():
    with pytest.raises(ValueError):
        run_regulatory_workflow(
            question="What are the rules?",
            document_version="invalid_version",
        )
        