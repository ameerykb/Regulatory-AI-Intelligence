
"""
Automated Tests for the Regulatory Section Parser
=================================================

Project:
    AI Regulatory Change Impact Intelligence System

Purpose:
    Verify that regulatory rules are extracted accurately
    from structured PDF extraction data.

Run:
    python -m pytest tests/test_section_parser.py -v

Testing approach:
    Use small, artificial regulatory documents so tests
    do not depend on downloaded PDFs or external services.
"""

import json

import pytest

from app.document_engine.section_parser import (
    detect_rule_heading,
    extract_rule_title,
    load_extraction,
    parse_sections,
    save_sections,
)


def make_extraction(pages):
    """
    Build a small artificial PDF extraction result.

    Args:
        pages: List of (page_number, text) pairs.

    Returns:
        Dictionary matching the parser's expected input.
    """

    return {
        "filename": "sample_regulation.pdf",
        "sha256": "sample_hash",
        "pages": [
            {
                "page_number": number,
                "raw_text": text,
            }
            for number, text in pages
        ],
    }


def test_detect_valid_rule_heading():
    """Recognize the next sequential regulatory rule."""

    result = detect_rule_heading(
        "1. Short title and commencement.—(1) These rules apply.",
        expected_number=1,
    )

    assert result is not None
    assert result[0] == 1
    assert result[1].startswith("Short title")


def test_reject_wrong_rule_number():
    """Reject numbered lines that are out of sequence."""

    result = detect_rule_heading(
        "5. This is a numbered schedule entry.",
        expected_number=2,
    )

    assert result is None


def test_reject_unnumbered_heading():
    """Do not classify ordinary text as a numbered rule."""

    result = detect_rule_heading(
        "Reasonable security safeguards.",
        expected_number=1,
    )

    assert result is None


def test_extract_rule_title():
    """Separate a rule title from its legal body text."""

    title = extract_rule_title(
        "Definitions.—Unless the context otherwise requires"
    )

    assert title == "Definitions"


def test_parse_multiple_rules():
    """Detect consecutive rules on the same PDF page."""

    extraction = make_extraction([
        (
            28,
            "1. First rule.—First rule text.\n"
            "2. Second rule.—Second rule text.",
        )
    ])

    result = parse_sections(
        extraction,
        start_page=28,
        end_page=28,
    )

    assert result["total_sections"] == 2
    assert [s["rule_number"] for s in result["sections"]] == [
        1, 2
    ]


def test_rule_continues_across_pages():
    """Preserve a rule's text when it spans PDF pages."""

    extraction = make_extraction([
        (28, "1. Data protection.—Beginning of rule."),
        (29, "This rule continues on the next page."),
    ])

    result = parse_sections(
        extraction,
        start_page=28,
        end_page=29,
    )

    section = result["sections"][0]

    assert section["start_page"] == 28
    assert section["end_page"] == 29
    assert "This rule continues" in section["text"]


def test_stop_before_schedule_page():
    """
    Ensure schedule numbering is not mistaken for rules.

    The schedule begins on a new page, matching the
    structure of the current DPDP draft document.
    """

    extraction = make_extraction([
        (28, "1. First rule.—Regulatory text."),
        (
            29,
            "THE GAZETTE OF INDIA\n"
            "FIRST SCHEDULE\n"
            "1. The applicant is a company.\n"
            "2. The applicant has sufficient capacity.",
        ),
    ])

    result = parse_sections(
        extraction,
        start_page=28,
        end_page=29,
    )

    assert result["total_sections"] == 1
    assert result["sections"][0]["end_page"] == 28
    assert "The applicant is a company" not in (
        result["sections"][0]["text"]
    )
    assert result["warnings"] == []


def test_preserve_source_metadata():
    """Retain the filename and source document fingerprint."""

    extraction = make_extraction([
        (28, "1. Definitions.—Regulatory text."),
    ])

    result = parse_sections(
        extraction,
        start_page=28,
        end_page=28,
    )

    assert result["filename"] == "sample_regulation.pdf"
    assert result["source_sha256"] == "sample_hash"
    assert result["language"] == "en"


def test_save_and_reload_json(tmp_path):
    """Verify that structured rules can be saved and reloaded."""

    extraction = make_extraction([
        (28, "1. Definitions.—Regulatory text."),
    ])

    result = parse_sections(
        extraction,
        start_page=28,
        end_page=28,
    )

    output_path = tmp_path / "parsed" / "sections.json"

    save_sections(result, output_path)

    assert output_path.is_file()

    with output_path.open("r", encoding="utf-8") as file:
        saved = json.load(file)

    assert saved["total_sections"] == 1
    assert saved["sections"][0]["section_id"] == "en_rule_1"


def test_invalid_page_range():
    """Reject a page range whose end precedes its start."""

    extraction = make_extraction([
        (28, "1. Definitions.—Regulatory text."),
    ])

    with pytest.raises(ValueError):
        parse_sections(
            extraction,
            start_page=38,
            end_page=28,
        )


def test_missing_input_file(tmp_path):
    """Raise an error when the extraction JSON is missing."""

    missing_path = tmp_path / "missing.json"

    with pytest.raises(FileNotFoundError):
        load_extraction(missing_path)


def test_invalid_extraction_structure(tmp_path):
    """Reject JSON that does not contain a valid pages list."""

    invalid_path = tmp_path / "invalid.json"

    invalid_path.write_text(
        json.dumps({"filename": "invalid.pdf"}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        load_extraction(invalid_path)

def test_detect_rule_heading_without_space():
    """
    Verify that a rule heading is recognized even when
    there is no space after the rule number.

    Regression case:
        Final DPDP Rules 2025, Rule 17.
    """
    from app.document_engine.section_parser import detect_rule_heading

    heading = "17.Appointment of Chairperson and other Members."

    result = detect_rule_heading(
        heading,
        expected_number=17,
    )

    assert result is not None
    assert result[0] == 17
def test_gazette_header_excluded_from_rule_text():
    """
    Verify that repeated Gazette page headers are excluded
    when a regulatory rule continues across PDF pages.

    The rule's content and page boundaries must remain
    correct after removing publication metadata.
    """
    from app.document_engine.section_parser import parse_sections

    extraction = make_extraction([
        (
            28,
            "1. First rule.—The regulatory text begins here."
        ),
        (
            29,
            "29       THE GAZETTE OF INDIA : EXTRAORDINARY "
            "[PART II—SEC. 3(i)]\n"
            "The regulatory text continues here."
        ),
    ])

    result = parse_sections(
        extraction,
        start_page=28,
        end_page=29,
    )

    assert result["total_sections"] == 1

    rule = result["sections"][0]

    assert "THE GAZETTE OF INDIA" not in rule["text"]
    assert "The regulatory text begins here." in rule["text"]
    assert "The regulatory text continues here." in rule["text"]
    assert rule["start_page"] == 28
    assert rule["end_page"] == 29
    
def test_standalone_punctuation_filter():
    """
    Verify that isolated punctuation is detected without
    treating normal regulatory text as an artifact.
    """
    from app.document_engine.section_parser import (
        is_standalone_punctuation,
    )

    assert is_standalone_punctuation(".") is True
    assert is_standalone_punctuation(" ; ") is True
    assert is_standalone_punctuation("Regulatory text.") is False
    assert is_standalone_punctuation("") is False