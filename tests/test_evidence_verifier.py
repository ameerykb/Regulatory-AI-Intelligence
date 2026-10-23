
from unittest.mock import patch

import pytest

from app.rag_engine.evidence_verifier import verify_claim_against_evidence


@pytest.mark.parametrize(
    "model_response, expected",
    [
        ("SUPPORTED", "SUPPORTED"),
        ("UNSUPPORTED", "UNSUPPORTED"),
        ("INSUFFICIENT_EVIDENCE", "INSUFFICIENT_EVIDENCE"),
    ],
)
def test_valid_verdicts(model_response, expected):
    with patch(
        "app.rag_engine.evidence_verifier.generate_chat_response",
        return_value=model_response,
    ):
        result = verify_claim_against_evidence(
            claim="A regulatory claim",
            evidence="A regulatory evidence passage",
        )

    assert result["verdict"] == expected


def test_unexpected_model_response():
    with patch(
        "app.rag_engine.evidence_verifier.generate_chat_response",
        return_value="I cannot determine the answer.",
    ):
        result = verify_claim_against_evidence(
            claim="A regulatory claim",
            evidence="A regulatory evidence passage",
        )

    assert result["verdict"] == "REVIEW_REQUIRED"


@pytest.mark.parametrize(
    "claim, evidence",
    [
        ("", "Valid evidence"),
        ("Valid claim", ""),
        ("   ", "Valid evidence"),
        ("Valid claim", "   "),
    ],
)
def test_empty_inputs(claim, evidence):
    with pytest.raises(ValueError):
        verify_claim_against_evidence(
            claim=claim,
            evidence=evidence,
        )
