
"""
PDF Extraction Module
=====================

Project:
    AI Regulatory Change Impact Intelligence System

Purpose:
    Extract regulatory PDF text while preserving page references,
    document integrity information, and extraction warnings.

Features:
    - Validate input files and PDF format.
    - Extract text page by page.
    - Preserve 1-indexed PDF page numbers.
    - Optionally use OCR for pages without selectable text.
    - Optionally remove repeated headers and footers.
    - Preserve original extracted text separately from cleaned text.
    - Generate a SHA-256 hash for document identification.
    - Save structured UTF-8 JSON.
    - Provide command-line options, logging, and exit codes.

Dependencies:
    PyMuPDF

Optional dependency:
    Tesseract OCR, required only when using --ocr.

Usage:
    python -m app.document_engine.pdf_extractor

    python -m app.document_engine.pdf_extractor \
        input.pdf output.json --ocr

Important:
    OCR results and cleaned regulatory text should be manually
    verified before use in legal impact assessments.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict

try:
    import pymupdf
except ImportError:
    import fitz as pymupdf


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

logger = logging.getLogger(__name__)

DEFAULT_INPUT = "data/regulatory/dpdp_draft_2025.pdf"
DEFAULT_OUTPUT = "data/extracted/dpdp_draft_2025.json"

HEADER_FOOTER_EDGE_LINES = 2
HEADER_FOOTER_MIN_PAGES = 4
HEADER_FOOTER_MIN_FRACTION = 0.6


# ---------------------------------------------------------
# Data Structures
# ---------------------------------------------------------

class PageResult(TypedDict):
    """Structured extraction information for one PDF page."""

    page_number: int
    raw_text: str
    text: str
    char_count: int
    has_text: bool
    ocr_used: bool


class ExtractionResult(TypedDict):
    """Structured extraction result for an entire PDF."""

    filename: str
    sha256: str
    extracted_at: str
    pymupdf_version: str
    total_pages: int
    pages_with_text: int
    pages: list[PageResult]


# ---------------------------------------------------------
# File Validation
# ---------------------------------------------------------

def validate_pdf_path(pdf_path: str | Path) -> Path:
    """
    Validate that the supplied path references an existing PDF.

    Args:
        pdf_path: Location of the PDF file.

    Returns:
        Resolved Path object.

    Raises:
        FileNotFoundError: File does not exist.
        ValueError: File extension or signature is invalid.
    """

    path = Path(pdf_path).resolve()

    if not path.is_file():
        raise FileNotFoundError(
            f"PDF file not found: {path}"
        )

    if path.suffix.lower() != ".pdf":
        raise ValueError(
            "Unsupported file type. Expected a .pdf file."
        )

    # Check the PDF file signature rather than relying only
    # on the filename extension.
    with path.open("rb") as file:
        signature = file.read(1024)

    if b"%PDF-" not in signature:
        raise ValueError(
            "The supplied file does not have a valid PDF header."
        )

    return path


# ---------------------------------------------------------
# Document Hashing
# ---------------------------------------------------------

def calculate_sha256(file_path: Path) -> str:
    """
    Calculate the SHA-256 hash of a file.

    The hash uniquely identifies the exact file contents,
    helping track which regulatory document was analyzed.

    Args:
        file_path: Path to the source file.

    Returns:
        Hexadecimal SHA-256 hash.
    """

    sha256 = hashlib.sha256()

    # Read the file in chunks to avoid loading large PDFs
    # entirely into memory.
    with file_path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b""
        ):
            sha256.update(chunk)

    return sha256.hexdigest()


# ---------------------------------------------------------
# Page Text Extraction
# ---------------------------------------------------------

def extract_page_text(
    page: pymupdf.Page,
    use_ocr: bool = False
) -> tuple[str, bool]:
    """
    Extract text from a single PDF page.

    Args:
        page: PyMuPDF page object.
        use_ocr: Enable OCR if no selectable text exists.

    Returns:
        Tuple containing:
            - Extracted text.
            - Whether OCR successfully produced text.

    Notes:
        Text sorting is a reading-order heuristic and may
        not preserve every complex document layout.
    """

    # Extract selectable PDF text using approximate
    # top-to-bottom, left-to-right ordering.
    text = page.get_text(
        "text",
        sort=True
    ).strip()

    if text or not use_ocr:
        return text, False

    logger.info(
        "Attempting OCR on page %d",
        page.number + 1
    )

    try:
        textpage = page.get_textpage_ocr(
            language="eng",
            dpi=300,
            full=True
        )

        ocr_text = page.get_text(
            "text",
            textpage=textpage,
            sort=True
        ).strip()

        return ocr_text, bool(ocr_text)

    except Exception as error:
        logger.warning(
            "OCR failed on page %d: %s",
            page.number + 1,
            error
        )

        return "", False


# ---------------------------------------------------------
# Header and Footer Processing
# ---------------------------------------------------------

def normalize_boilerplate_line(line: str) -> str:
    """
    Normalize whitespace for repeated-line comparison.

    Digits are deliberately preserved because numbers
    in regulatory documents may identify legal provisions.

    Args:
        line: Input text line.

    Returns:
        Whitespace-normalized line.
    """

    return re.sub(
        r"\s+",
        " ",
        line.strip()
    )


def get_edge_indices(
    lines: list[str]
) -> set[int]:
    """
    Identify actual line positions near page boundaries.

    Args:
        lines: All text lines on one page.

    Returns:
        Set of indices for the first and last nonempty
        lines, limited by HEADER_FOOTER_EDGE_LINES.
    """

    nonempty_indices = [
        index
        for index, line in enumerate(lines)
        if line.strip()
    ]

    first = nonempty_indices[
        :HEADER_FOOTER_EDGE_LINES
    ]

    last = nonempty_indices[
        -HEADER_FOOTER_EDGE_LINES:
    ]

    return set(first + last)


def strip_repeated_headers_footers(
    pages: list[PageResult]
) -> int:
    """
    Remove repeated text occurring near page boundaries.

    This function changes only the cleaned 'text' field.
    The original 'raw_text' remains unchanged.

    A candidate is removed only when it occurs at an
    actual page edge and repeats across enough pages.

    Args:
        pages: Extracted page records.

    Returns:
        Number of removed lines.

    Warning:
        Repeated legal headings can resemble boilerplate.
        Always inspect cleaned text before further analysis.
    """

    if len(pages) < HEADER_FOOTER_MIN_PAGES:
        return 0

    # Count candidate occurrences by distinct page.
    counts: Counter[str] = Counter()

    for page in pages:
        lines = page["text"].splitlines()
        indices = get_edge_indices(lines)

        candidates = {
            normalize_boilerplate_line(lines[index])
            for index in indices
            if lines[index].strip()
        }

        counts.update(candidates)

    # Use a ceiling so the minimum fraction is respected.
    import math

    threshold = max(
        2,
        math.ceil(
            len(pages) * HEADER_FOOTER_MIN_FRACTION
        )
    )

    repeated_lines = {
        line
        for line, count in counts.items()
        if count >= threshold
    }

    removed = 0

    for page in pages:
        lines = page["text"].splitlines()
        edge_indices = get_edge_indices(lines)

        kept_lines = []

        for index, line in enumerate(lines):

            normalized = normalize_boilerplate_line(
                line
            )

            # Only remove actual edge lines.
            if (
                index in edge_indices
                and normalized in repeated_lines
            ):
                removed += 1
                continue

            kept_lines.append(line)

        page["text"] = "\n".join(
            kept_lines
        ).strip()

        page["char_count"] = len(
            page["text"]
        )

        page["has_text"] = bool(
            page["text"]
        )

    return removed


# ---------------------------------------------------------
# Main Extraction Pipeline
# ---------------------------------------------------------

def extract_pdf(
    pdf_path: str | Path,
    *,
    use_ocr: bool = False,
    strip_headers_footers: bool = False
) -> ExtractionResult:
    """
    Extract regulatory PDF text and metadata.

    Args:
        pdf_path: Source PDF location.
        use_ocr: Enable optional OCR fallback.
        strip_headers_footers: Remove repeated edge lines.

    Returns:
        ExtractionResult containing document metadata,
        SHA-256 hash, and page-level extracted text.

    Raises:
        FileNotFoundError: PDF does not exist.
        ValueError: Invalid or protected PDF.
        RuntimeError: PDF processing failure.
    """

    path = validate_pdf_path(pdf_path)

    document_hash = calculate_sha256(path)

    pages: list[PageResult] = []

    with pymupdf.open(path) as document:

        if document.needs_pass:
            raise ValueError(
                "Password-protected PDFs are not supported."
            )

        for page_number, page in enumerate(
            document,
            start=1
        ):

            text, ocr_used = extract_page_text(
                page,
                use_ocr=use_ocr
            )

            pages.append({
                "page_number": page_number,
                "raw_text": text,
                "text": text,
                "char_count": len(text),
                "has_text": bool(text),
                "ocr_used": ocr_used
            })

    # Cleaning is optional and never modifies raw_text.
    if strip_headers_footers:

        removed = strip_repeated_headers_footers(
            pages
        )

        logger.info(
            "Removed %d repeated header/footer lines",
            removed
        )

    result: ExtractionResult = {
        "filename": path.name,
        "sha256": document_hash,
        "extracted_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "pymupdf_version": str(
            pymupdf.VersionBind
        ),
        "total_pages": len(pages),
        "pages_with_text": sum(
            page["has_text"]
            for page in pages
        ),
        "pages": pages
    }

    return result


# ---------------------------------------------------------
# JSON Export
# ---------------------------------------------------------

def save_extraction(
    result: ExtractionResult,
    output_path: str | Path
) -> None:
    """
    Save extraction results as formatted UTF-8 JSON.

    Args:
        result: Structured PDF extraction data.
        output_path: Destination JSON file path.

    Returns:
        None
    """

    output = Path(output_path)

    output.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with output.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            result,
            file,
            indent=4,
            ensure_ascii=False
        )


# ---------------------------------------------------------
# Command-Line Interface
# ---------------------------------------------------------

def parse_arguments(
    argv: list[str] | None = None
) -> argparse.Namespace:
    """
    Parse command-line arguments.

    Args:
        argv: Optional list of command-line arguments.

    Returns:
        Parsed argparse namespace.
    """

    parser = argparse.ArgumentParser(
        description=(
            "Extract regulatory PDF text into JSON."
        )
    )

    parser.add_argument(
        "input_pdf",
        nargs="?",
        default=DEFAULT_INPUT
    )

    parser.add_argument(
        "output_json",
        nargs="?",
        default=DEFAULT_OUTPUT
    )

    parser.add_argument(
        "--ocr",
        action="store_true",
        help="Enable OCR for pages without selectable text."
    )

    parser.add_argument(
        "--strip-headers-footers",
        action="store_true",
        help="Remove repeated page-edge lines."
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable detailed logging."
    )

    return parser.parse_args(argv)


# ---------------------------------------------------------
# Application Entry Point
# ---------------------------------------------------------

def main(
    argv: list[str] | None = None
) -> int:
    """
    Execute the complete PDF extraction workflow.

    Args:
        argv: Optional command-line arguments.

    Returns:
        0: Extraction successful.
        1: Expected processing error.
        2: Unexpected error.
    """

    args = parse_arguments(argv)

    logging.basicConfig(
        level=(
            logging.DEBUG
            if args.verbose
            else logging.INFO
        ),
        format=(
            "%(asctime)s %(levelname)s %(message)s"
        )
    )

    try:
        result = extract_pdf(
            args.input_pdf,
            use_ocr=args.ocr,
            strip_headers_footers=(
                args.strip_headers_footers
            )
        )

        save_extraction(
            result,
            args.output_json
        )

    except (
        FileNotFoundError,
        ValueError,
        RuntimeError,
        OSError
    ) as error:

        logger.error(
            "Extraction failed: %s",
            error
        )

        return 1

    except Exception:

        logger.exception(
            "Unexpected extraction error"
        )

        return 2

    logger.info(
        "PDF extraction completed successfully"
    )

    logger.info(
        "Filename: %s",
        result["filename"]
    )

    logger.info(
        "Total pages: %d",
        result["total_pages"]
    )

    logger.info(
        "Pages with text: %d",
        result["pages_with_text"]
    )

    logger.info(
        "Saved to: %s",
        args.output_json
    )

    empty_pages = [
        page["page_number"]
        for page in result["pages"]
        if not page["has_text"]
    ]

    if empty_pages:
        logger.warning(
            "Pages without extractable text: %s",
            empty_pages
        )

    ocr_pages = [
        page["page_number"]
        for page in result["pages"]
        if page["ocr_used"]
    ]

    if ocr_pages:
        logger.warning(
            "OCR-derived text requires verification: pages %s",
            ocr_pages
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
