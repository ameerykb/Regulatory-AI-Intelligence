"""Tests for mapping regulatory claims to cited evidence."""

import pytest

from app.rag_engine.claim_evidence_mapper import map_claims_to_evidence


SOURCES = [
    {
        "source_number": 1,
        "rule_number": "7",
        "document_version": "final_2025",
        "source_file": "dpdp_rules_2025.pdf",
        "text": "A Data Fiduciary shall notify affected Data Principals.",
    },
    {
        "source_number": 2,
        "rule_number": "7",
        "document_version": "final_2025",
        "source_file": "dpdp_rules_2025.pdf",
        "text": "Detailed information must be provided within 72 hours.",
    },
]


def test_single_source_mapping():
    claims = [
        {
            "claim": "Notification is required.",
            "source_numbers": [1],
        }
    ]

    result = map_claims_to_evidence(claims, SOURCES)

    assert len(result) == 1
    assert len(result[0]["matched_sources"]) == 1
    assert result[0]["missing_sources"] == []
    assert result[0]["matched_sources"][0]["rule_number"] == "7"


def test_multiple_source_mapping():
    claims = [
        {
            "claim": "Detailed notification is required.",
            "source_numbers": [1, 2],
        }
    ]

    result = map_claims_to_evidence(claims, SOURCES)

    assert len(result[0]["matched_sources"]) == 2
    assert result[0]["missing_sources"] == []


def test_missing_source():
    claims = [
        {
            "claim": "Compensation is required.",
            "source_numbers": [3],
        }
    ]

    result = map_claims_to_evidence(claims, SOURCES)

    assert result[0]["matched_sources"] == []
    assert result[0]["missing_sources"] == [3]


def test_partially_missing_sources():
    claims = [
        {
            "claim": "Notification and compensation are required.",
            "source_numbers": [1, 99],
        }
    ]

    result = map_claims_to_evidence(claims, SOURCES)

    assert len(result[0]["matched_sources"]) == 1
    assert result[0]["missing_sources"] == [99]


def test_evidence_text_preserved():
    claims = [
        {
            "claim": "Notification is required.",
            "source_numbers": [1],
        }
    ]

    result = map_claims_to_evidence(claims, SOURCES)

    assert (
        result[0]["matched_sources"][0]["text"]
        == SOURCES[0]["text"]
    )


def test_empty_claims():
    assert map_claims_to_evidence([], SOURCES) == []


def test_invalid_claims_input():
    with pytest.raises(TypeError):
        map_claims_to_evidence(None, SOURCES)


def test_invalid_sources_input():
    with pytest.raises(TypeError):
        map_claims_to_evidence([], None)