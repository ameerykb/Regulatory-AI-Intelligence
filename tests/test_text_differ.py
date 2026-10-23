"""
Unit Tests for Regulatory Text Difference Engine
=================================================

Tests text normalization and word-level change detection.

Run:
    python -m pytest tests/test_text_differ.py -v
"""

import pytest

from app.change_engine.text_differ import (
    normalize_comparison_text,
    compare_regulatory_text,
    remove_gazette_page_headers,
    remove_leading_rule_number,
    prepare_regulatory_text,
    normalize_punctuation_spacing,
)


def test_normalize_whitespace():
    """Extra spaces and line breaks should be normalized."""
    result = normalize_comparison_text(
        "The  organization\nmust   notify users."
    )

    assert result == "The organization must notify users."


def test_normalize_invalid_type():
    """Non-string input should raise TypeError."""
    with pytest.raises(TypeError):
        normalize_comparison_text(123)


def test_normalize_empty_text():
    """Whitespace-only text should raise ValueError."""
    with pytest.raises(ValueError):
        normalize_comparison_text("   ")


def test_unchanged_text():
    """Identical text should produce an unchanged result."""
    result = compare_regulatory_text(
        "Organizations must protect personal data.",
        "Organizations must protect personal data.",
    )

    assert result["status"] == "unchanged"
    assert result["similarity"] == 1.0
    assert result["review_required"] is False


def test_replaced_text():
    """A changed word should be detected as a replacement."""
    result = compare_regulatory_text(
        "Notify users within 72 hours.",
        "Notify users within 24 hours.",
    )

    changes = [
        operation
        for operation in result["operations"]
        if operation["operation"] != "equal"
    ]

    assert result["status"] == "modified"
    assert len(changes) == 1
    assert changes[0]["operation"] == "replace"
    assert changes[0]["draft_text"] == "72"
    assert changes[0]["final_text"] == "24"


def test_inserted_text():
    """Newly inserted words should be identified."""
    result = compare_regulatory_text(
        "Organizations must notify users.",
        "Organizations must immediately notify users.",
    )

    changes = [
        operation
        for operation in result["operations"]
        if operation["operation"] != "equal"
    ]

    assert len(changes) == 1
    assert changes[0]["operation"] == "insert"
    assert changes[0]["final_text"] == "immediately"


def test_deleted_text():
    """Removed words should be identified."""
    result = compare_regulatory_text(
        "Organizations must immediately notify users.",
        "Organizations must notify users.",
    )

    changes = [
        operation
        for operation in result["operations"]
        if operation["operation"] != "equal"
    ]

    assert len(changes) == 1
    assert changes[0]["operation"] == "delete"
    assert changes[0]["draft_text"] == "immediately"


def test_whitespace_only_difference():
    """Formatting-only whitespace changes should be ignored."""
    result = compare_regulatory_text(
        "Organizations   must\nnotify users.",
        "Organizations must notify users.",
    )

    assert result["status"] == "unchanged"
    assert result["similarity"] == 1.0


def test_compare_empty_text():
    """Empty regulatory text should be rejected."""
    with pytest.raises(ValueError):
        compare_regulatory_text(
            "",
            "Organizations must notify users.",
        )


def test_compare_invalid_type():
    """Non-string regulatory text should be rejected."""
    with pytest.raises(TypeError):
        compare_regulatory_text(
            None,
            "Organizations must notify users.",
        )

def test_remove_gazette_header():
    """Remove a standalone Gazette header without losing text."""
    header = (
        "\u092d\u093e\u0930\u0924 \u0915\u093e "
        "\u0930\u093e\u093f\u092a\u0924\u094d\u0930 : "
        "\u0905\u0938\u093e\u0927\u093e\u0930\u0923 35"
    )

    original = (
        "The Board shall process requests.\n"
        + header
        + "\nThe Data Principal may respond."
    )

    result = remove_gazette_page_headers(original)

    assert header not in result
    assert "The Board shall process requests." in result
    assert "The Data Principal may respond." in result


def test_preserve_non_header_hindi_text():
    """Ordinary Hindi text must not be removed."""
    original = "\u092d\u093e\u0930\u0924 \u0915\u093e \u0915\u093e\u0928\u0942\u0928"

    assert remove_gazette_page_headers(original) == original


def test_remove_expected_rule_number():
    """Remove only the expected leading rule number."""
    result = remove_leading_rule_number(
        "13. Rights of Data Principals.",
        13,
    )

    assert result == "Rights of Data Principals."


def test_preserve_other_rule_numbers():
    """A different leading rule number must be preserved."""
    result = remove_leading_rule_number(
        "14. Rights of Data Principals.",
        13,
    )

    assert result == "14. Rights of Data Principals."


def test_prepare_regulatory_text():
    """Preparation should remove headers and rule numbering."""
    header = (
        "\u092d\u093e\u0930\u0924 \u0915\u093e "
        "\u0930\u093e\u093f\u092a\u0924\u094d\u0930 : "
        "\u0905\u0938\u093e\u0927\u093e\u0930\u0923 35"
    )

    original = (
        "13. The Board shall\n"
        + header
        + "\nrespond within 90 days."
    )

    result = prepare_regulatory_text(original, 13)

    assert result == "The Board shall respond within 90 days."


def test_prepare_rejects_invalid_rule_number():
    """Invalid rule numbers must be rejected."""
    with pytest.raises(ValueError):
        prepare_regulatory_text(
            "13. Rights of Data Principals.",
            0,
        )
def test_normalize_em_dash_spacing():
    """Remove formatting-only spacing before an em dash."""
    result = normalize_punctuation_spacing(
        "Rights of Data Principals. —"
    )

    assert result == "Rights of Data Principals.—"


def test_preserve_meaningful_punctuation():
    """Preserve punctuation characters in regulatory text."""
    original = "Notify users within 30 days; otherwise, explain."

    result = normalize_punctuation_spacing(original)

    assert result == original


def test_preserve_regular_em_dash_spacing():
    """Do not change em dashes outside the supported pattern."""
    original = "The organization — where applicable — must notify."

    result = normalize_punctuation_spacing(original)

    assert result == original


def test_prepare_ignores_em_dash_spacing():
    """Formatting differences should not create false changes."""
    draft = prepare_regulatory_text(
        "13. Rights of Data Principals.—",
        13,
    )

    final = prepare_regulatory_text(
        "14. Rights of Data Principals. —",
        14,
    )

    comparison = compare_regulatory_text(draft, final)

    assert comparison["status"] == "unchanged"
    assert comparison["similarity"] == 1.0
    assert comparison["review_required"] is False


def test_normalize_punctuation_rejects_empty_text():
    """Empty text must be rejected."""
    with pytest.raises(ValueError):
        normalize_punctuation_spacing("   ")