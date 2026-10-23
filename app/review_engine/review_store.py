
"""
Store human review decisions for regulatory changes.

Review decisions are saved separately from the original
regulatory analysis and evidence reports.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def save_review(
    draft_rule_number: int,
    final_rule_number: int,
    status: str,
    reviewer: str,
    comment: str = "",
    file_path: str = "data/reviews/review_decisions.json",
) -> dict[str, Any]:
    """
    Save a human review decision to a JSON file.

    Args:
        draft_rule_number: Draft regulatory rule number.
        final_rule_number: Final regulatory rule number.
        status: Review decision.
        reviewer: Name or identifier of the reviewer.
        comment: Optional review explanation.
        file_path: Path to the review decisions JSON file.

    Returns:
        The saved review record.
    """
    allowed_statuses = {
        "under_review",
        "approved",
        "rejected",
        "needs_revision",
    }

    if status not in allowed_statuses:
        raise ValueError("Invalid review status.")

    if not reviewer.strip():
        raise ValueError("Reviewer cannot be empty.")

    review = {
        "draft_rule_number": draft_rule_number,
        "final_rule_number": final_rule_number,
        "status": status,
        "reviewer": reviewer.strip(),
        "comment": comment,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    }

    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        with path.open("r", encoding="utf-8") as file:
            reviews = json.load(file)
    else:
        reviews = []

    if not isinstance(reviews, list):
        raise ValueError("Review storage must contain a JSON list.")

    
    
    for previous_review in reviews:
        if (
            previous_review["draft_rule_number"] == draft_rule_number
            and previous_review["final_rule_number"] == final_rule_number
            and previous_review["status"] == status
            and previous_review["reviewer"] == reviewer.strip()
            and previous_review["comment"] == comment
        ):
            raise ValueError(
                "Duplicate review detected. "
                "An identical review already exists for this rule."
            )


    reviews.append(review)

    with path.open("w", encoding="utf-8") as file:
        json.dump(reviews, file, indent=2, ensure_ascii=False)

    return review


def load_reviews(
    file_path: str = "data/reviews/review_decisions.json",
) -> list[dict[str, Any]]:
    """Load saved human review decisions from a JSON file."""

    path = Path(file_path)

    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as file:
        reviews = json.load(file)

    if not isinstance(reviews, list):
        raise ValueError("Review storage must contain a JSON list.")

    return reviews

