"""
Rule Alignment Engine
=====================

Matches regulatory rules across different document versions.

Purpose:
    Identify corresponding provisions even when their rule
    numbers or positions have changed.

Planned capabilities:
    - Compare rule titles.
    - Calculate text similarity.
    - Detect renumbered rules.
    - Identify added and removed rules.
    - Support split and merged provisions.

Current stage:
    Input validation and text normalization.

Dependencies:
    Python standard library only.
"""

import re
from difflib import SequenceMatcher
from typing import Any


def normalize_text(text: str) -> str:
    """
    Normalize regulatory text for similarity comparison.

    Converts text to lowercase and collapses repeated
    whitespace without changing the original source.

    Args:
        text: Regulatory text to normalize.

    Returns:
        A normalized string suitable for comparison.

    Raises:
        TypeError: If the input is not a string.
    """
    if not isinstance(text, str):
        raise TypeError("Text must be a string.")

    normalized = text.casefold()
    normalized = re.sub(r"\s+", " ", normalized)

    return normalized.strip()


def validate_rule(rule: dict[str, Any]) -> None:
    """
    Validate the basic structure of a parsed regulatory rule.

    Args:
        rule: A dictionary representing one regulatory rule.

    Raises:
        TypeError: If the rule is not a dictionary.
        ValueError: If required fields are missing or invalid.
    """
    if not isinstance(rule, dict):
        raise TypeError("Rule must be a dictionary.")

    required_fields = (
        "section_id",
        "rule_number",
        "title",
        "text",
    )

    for field in required_fields:
        if field not in rule:
            raise ValueError(f"Missing required field: {field}")

    if not isinstance(rule["rule_number"], int) or isinstance(
        rule["rule_number"], bool
    ) or rule["rule_number"] < 1:
        raise ValueError("Rule number must be a positive integer.")

    for field in ("section_id", "title", "text"):
        if not isinstance(rule[field], str) or not rule[field].strip():
            raise ValueError(
                f"Field '{field}' must be a non-empty string."
            )
def calculate_title_similarity(
    title_a: str,
    title_b: str,
) -> float:
    """
    Calculate similarity between two regulatory rule titles.

    Uses Python's SequenceMatcher to compare normalized
    text without relying on rule numbers.

    Args:
        title_a: Title from the earlier regulatory version.
        title_b: Title from the newer regulatory version.

    Returns:
        A similarity score between 0.0 and 1.0.

    Raises:
        TypeError: If either title is not a string.

    Notes:
        This measures textual similarity, not legal or
        semantic equivalence. It will be combined with
        other signals in the alignment engine.
    """
    normalized_a = normalize_text(title_a).rstrip(" .;:")
    normalized_b = normalize_text(title_b).rstrip(" .;:")

    if not normalized_a or not normalized_b:
        return 0.0

    return SequenceMatcher(
        None,
        normalized_a,
        normalized_b,
        autojunk=False,
    ).ratio()

def calculate_rule_similarity(
    draft_rule: dict[str, Any],
    final_rule: dict[str, Any],
) -> dict[str, float]:
    """
    Compare two regulatory rules using title and text similarity.

    Purpose:
        Estimate whether rules from different document versions
        might correspond to the same regulatory provision.

    Args:
        draft_rule: A parsed rule from the draft document.
        final_rule: A parsed rule from the final document.

    Returns:
        A dictionary containing:
            title_similarity: Similarity between rule titles.
            text_similarity: Similarity between rule texts.
            combined_similarity: Weighted similarity score.

    Raises:
        TypeError: If a rule is not a dictionary.
        ValueError: If required rule fields are invalid.

    Notes:
        Scores measure textual resemblance, not legal equivalence.
        A high score does not prove two provisions have the same
        legal effect.

        The 40/60 weights are provisional and will be evaluated
        against the actual DPDP rule mappings.
    """
    validate_rule(draft_rule)
    validate_rule(final_rule)

    title_score = calculate_title_similarity(
        draft_rule["title"],
        final_rule["title"],
    )

    draft_text = normalize_text(draft_rule["text"])
    final_text = normalize_text(final_rule["text"])

    text_score = SequenceMatcher(
        None,
        draft_text,
        final_text,
        autojunk=False,
    ).ratio()

    combined_score = (
        0.40 * title_score
        + 0.60 * text_score
    )

    return {
        "title_similarity": round(title_score, 4),
        "text_similarity": round(text_score, 4),
        "combined_similarity": round(combined_score, 4),
    }

def find_rule_candidates(
    draft_rule: dict[str, Any],
    final_rules: list[dict[str, Any]],
    top_k: int = 3,
) -> list[dict[str, Any]]:
    """
    Find the most similar final-version rules for one draft rule.

    Compares a draft rule against all supplied final rules
    and ranks potential matches by combined similarity.

    Args:
        draft_rule: A parsed regulatory rule from the draft.
        final_rules: Parsed rules from the final document.
        top_k: Maximum number of candidates to return.

    Returns:
        A descending list of candidate matches containing
        rule numbers, titles, and similarity scores.

    Raises:
        TypeError: If final_rules is not a list or top_k
            is not an integer.
        ValueError: If top_k is less than one.

    Notes:
        Candidate rankings are suggestions, not confirmed
        legal relationships. Split and merged provisions
        require additional analysis.
    """
    validate_rule(draft_rule)

    if not isinstance(final_rules, list):
        raise TypeError("Final rules must be a list.")

    if isinstance(top_k, bool) or not isinstance(top_k, int):
        raise TypeError("top_k must be an integer.")

    if top_k < 1:
        raise ValueError("top_k must be at least 1.")

    candidates = []

    for final_rule in final_rules:
        scores = calculate_rule_similarity(
            draft_rule,
            final_rule,
        )

        candidates.append({
            "draft_rule_number": draft_rule["rule_number"],
            "final_rule_number": final_rule["rule_number"],
            "final_title": final_rule["title"],
            **scores,
        })

    candidates.sort(
        key=lambda item: (
            -item["combined_similarity"],
            -item["title_similarity"],
            item["final_rule_number"],
        )
    )

    return candidates[:top_k]