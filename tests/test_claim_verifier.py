"""Tests for claim-level regulatory evidence verification."""

import json

from app.rag_engine.claim_verifier import verify_individual_claim


EVIDENCE = (
    "On becoming aware of a personal data breach, "
    "the Data Fiduciary shall notify affected Data Principals."
)


def mock_llm(monkeypatch, verdict, quote):
    """Replace the real LLM with a predictable test response."""

    def fake_generate_chat_response(system_message, user_message):
        return json.dumps(
            {
                "verdict": verdict,
                "evidence_quote": quote,
            }
        )

    monkeypatch.setattr(
        "app.rag_engine.claim_verifier.generate_chat_response",
        fake_generate_chat_response,
    )


def test_supported_claim(monkeypatch):
    mock_llm(
        monkeypatch,
        "SUPPORTED",
        "the Data Fiduciary shall notify affected Data Principals.",
    )

    result = verify_individual_claim(
        "A Data Fiduciary must notify affected Data Principals.",
        EVIDENCE,
    )

    assert result["verdict"] == "SUPPORTED"
    assert result["quote_valid"] is True


def test_unsupported_claim(monkeypatch):
    mock_llm(
        monkeypatch,
        "UNSUPPORTED",
        "the Data Fiduciary shall notify affected Data Principals.",
    )

    result = verify_individual_claim(
        "A Data Fiduciary must never notify affected Data Principals.",
        EVIDENCE,
    )

    assert result["verdict"] == "UNSUPPORTED"
    assert result["quote_valid"] is True


def test_insufficient_evidence(monkeypatch):
    mock_llm(
        monkeypatch,
        "INSUFFICIENT_EVIDENCE",
        "",
    )

    result = verify_individual_claim(
        "A Data Fiduciary must pay one million rupees.",
        EVIDENCE,
    )

    assert result["verdict"] == "INSUFFICIENT_EVIDENCE"
    assert result["quote_valid"] is False


def test_fabricated_quote(monkeypatch):
    mock_llm(
        monkeypatch,
        "SUPPORTED",
        "The Data Fiduciary shall pay one million rupees.",
    )

    result = verify_individual_claim(
        "A Data Fiduciary must pay one million rupees.",
        EVIDENCE,
    )

    assert result["verdict"] == "REVIEW_REQUIRED"
    assert result["quote_valid"] is False


def test_empty_claim():
    try:
        verify_individual_claim("", EVIDENCE)
    except ValueError:
        pass
    else:
        raise AssertionError("Empty claims must raise ValueError.")


def test_missing_evidence():
    result = verify_individual_claim(
        "A Data Fiduciary must notify affected individuals.",
        "",
    )

    assert result["verdict"] == "INSUFFICIENT_EVIDENCE"


def test_invalid_json(monkeypatch):
    def fake_generate_chat_response(system_message, user_message):
        return "This is not valid JSON"

    monkeypatch.setattr(
        "app.rag_engine.claim_verifier.generate_chat_response",
        fake_generate_chat_response,
    )

    result = verify_individual_claim(
        "A Data Fiduciary must notify affected individuals.",
        EVIDENCE,
    )

    assert result["verdict"] == "REVIEW_REQUIRED"