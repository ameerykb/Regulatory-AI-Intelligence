"""Tests for the complete claim-verification workflow."""

from app.rag_engine.claim_verification_pipeline import verify_answer_claims


SOURCES = [
    {
        "source_number": 1,
        "rule_number": "7",
        "document_version": "final_2025",
        "source_file": "dpdp_rules_2025.pdf",
        "text": (
            "The Data Fiduciary shall notify affected "
            "Data Principals without delay."
        ),
    },
    {
        "source_number": 2,
        "rule_number": "7",
        "document_version": "final_2025",
        "source_file": "dpdp_rules_2025.pdf",
        "text": "Detailed information must be provided within 72 hours.",
    },
]


def test_supported_claim(monkeypatch):
    def fake_verifier(claim, evidence):
        assert "notify affected" in evidence

        return {
            "claim": claim,
            "verdict": "SUPPORTED",
            "quote_valid": True,
            "evidence_quote": "notify affected Data Principals",
        }

    monkeypatch.setattr(
        "app.rag_engine.claim_verification_pipeline.verify_individual_claim",
        fake_verifier,
    )

    result = verify_answer_claims(
        "Notification is required. [Source 1]",
        SOURCES,
    )

    assert result["total_cited_claims"] == 1
    assert result["claims"][0]["verification"]["verdict"] == "SUPPORTED"


def test_multiple_claims(monkeypatch):
    def fake_verifier(claim, evidence):
        return {
            "claim": claim,
            "verdict": "SUPPORTED",
            "quote_valid": True,
            "evidence_quote": "",
        }

    monkeypatch.setattr(
        "app.rag_engine.claim_verification_pipeline.verify_individual_claim",
        fake_verifier,
    )

    answer = """
    Notification is required. [Source 1]
    Detailed information is required. [Source 2]
    """

    result = verify_answer_claims(answer, SOURCES)

    assert result["total_cited_claims"] == 2
    assert len(result["claims"]) == 2


def test_missing_source_requires_review(monkeypatch):
    def fail_if_called(claim, evidence):
        raise AssertionError("LLM must not run for missing sources.")

    monkeypatch.setattr(
        "app.rag_engine.claim_verification_pipeline.verify_individual_claim",
        fail_if_called,
    )

    result = verify_answer_claims(
        "Free laptops are required. [Source 99]",
        SOURCES,
    )

    verification = result["claims"][0]["verification"]

    assert verification["verdict"] == "REVIEW_REQUIRED"
    assert verification["quote_valid"] is False
    assert result["claims"][0]["missing_sources"] == [99]


def test_partially_missing_sources_requires_review(monkeypatch):
    def fail_if_called(claim, evidence):
        raise AssertionError("LLM must not run with missing citations.")

    monkeypatch.setattr(
        "app.rag_engine.claim_verification_pipeline.verify_individual_claim",
        fail_if_called,
    )

    result = verify_answer_claims(
        "Notification and compensation are required. [Source 1] [Source 99]",
        SOURCES,
    )

    assert result["claims"][0]["verification"]["verdict"] == "REVIEW_REQUIRED"


def test_only_cited_evidence_is_used(monkeypatch):
    def fake_verifier(claim, evidence):
        assert "notify affected" in evidence
        assert "72 hours" not in evidence

        return {
            "claim": claim,
            "verdict": "SUPPORTED",
            "quote_valid": True,
            "evidence_quote": "",
        }

    monkeypatch.setattr(
        "app.rag_engine.claim_verification_pipeline.verify_individual_claim",
        fake_verifier,
    )

    result = verify_answer_claims(
        "Notification is required. [Source 1]",
        SOURCES,
    )

    assert result["total_cited_claims"] == 1


def test_empty_answer():
    result = verify_answer_claims("", SOURCES)

    assert result["total_cited_claims"] == 0
    assert result["claims"] == []


def test_workflow_status(monkeypatch):
    def fake_verifier(claim, evidence):
        return {
            "claim": claim,
            "verdict": "SUPPORTED",
            "quote_valid": True,
            "evidence_quote": "",
        }

    monkeypatch.setattr(
        "app.rag_engine.claim_verification_pipeline.verify_individual_claim",
        fake_verifier,
    )

    result = verify_answer_claims(
        "Notification is required. [Source 1]",
        SOURCES,
    )

    assert result["status"] == "completed_requires_human_review"