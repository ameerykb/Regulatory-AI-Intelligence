"""Validate quotations against retrieved regulatory evidence."""

import re


def normalize_text(text: str) -> str:
    """Normalize whitespace for quotation comparison."""
    return re.sub(r"\s+", " ", text).strip()


def validate_evidence_quote(
    quote: str,
    evidence: str,
) -> dict:
    """
    Check whether a quoted passage occurs in the evidence.

    This performs literal text matching after whitespace
    normalization. It does not verify legal meaning.
    """

    if not quote.strip():
        return {
            "is_valid": False,
            "reason": "Empty quotation.",
        }

    if not evidence.strip():
        return {
            "is_valid": False,
            "reason": "No evidence provided.",
        }

    normalized_quote = normalize_text(quote)
    normalized_evidence = normalize_text(evidence)

    is_valid = normalized_quote in normalized_evidence

    return {
        "is_valid": is_valid,
        "reason": (
            "Quotation found in evidence."
            if is_valid
            else "Quotation not found in evidence."
        ),
    }