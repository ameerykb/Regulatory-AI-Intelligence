"""
Regulatory Rule Change Analyzer
===============================

Combines rule alignment and word-level text comparison.

Responsibilities:
    - Compare corresponding draft and final rules.
    - Prepare regulatory text before comparison.
    - Identify insertions, deletions, and replacements.
    - Preserve source rule numbers and titles.
    - Flag detected changes for human review.

Important:
    This module detects textual changes, not legal conclusions.
"""

from typing import Any
import json
from pathlib import Path

from app.change_engine.rule_aligner import validate_rule

from app.change_engine.text_differ import (
    prepare_regulatory_text,
    compare_regulatory_text,
)


def analyze_rule_change(
    draft_rule: dict[str, Any],
    final_rule: dict[str, Any],
) -> dict[str, Any]:
    """
    Analyze textual differences between two matched rules.

    Args:
        draft_rule: Parsed rule from the earlier regulation.
        final_rule: Parsed rule from the newer regulation.

    Returns:
        A structured report containing:
            - Draft and final rule numbers
            - Draft and final titles
            - Text comparison status
            - Word-level similarity
            - Individual change operations
            - Number of detected changes
            - Human review requirement

    Raises:
        TypeError: If a rule has an invalid structure.
        ValueError: If required rule information is invalid.

    Notes:
        The caller must establish that the rules are
        corresponding provisions. This function does
        not independently verify their alignment.
    """

    # Validate both parsed regulatory rules.
    validate_rule(draft_rule)
    validate_rule(final_rule)

    # Prepare text without changing stored source data.
    draft_text = prepare_regulatory_text(
        draft_rule["text"],
        draft_rule["rule_number"],
    )

    final_text = prepare_regulatory_text(
        final_rule["text"],
        final_rule["rule_number"],
    )

    # Perform word-level comparison.
    comparison = compare_regulatory_text(
        draft_text,
        final_text,
    )

    # Retain only actual change operations.
    changes = [
        operation
        for operation in comparison["operations"]
        if operation["operation"] != "equal"
    ]
            # Classify detected textual changes into additions,
    # deletions, and modifications.
    classification = classify_text_changes(changes)
    # Build a structured analysis report.
    return {
        "draft_rule_number": draft_rule["rule_number"],
        "final_rule_number": final_rule["rule_number"],
        "draft_title": draft_rule["title"],
        "final_title": final_rule["title"],
        "status": comparison["status"],
        "similarity": comparison["similarity"],
        "change_count": len(changes),
        "changes": changes,
        "change_categories": classification["category_counts"],
        "classified_changes": classification["classified_changes"],
        "review_required": comparison["review_required"],
    }
def analyze_document_changes(
    draft_rules: list[dict[str, Any]],
    final_rules: list[dict[str, Any]],
    alignment_report: dict[str, Any],
) -> dict[str, Any]:
    """
    Analyze textual changes across aligned regulatory rules.

    Only high-confidence, one-to-one candidate alignments
    are automatically compared.

    Medium-confidence, low-confidence, and possible-split
    alignments are placed in a manual review queue.

    Args:
        draft_rules: Parsed draft regulatory rules.
        final_rules: Parsed final regulatory rules.
        alignment_report: Output from align_documents().

    Returns:
        A document-level report containing:
            - Analyzed rule pairs
            - Rules awaiting alignment review
            - Counts of analyzed and modified pairs

    Raises:
        TypeError: If inputs have invalid structures.
        ValueError: If alignment references are invalid.

    Important:
        High confidence is a heuristic classification,
        not confirmation that two rules are legally equivalent.
    """
    from app.change_engine.document_aligner import (
        validate_rule_collection,
        find_alignment_conflicts,
    )

    validate_rule_collection(draft_rules)
    validate_rule_collection(final_rules)

    if not isinstance(alignment_report, dict):
        raise TypeError("Alignment report must be a dictionary.")

    alignments = alignment_report.get("alignments")

    if not isinstance(alignments, list):
        raise TypeError("Alignment report must contain an alignments list.")

    # Index source rules for efficient lookup.
    draft_lookup = {
        rule["rule_number"]: rule
        for rule in draft_rules
    }

    final_lookup = {
        rule["rule_number"]: rule
        for rule in final_rules
    }

    analyzed_rules = []
    pending_review = []
    seen_draft_numbers = set()
        # Detect duplicate top-candidate assignments before
    # automatically comparing any rule pairs.
    conflicts = find_alignment_conflicts(alignments)

    # Collect draft rules involved in conflicts.
    conflicting_draft_numbers = {
        draft_number
        for conflict in conflicts
        for draft_number in conflict["draft_rule_numbers"]
    }

    for alignment in alignments:
        if not isinstance(alignment, dict):
            raise TypeError("Each alignment must be a dictionary.")

        draft_number = alignment.get("draft_rule_number")

        if draft_number not in draft_lookup:
            raise ValueError(
                f"Unknown draft rule number: {draft_number}"
            )

        if draft_number in seen_draft_numbers:
            raise ValueError(
                f"Duplicate draft alignment: {draft_number}"
            )

        seen_draft_numbers.add(draft_number)
                # Never automatically compare a rule involved in
        # a duplicate top-candidate assignment.
        if draft_number in conflicting_draft_numbers:
            pending_review.append({
                "draft_rule_number": draft_number,
                "reason": "Conflicting final-rule assignment",
                "relationship": alignment.get("relationship"),
                "confidence_level": alignment.get("confidence_level"),
            })
            continue

        candidates = alignment.get("candidates", [])

        # Only analyze high-confidence one-to-one candidates.
        eligible = (
            alignment.get("confidence_level") == "high"
            and alignment.get("relationship") == "possible_one_to_one"
            and isinstance(candidates, list)
            and len(candidates) > 0
        )

        if not eligible:
            pending_review.append({
                "draft_rule_number": draft_number,
                "reason": "Alignment requires manual review",
                "relationship": alignment.get("relationship"),
                "confidence_level": alignment.get("confidence_level"),
            })
            continue

        best_candidate = candidates[0]

        if not isinstance(best_candidate, dict):
            raise TypeError("Alignment candidate must be a dictionary.")

        final_number = best_candidate.get("final_rule_number")

        if final_number not in final_lookup:
            raise ValueError(
                f"Unknown final rule number: {final_number}"
            )

        # Analyze the wording of the candidate rule pair.
        result = analyze_rule_change(
            draft_lookup[draft_number],
            final_lookup[final_number],
        )

        # Retain alignment evidence alongside the comparison.
        result["alignment_confidence"] = alignment["confidence_level"]
        result["alignment_relationship"] = alignment["relationship"]
        result["alignment_similarity"] = best_candidate.get(
            "combined_similarity"
        )

        # These remain candidate matches requiring human review.
        result["review_required"] = True

        analyzed_rules.append(result)

    modified_count = sum(
        result["status"] == "modified"
        for result in analyzed_rules
    )

    return {
        "draft_rule_count": len(draft_rules),
        "final_rule_count": len(final_rules),
        "analyzed_rule_count": len(analyzed_rules),
        "modified_rule_count": modified_count,
        "pending_review_count": len(pending_review),
        "analyzed_rules": analyzed_rules,
        "pending_review": pending_review,
        "alignment_conflicts": conflicts,
    }

