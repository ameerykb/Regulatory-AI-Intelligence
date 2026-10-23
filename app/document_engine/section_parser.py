
"""
Regulatory Section Parser
=========================

Project:
    AI Regulatory Change Impact Intelligence System

Purpose:
    Convert extracted regulatory PDF pages into numbered rules,
    preserving source references and identifying numbering problems.

Current use:
    Parse the English rules in the DPDP Draft Rules 2025.

Important:
    Page boundaries are configurable and must be verified for
    each new regulatory document.

Usage:
    python -m app.document_engine.section_parser
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys

from pathlib import Path
from typing import TypedDict


logger = logging.getLogger(__name__)

DEFAULT_INPUT = "data/extracted/dpdp_draft_2025.json"
DEFAULT_OUTPUT = "data/parsed/dpdp_draft_2025_sections.json"

DEFAULT_START_PAGE = 28
DEFAULT_END_PAGE = 37

# Detect a numbered heading beginning with English text.
RULE_PATTERN = re.compile(
    r"^\s*(\d{1,3})\.\s*([A-Za-z].*)$"
)

# A standalone schedule heading marks the end of main rules.
SCHEDULE_PATTERN = re.compile(
    r"^\s*(?:FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH)"
    r"\s+SCHEDULE\s*$",
    re.IGNORECASE
)


class Section(TypedDict):
    """Represent one numbered regulatory rule."""

    section_id: str
    rule_number: int
    title: str
    text: str
    start_page: int
    end_page: int


class ParseResult(TypedDict):
    """Represent the parsed rules and validation warnings."""

    filename: str
    source_sha256: str
    language: str
    total_sections: int
    sections: list[Section]
    warnings: list[str]
    unclassified_text: str


def load_extraction(path: str | Path) -> dict:
    """
    Load and validate an extracted PDF JSON file.

    Args:
        path: Location of extraction JSON.

    Returns:
        Parsed extraction dictionary.

    Raises:
        FileNotFoundError: File does not exist.
        ValueError: Required page data is missing.
        json.JSONDecodeError: JSON is invalid.
    """

    source = Path(path)

    if not source.is_file():
        raise FileNotFoundError(
            f"Extraction file not found: {source}"
        )

    with source.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object.")

    pages = data.get("pages")

    if not isinstance(pages, list):
        raise ValueError("Missing or invalid pages list.")

    for index, page in enumerate(pages):
        if not isinstance(page, dict):
            raise ValueError(
                f"Invalid page record at index {index}."
            )

        if not isinstance(page.get("page_number"), int):
            raise ValueError(
                f"Missing page number at index {index}."
            )

        if not isinstance(
            page.get("raw_text", page.get("text")),
            str
        ):
            raise ValueError(
                f"Missing page text at index {index}."
            )

    return data

def is_standalone_punctuation(line: str) -> bool:
    """
    Check whether a line contains only an isolated
    punctuation character introduced by PDF extraction.

    Args:
        line: A single extracted text line.

    Returns:
        True if the line contains only an isolated
        punctuation character; otherwise False.
    """
    stripped = line.strip()

    return stripped in {".", ",", ";", ":"}

def is_gazette_page_header(line: str) -> bool:
    """
    Detect repeated Gazette of India page headers.

    These headers appear when regulatory rules continue
    across PDF pages. They are publication metadata,
    not part of the regulatory provisions.

    Args:
        line: One line of extracted PDF text.

    Returns:
        True when the line matches a numbered Gazette
        page header; otherwise False.
    """
    return bool(
        re.match(
            r"^\s*\d+\s+THE\s+GAZETTE\s+OF\s+INDIA\s*:\s*EXTRAORDINARY\b",
            line,
            re.IGNORECASE,
        )
    )
def detect_rule_heading(
    line: str,
    expected_number: int
) -> tuple[int, str] | None:
    """
    Detect the next sequential numbered rule.

    Args:
        line: Extracted text line.
        expected_number: Rule number expected next.

    Returns:
        Rule number and heading text when matched;
        otherwise None.

    Notes:
        Sequential numbering reduces false positives,
        but cannot eliminate every ambiguity.
    """

    match = RULE_PATTERN.match(line)

    if not match:
        return None

    number = int(match.group(1))
    heading = match.group(2).strip()

    if number != expected_number:
        return None

    return number, heading


def extract_rule_title(heading: str) -> str:
    """
    Extract a readable rule title from its heading.

    Args:
        heading: Text following the rule number.

    Returns:
        Title text before the heading/body separator,
        or the complete heading if no separator exists.
    """

    for separator in (".—", "—", "–"):
        if separator in heading:
            return heading.split(separator, 1)[0].strip()

    return heading.strip()


def parse_sections(
    extraction: dict,
    start_page: int = DEFAULT_START_PAGE,
    end_page: int = DEFAULT_END_PAGE
) -> ParseResult:
    """
    Parse sequential English rules from a selected page range.

    Args:
        extraction: Output of pdf_extractor.py.
        start_page: First PDF page to inspect, inclusive.
        end_page: Last PDF page to inspect, inclusive.

    Returns:
        Structured rules, source metadata, and warnings.

    Raises:
        ValueError: Invalid page range.

    Notes:
        Text before Rule 1 is preserved as unclassified.
        The parser stops when a standalone schedule heading
        is encountered.
    """

    if start_page < 1 or end_page < start_page:
        raise ValueError("Invalid page range.")

    sections: list[Section] = []
    warnings: list[str] = []
    unclassified_lines: list[str] = []

    current: Section | None = None
    expected_number = 1
    schedule_found = False

    pages = sorted(
        extraction["pages"],
        key=lambda page: page["page_number"]
    )

    selected_pages = [
        page for page in pages
        if start_page <= page["page_number"] <= end_page
    ]

    if not selected_pages:
        raise ValueError(
            "No PDF pages found in the selected range."
        )

    for page in selected_pages:
        page_number = page["page_number"]

        page_text = page.get(
            "raw_text",
            page.get("text", "")
        )
                    # Identify whether this page contains a schedule heading.
        # A schedule may start on the same page as the final rule.
        page_lines = page_text.splitlines()

        schedule_index = next(
            (
                index
                for index, line in enumerate(page_lines)
                if SCHEDULE_PATTERN.fullmatch(line.strip())
            ),
            None
        )

        # If the schedule starts on this page, retain only
        # the lines before its heading.
        if schedule_index is not None:
            page_lines = page_lines[:schedule_index]

            # When the page contains no regulatory rule text
            # before the schedule, do not append its Gazette
            # header to the previous rule.
            meaningful_lines = [ 
                line.strip()
                for line in page_lines
                if line.strip()
                and not re.search(
                    r"THE GAZETTE OF INDIA",
                    line,
                    re.IGNORECASE,
                )
                and not re.fullmatch(
                    r"[\W_]+",
                    line.strip(),
                )
            ]

            if not meaningful_lines:
                schedule_found = True
                break
        
        

        for line in page_lines:
            stripped = line.strip()
                        # Skip repeated Gazette publication headers.
            # These are PDF formatting, not regulatory text.
            # Preserve the original extracted PDF separately.
            if is_gazette_page_header(line):
                continue
            if is_standalone_punctuation(line):
                continue
                  

            heading = detect_rule_heading(
                stripped,
                expected_number
            )

            if heading is not None:
                rule_number, heading_text = heading

                if current is not None:
                    current["text"] = current["text"].strip()
                    sections.append(current)

                current = {
                    "section_id": f"en_rule_{rule_number}",
                    "rule_number": rule_number,
                    "title": extract_rule_title(heading_text),
                    "text": stripped,
                    "start_page": page_number,
                    "end_page": page_number
                }

                expected_number += 1
                continue

            if current is not None:
                current["text"] += "\n" + line
                if stripped:
                    current["end_page"] = page_number
            else:
                unclassified_lines.append(line)

        if schedule_index is not None:
            schedule_found = True
            break

    # Store the final rule.
    if current is not None:
        current["text"] = current["text"].strip()
        sections.append(current)

    # Report unexpected numbering without inventing rules.
    numbers = [
        section["rule_number"]
        for section in sections
    ]

    if not numbers:
        warnings.append(
            "No numbered rules were detected."
        )

    if numbers and numbers[0] != 1:
        warnings.append(
            "The first detected rule is not Rule 1."
        )

    if not schedule_found:
        warnings.append(
            "No schedule boundary was detected in "
            "the selected page range."
        )

    # Warn when the final detected rule reaches the page
    # boundary; additional text may exist on later pages.
        # Warn about a potentially incomplete final rule only
    # when no schedule boundary was detected.
    #
    # If the schedule heading was found, the parser has
    # identified the end of the main regulatory rules.
    if (
        sections
        and not schedule_found
        and sections[-1]["end_page"] == end_page
    ):
        warnings.append(
            "Final rule reaches the selected end page. "
            "Verify that its complete text was captured."
        )

    return {
        "filename": extraction.get("filename", "unknown"),
        "source_sha256": extraction.get("sha256", ""),
        "language": "en",
        "total_sections": len(sections),
        "sections": sections,
        "warnings": warnings,
        "unclassified_text": "\n".join(
            unclassified_lines
        ).strip()
    }


def save_sections(
    result: ParseResult,
    output_path: str | Path
) -> None:
    """
    Save structured regulatory rules to UTF-8 JSON.

    Args:
        result: Completed parsing result.
        output_path: Destination JSON file.
    """

    destination = Path(output_path)

    destination.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with destination.open("w", encoding="utf-8") as file:
        json.dump(
            result,
            file,
            indent=4,
            ensure_ascii=False
        )


def main(argv: list[str] | None = None) -> int:
    """
    Run the regulatory section parsing command.

    Args:
        argv: Optional command-line arguments.

    Returns:
        0 on successful execution, 1 on error.
    """

    parser = argparse.ArgumentParser(
        description="Parse sequential English regulatory rules."
    )

    parser.add_argument(
        "input_json",
        nargs="?",
        default=DEFAULT_INPUT
    )

    parser.add_argument(
        "output_json",
        nargs="?",
        default=DEFAULT_OUTPUT
    )

    parser.add_argument(
        "--start-page",
        type=int,
        default=DEFAULT_START_PAGE
    )

    parser.add_argument(
        "--end-page",
        type=int,
        default=DEFAULT_END_PAGE
    )

    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s"
    )

    try:
        extraction = load_extraction(args.input_json)

        result = parse_sections(
            extraction,
            start_page=args.start_page,
            end_page=args.end_page
        )

        save_sections(result, args.output_json)

    except (
        FileNotFoundError,
        ValueError,
        OSError,
        json.JSONDecodeError
    ) as error:
        logger.error("Parsing failed: %s", error)
        return 1

    logger.info(
        "Detected %d regulatory rules.",
        result["total_sections"]
    )

    for section in result["sections"]:
        logger.info(
            "Rule %d | Pages %d-%d | %s",
            section["rule_number"],
            section["start_page"],
            section["end_page"],
            section["title"][:65]
        )

    for warning in result["warnings"]:
        logger.warning(warning)

    logger.info("Saved to: %s", args.output_json)

    return 0


if __name__ == "__main__":
    sys.exit(main())
