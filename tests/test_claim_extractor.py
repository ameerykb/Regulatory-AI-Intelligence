"""Automated tests for regulatory claim extraction."""

import pytest

from app.rag_engine.claim_extractor import extract_cited_claims


def test_single_claim():
    answer = "A Data Fiduciary must notify affected individuals. [Source 1]"

    claims = extract_cited_claims(answer)

    assert len(claims) == 1
    assert claims[0]["claim"] == (
        "A Data Fiduciary must notify affected individuals."
    )
    assert claims[0]["source_numbers"] == [1]


def test_multiple_claims():
    answer = """
    Breach notification is required. [Source 1]
    Security safeguards are required. [Source 2]
    """

    claims = extract_cited_claims(answer)

    assert len(claims) == 2
    assert claims[0]["source_numbers"] == [1]
    assert claims[1]["source_numbers"] == [2]


def test_multiple_citations():
    answer = "Detailed information is required. [Source 1] [Source 2]"

    claims = extract_cited_claims(answer)

    assert len(claims) == 1
    assert claims[0]["source_numbers"] == [1, 2]


def test_duplicate_citations():
    answer = "Notification is required. [Source 2] [Source 2] [Source 1]"

    claims = extract_cited_claims(answer)

    assert claims[0]["source_numbers"] == [1, 2]


def test_answer_without_citations():
    answer = "This statement has no regulatory citation."

    claims = extract_cited_claims(answer)

    assert len(claims) == 1
    assert claims[0]["claim"] == answer
    assert claims[0]["source_numbers"] == []


def test_empty_answer():
    assert extract_cited_claims("") == []


def test_invalid_input():
    with pytest.raises(TypeError):
        extract_cited_claims(None)