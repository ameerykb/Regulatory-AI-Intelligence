
"""
Automated Tests for the PDF Extraction Module
=============================================

Project:
    AI Regulatory Change Impact Intelligence System

Purpose:
    Verify PDF validation, text extraction, document hashing,
    JSON export, and preservation of page metadata.

Run from the project root:
    python -m pytest tests/test_pdf_extractor.py -v

Dependencies:
    pytest
    PyMuPDF
"""

import hashlib
import json

import pytest

try:
    import pymupdf
except ImportError:
    import fitz as pymupdf

from app.document_engine.pdf_extractor import (
    calculate_sha256,
    extract_pdf,
    save_extraction,
    validate_pdf_path,
)


@pytest.fixture
def sample_pdf(tmp_path):
    """
    Create a temporary PDF containing two pages of sample text.

    The fixture generates its own PDF so the tests do not depend
    on downloaded regulatory documents.

    Args:
        tmp_path: Temporary directory supplied by pytest.

    Returns:
        Path to the generated sample PDF.
    """

    pdf_path = tmp_path / "sample.pdf"

    document = pymupdf.open()

    for text in [
        "Rule 1: Data protection requirements.",
        "Rule 2: Consent management requirements.",
    ]:
        page = document.new_page()
        page.insert_text((72, 72), text)

    document.save(pdf_path)
    document.close()

    return pdf_path


def test_validate_existing_pdf(sample_pdf):
    """Verify that an existing PDF passes validation."""

    result = validate_pdf_path(sample_pdf)

    assert result == sample_pdf.resolve()


def test_validate_missing_pdf(tmp_path):
    """Verify that a missing PDF raises FileNotFoundError."""

    missing_file = tmp_path / "missing.pdf"

    with pytest.raises(FileNotFoundError):
        validate_pdf_path(missing_file)


def test_reject_non_pdf(tmp_path):
    """Verify that non-PDF files are rejected."""

    text_file = tmp_path / "sample.txt"
    text_file.write_text("This is not a PDF.")

    with pytest.raises(ValueError):
        validate_pdf_path(text_file)


def test_extract_pdf_pages(sample_pdf):
    """Verify that PDF pages are extracted in order."""

    result = extract_pdf(sample_pdf)

    assert result["total_pages"] == 2
    assert result["pages_with_text"] == 2

    assert result["pages"][0]["page_number"] == 1
    assert result["pages"][1]["page_number"] == 2

    assert "Rule 1" in result["pages"][0]["text"]
    assert "Rule 2" in result["pages"][1]["text"]


def test_preserve_raw_text(sample_pdf):
    """Verify that original extracted text is preserved."""

    result = extract_pdf(sample_pdf)

    for page in result["pages"]:
        assert page["raw_text"] == page["text"]


def test_character_count(sample_pdf):
    """Verify that character counts match extracted text."""

    result = extract_pdf(sample_pdf)

    for page in result["pages"]:
        assert page["char_count"] == len(page["text"])


def test_sha256_hash(sample_pdf):
    """Verify that the generated document hash is correct."""

    expected_hash = hashlib.sha256(
        sample_pdf.read_bytes()
    ).hexdigest()

    actual_hash = calculate_sha256(sample_pdf)

    assert actual_hash == expected_hash


def test_save_json(sample_pdf, tmp_path):
    """Verify that extraction results can be saved as JSON."""

    result = extract_pdf(sample_pdf)

    output_path = tmp_path / "output" / "result.json"

    save_extraction(result, output_path)

    assert output_path.exists()

    saved_data = json.loads(
        output_path.read_text(encoding="utf-8")
    )

    assert saved_data["total_pages"] == 2
    assert saved_data["filename"] == "sample.pdf"


def test_empty_pdf_page(tmp_path):
    """Verify that a blank PDF page is correctly identified."""

    pdf_path = tmp_path / "blank.pdf"

    document = pymupdf.open()
    document.new_page()
    document.save(pdf_path)
    document.close()

    result = extract_pdf(pdf_path)

    assert result["total_pages"] == 1
    assert result["pages_with_text"] == 0

    assert result["pages"][0]["has_text"] is False
    assert result["pages"][0]["text"] == ""
