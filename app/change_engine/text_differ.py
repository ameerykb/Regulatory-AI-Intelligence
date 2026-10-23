"""
Regulatory Text Difference Engine
=================================

Detects wording changes between corresponding
regulatory provisions.

Responsibilities:
    - Compare draft and final regulatory text.
    - Identify unchanged and modified wording.
    - Extract inserted, deleted, and replaced text.
    - Preserve evidence for human review.

Current stage:
    Text validation and normalization.

Note:
    Textual differences do not automatically establish
    changes in legal meaning.
"""

import re
from difflib import SequenceMatcher
from typing import Any


def normalize_comparison_text(text: str) -> str:
    """
    Normalize regulatory text before comparison.

    Removes unnecessary whitespace while preserving
    original wording, punctuation, and capitalization.

    Args:
        text: Extracted regulatory provision text.

    Returns:
        A normalized string suitable for comparison.

    Raises:
        TypeError: If the input is not a string.
        ValueError: If the text is empty or contains
            only whitespace.

    Example:
        >>> normalize_comparison_text("Rule  1.\\n  Notice")
        'Rule 1. Notice'
    """
    if not isinstance(text, str):
        raise TypeError("Regulatory text must be a string.")

    normalized = re.sub(r"\s+", " ", text).strip()

    if not normalized:
        raise ValueError("Regulatory text cannot be empty.")

    return normalized

def remove_gazette_page_headers(text: str) -> str:
    """
    Remove recognizable Gazette page-header artifacts.

    This function targets repeated page-header lines that
    can appear inside text extracted from Indian Gazette PDFs.

    It does not modify the original stored PDF or parsed data.

    Args:
        text: Regulatory text containing possible page headers.

    Returns:
        Text with recognized page-header lines removed.

    Raises:
        TypeError: If text is not a string.

    Important:
        Only remove lines that match a recognizable header
        pattern. Never remove arbitrary Hindi regulatory text.
    """
    if not isinstance(text, str):
        raise TypeError("Regulatory text must be a string.")

    cleaned_lines = []

    for line in text.splitlines():
        stripped = line.strip()

        # Recognize a Gazette header containing the publication
        # name and an extraordinary-issue marker.
        is_gazette_header = (
            "भारत का रािपत्र" in stripped
            or "भारत का राजपत्र" in stripped
        ) and "असाधारण" in stripped

        if not is_gazette_header:
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines)

def compare_regulatory_text(
    draft_text: str,
    final_text: str,
) -> dict[str, Any]:
    """
    Compare two regulatory provisions at word level.

    Identifies:
        - Equal text
        - Inserted text
        - Deleted text
        - Replaced text

    Args:
        draft_text: Wording from the earlier regulation.
        final_text: Wording from the newer regulation.

    Returns:
        A dictionary containing the change status,
        similarity score, and detailed text operations.

    Raises:
        TypeError: If either input is not a string.
        ValueError: If either input is empty.

    Notes:
        Text differences are not necessarily changes
        in legal meaning. All results require review.
    """
    draft = normalize_comparison_text(draft_text)
    final = normalize_comparison_text(final_text)

    # Split into whitespace-separated tokens while keeping
    # the original capitalization and punctuation.
    draft_words = draft.split()
    final_words = final.split()

    # Compare word sequences without the automatic
    # popular-token suppression heuristic.
    matcher = SequenceMatcher(
        None,
        draft_words,
        final_words,
        autojunk=False,
    )

    operations = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        operations.append({
            "operation": tag,
            "draft_text": " ".join(draft_words[i1:i2]),
            "final_text": " ".join(final_words[j1:j2]),
            "draft_word_range": [i1, i2],
            "final_word_range": [j1, j2],
        })

    has_changes = any(
        operation["operation"] != "equal"
        for operation in operations
    )

    return {
        "status": "modified" if has_changes else "unchanged",
        "similarity": round(matcher.ratio(), 4),
        "operations": operations,
        "review_required": has_changes,
    }

def remove_leading_rule_number(
    text: str,
    expected_rule_number: int,
) -> str:
    """
    Remove an expected leading rule number for comparison.

    This allows corresponding regulatory provisions to be
    compared without treating renumbering as a text amendment.

    The original text remains unchanged in stored data.

    Args:
        text: Regulatory rule text.
        expected_rule_number: Rule number expected at the start.

    Returns:
        Regulatory text without the leading rule number,
        when that exact number is present.

    Raises:
        TypeError: If inputs have invalid types.
        ValueError: If the rule number is not positive or
            the regulatory text is empty.

    Important:
        Only removes the expected number at the beginning.
        Numbers appearing inside the provision are preserved.
    """
    normalized = normalize_comparison_text(text)

    if (
        isinstance(expected_rule_number, bool)
        or not isinstance(expected_rule_number, int)
    ):
        raise TypeError("Expected rule number must be an integer.")

    if expected_rule_number <= 0:
        raise ValueError("Expected rule number must be positive.")

    pattern = rf"^{expected_rule_number}\.(?=\s)"

    cleaned = re.sub(
        pattern,
        "",
        normalized,
        count=1,
    ).strip()

    return cleaned
def prepare_regulatory_text(
    text: str,
    rule_number: int,
) -> str:
    """
    Prepare regulatory text for word-level comparison.

    Processing steps:
        1. Remove recognizable Gazette page headers.
        2. Remove the expected leading rule number.
        3. Normalize unnecessary whitespace.

    Args:
        text: Original regulatory rule text.
        rule_number: Rule number in the source document.

    Returns:
        Cleaned regulatory text suitable for comparison.

    Raises:
        TypeError: If text or rule_number has an invalid type.
        ValueError: If the text is empty or rule_number is invalid.

    Notes:
        This function does not modify the original text.
        Cleaned text is used only for comparison.
        Regulatory changes still require human review.
    """
    # Remove known PDF extraction artifacts.
    cleaned = remove_gazette_page_headers(text)

    # Remove the expected rule number from the beginning.
    cleaned = remove_leading_rule_number(
        cleaned,
        rule_number,
    )

    # Return consistently normalized text.
        # Normalize whitespace and supported punctuation spacing.
    cleaned = normalize_punctuation_spacing(cleaned)

    # Return consistently normalized text.
    return cleaned

def normalize_punctuation_spacing(text: str) -> str:
    """
    Normalize selected punctuation-spacing differences.

    This function removes unnecessary spaces immediately
    before an em dash (—) when it follows a sentence
    punctuation mark.

    Example:
        "Principals. —" -> "Principals.—"

    Args:
        text: Regulatory text to normalize.

    Returns:
        Text with consistent spacing around the
        supported punctuation pattern.

    Raises:
        TypeError: If text is not a string.
        ValueError: If text is empty.

    Important:
        This function does not remove punctuation,
        change words, or modify the original source.
    """
    normalized = normalize_comparison_text(text)

    # Normalize spaces between sentence punctuation
    # and an em dash. Preserve the punctuation itself.
    normalized = re.sub(
        r"([.!?])\s+—",
        r"\1—",
        normalized,
    )

    return normalized