def save_change_analysis(
    report: dict[str, Any],
    output_path: str | Path,
) -> Path:
    """
    Save a regulatory change analysis report as JSON.

    Responsibilities:
        - Validate the analysis report.
        - Create the output directory when necessary.
        - Serialize the report using UTF-8.
        - Preserve Unicode regulatory wording.
        - Return the saved file path.

    Args:
        report: Structured document change analysis.
        output_path: Destination JSON file path.

    Returns:
        Path pointing to the saved JSON report.

    Raises:
        TypeError: If the report or path has an invalid type.
        ValueError: If the report or path is empty.
        OSError: If the report cannot be written.

    Notes:
        This function saves analysis results only.
        It does not alter the original regulatory PDFs.
    """

    # Validate the report structure.
    if not isinstance(report, dict):
        raise TypeError("Analysis report must be a dictionary.")

    if not report:
        raise ValueError("Analysis report cannot be empty.")

    # Validate the output path.
    if not isinstance(output_path, (str, Path)):
        raise TypeError("Output path must be a string or Path.")

    if isinstance(output_path, str) and not output_path.strip():
        raise ValueError("Output path cannot be empty.")

    destination = Path(output_path)

    # Create the destination folder if it does not exist.
    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Save Unicode text without converting it to escape sequences.
    with destination.open("w", encoding="utf-8") as file:
        json.dump(
            report,
            file,
            indent=2,
            ensure_ascii=False,
        )

    return destination

def classify_text_changes(
    changes: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Classify detected regulatory wording changes.

    Maps word-level comparison operations into:
        - addition
        - deletion
        - modification

    Args:
        changes: Change operations produced by
            compare_regulatory_text() or analyze_rule_change().

    Returns:
        A dictionary containing classified changes,
        category counts, and total changes.

    Raises:
        TypeError: If the input or its entries are invalid.
        ValueError: If an operation is unsupported.

    Notes:
        Classifications describe textual changes only.
        They do not establish legal significance.
    """
    if not isinstance(changes, list):
        raise TypeError("Changes must be a list.")

    operation_categories = {
        "insert": "addition",
        "delete": "deletion",
        "replace": "modification",
    }

    classified_changes = []
    counts = {
        "addition": 0,
        "deletion": 0,
        "modification": 0,
    }

    for index, change in enumerate(changes, start=1):
        if not isinstance(change, dict):
            raise TypeError("Each change must be a dictionary.")

        operation = change.get("operation")

        if operation not in operation_categories:
            raise ValueError(
                f"Unsupported change operation: {operation}"
            )

        category = operation_categories[operation]
        counts[category] += 1

        classified_changes.append({
            "change_id": index,
            "category": category,
            "operation": operation,
            "draft_text": change.get("draft_text", ""),
            "final_text": change.get("final_text", ""),
            "draft_word_range": change.get("draft_word_range"),
            "final_word_range": change.get("final_word_range"),
            "review_required": True,
        })

    return {
        "total_changes": len(classified_changes),
        "category_counts": counts,
        "classified_changes": classified_changes,
    }