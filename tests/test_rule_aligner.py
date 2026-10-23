"""
Unit Tests for the Rule Alignment Engine
========================================

Tests text normalization and regulatory rule validation.

Run:
    python -m pytest tests/test_rule_aligner.py -v
"""

import pytest

from app.change_engine.rule_aligner import (
    normalize_text,
    validate_rule,
    calculate_title_similarity,
    calculate_rule_similarity,
    find_rule_candidates,
)


def make_valid_rule() -> dict:
    """
    Create a sample regulatory rule for testing.

    Returns:
        A valid rule dictionary matching the parser's
        expected structure.
    """
    return {
        "section_id": "en_rule_10",
        "rule_number": 10,
        "title": "Verifiable consent",
        "text": "10. Verifiable consent shall be obtained.",
    }


def test_normalize_text():
    """Verify lowercase conversion and whitespace normalization."""
    result = normalize_text("  Personal   DATA\nProtection  ")

    assert result == "personal data protection"


def test_normalize_empty_text():
    """Verify that empty input produces an empty string."""
    assert normalize_text("   ") == ""


def test_normalize_invalid_input():
    """Verify that non-string input raises TypeError."""
    with pytest.raises(TypeError):
        normalize_text(None)


def test_validate_valid_rule():
    """Verify that a correctly structured rule is accepted."""
    validate_rule(make_valid_rule())


def test_validate_missing_field():
    """Verify that missing required fields are rejected."""
    rule = make_valid_rule()
    del rule["title"]

    with pytest.raises(ValueError, match="Missing required field"):
        validate_rule(rule)


def test_validate_invalid_rule_number():
    """Verify that invalid rule numbers are rejected."""
    rule = make_valid_rule()
    rule["rule_number"] = 0

    with pytest.raises(ValueError):
        validate_rule(rule)


def test_validate_boolean_rule_number():
    """Verify that True is not accepted as rule number 1."""
    rule = make_valid_rule()
    rule["rule_number"] = True

    with pytest.raises(ValueError):
        validate_rule(rule)


def test_validate_empty_title():
    """Verify that blank regulatory titles are rejected."""
    rule = make_valid_rule()
    rule["title"] = "   "

    with pytest.raises(ValueError):
        validate_rule(rule)


def test_validate_non_dictionary():
    """Verify that a non-dictionary rule is rejected."""
    with pytest.raises(TypeError):
        validate_rule("not a rule")

def test_title_similarity_identical():
    """
    Verify that identical titles receive a perfect score.
    """
    score = calculate_title_similarity(
        "Rights of Data Principals",
        "Rights of Data Principals",
    )

    assert score == 1.0


def test_title_similarity_case_and_whitespace():
    """
    Verify that case and repeated whitespace do not
    affect the similarity of equivalent titles.
    """
    score = calculate_title_similarity(
        "  RIGHTS   of Data Principals ",
        "rights of data principals",
    )

    assert score == 1.0


def test_title_similarity_different_titles():
    """
    Verify that unrelated titles receive a low score.
    """
    score = calculate_title_similarity(
        "Definitions",
        "Appeal to Appellate Tribunal",
    )

    assert 0.0 <= score < 0.5


def test_title_similarity_empty_title():
    """
    Verify that an empty title produces zero similarity.
    """
    score = calculate_title_similarity(
        "",
        "Rights of Data Principals",
    )

    assert score == 0.0


def test_title_similarity_invalid_input():
    """
    Verify that non-string input raises TypeError.
    """
    with pytest.raises(TypeError):
        calculate_title_similarity(
            None,
            "Rights of Data Principals",
        )

def test_title_similarity_trailing_punctuation():
    """
    Verify that trailing heading punctuation does not
    reduce similarity between equivalent rule titles.

    This handles formatting differences between draft
    and final regulatory documents.
    """
    score = calculate_title_similarity(
        "Rights of Data Principals",
        "Rights of Data Principals.",
    )

    assert score == 1.0

def test_find_rule_candidates_ranking():
    """
    Verify that the most similar rule ranks first,
    even when its rule number is different.
    """
    draft_rule = make_valid_rule()

    unrelated_rule = {
        "section_id": "en_rule_9",
        "rule_number": 9,
        "title": "Appeal to Tribunal",
        "text": "9. Appeals shall be submitted to the Tribunal.",
    }

    matching_rule = {
        "section_id": "en_rule_11",
        "rule_number": 11,
        "title": "Verifiable consent",
        "text": "10. Verifiable consent shall be obtained.",
    }

    candidates = find_rule_candidates(
        draft_rule,
        [unrelated_rule, matching_rule],
        top_k=2,
    )

    assert len(candidates) == 2
    assert candidates[0]["final_rule_number"] == 11
    assert (
        candidates[0]["combined_similarity"]
        > candidates[1]["combined_similarity"]
    )


def test_find_rule_candidates_top_k():
    """Verify that top_k limits the number of results."""
    candidates = find_rule_candidates(
        make_valid_rule(),
        [make_valid_rule(), make_valid_rule()],
        top_k=1,
    )

    assert len(candidates) == 1


def test_find_rule_candidates_empty_list():
    """Verify that an empty list returns no candidates."""
    candidates = find_rule_candidates(
        make_valid_rule(),
        [],
    )

    assert candidates == []


def test_find_rule_candidates_invalid_top_k():
    """Verify that top_k cannot be zero."""
    with pytest.raises(ValueError):
        find_rule_candidates(
            make_valid_rule(),
            [make_valid_rule()],
            top_k=0,
        )


def test_find_rule_candidates_boolean_top_k():
    """Verify that Boolean values are rejected."""
    with pytest.raises(TypeError):
        find_rule_candidates(
            make_valid_rule(),
            [make_valid_rule()],
            top_k=True,
        )