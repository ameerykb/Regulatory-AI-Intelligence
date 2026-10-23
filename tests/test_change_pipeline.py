"""
End-to-end tests for the regulatory change analysis pipeline.

These tests verify that:
1. Draft and final rules can be aligned.
2. Aligned rules can be compared.
3. Text changes are classified.
4. Results can be saved and loaded as JSON.

All test data is fictional and used only for testing.
"""

import json

from app.change_engine.document_aligner import align_documents
from app.change_engine.change_analyzer import (
    analyze_document_changes,
    save_change_analysis,
)


def make_test_rules():
    """
    Create a small fictional regulatory dataset.

    The final regulation contains a changed deadline
    and an additional reporting requirement.
    """

    draft_rules = [
        {
            "section_id": "rule_1",
            "rule_number": 1,
            "title": "Notification Requirements",
            "text": (
                "1. Notification Requirements. "
                "Organizations must notify affected individuals "
                "within 72 hours."
            ),
        },
        {
            "section_id": "rule_2",
            "rule_number": 2,
            "title": "Record Maintenance",
            "text": (
                "2. Record Maintenance. "
                "Organizations must maintain accurate records."
            ),
        },
    ]

    final_rules = [
        {
            "section_id": "rule_1",
            "rule_number": 1,
            "title": "Notification Requirements",
            "text": (
                "1. Notification Requirements. "
                "Organizations must notify affected individuals "
                "within 24 hours."
            ),
        },
        {
            "section_id": "rule_2",
            "rule_number": 2,
            "title": "Record Maintenance",
            "text": (
                "2. Record Maintenance. "
                "Organizations must maintain accurate records."
            ),
        },
    ]

    return draft_rules, final_rules


def test_complete_regulatory_pipeline(tmp_path):
    """
    Verify alignment, analysis, classification,
    JSON saving, and JSON loading work together.
    """

    # Step 1: Prepare fictional regulations.
    draft_rules, final_rules = make_test_rules()

    # Step 2: Align draft and final rules.
    alignment_report = align_documents(
        draft_rules,
        final_rules,
    )

    assert isinstance(alignment_report, dict)
    assert "alignments" in alignment_report

    # Step 3: Analyze aligned rules.
    analysis = analyze_document_changes(
        draft_rules,
        final_rules,
        alignment_report,
    )

    assert analysis["draft_rule_count"] == 2
    assert analysis["final_rule_count"] == 2

    # Step 4: Confirm at least one rule was analyzed.
    assert analysis["analyzed_rule_count"] >= 1

    # Step 5: Verify classified changes are consistent.
    for rule in analysis["analyzed_rules"]:
        assert "change_categories" in rule
        assert "classified_changes" in rule

        category_total = sum(
            rule["change_categories"].values()
        )

        assert category_total == rule["change_count"]

    # Step 6: Save the complete analysis.
    output_path = tmp_path / "regulatory_analysis.json"

    saved_path = save_change_analysis(
        analysis,
        output_path,
    )

    assert saved_path.exists()

    # Step 7: Reload the JSON and verify its contents.
    with saved_path.open("r", encoding="utf-8") as file:
        loaded_report = json.load(file)

    assert loaded_report == analysis


def test_pipeline_preserves_review_requirements():
    """
    Ensure automatically aligned regulatory rules
    remain subject to human review.
    """

    draft_rules, final_rules = make_test_rules()

    alignment_report = align_documents(
        draft_rules,
        final_rules,
    )

    analysis = analyze_document_changes(
        draft_rules,
        final_rules,
        alignment_report,
    )

    # Analyzed legal changes must not be treated
    # as automatically approved.
    for rule in analysis["analyzed_rules"]:
        assert rule["review_required"] is True


def test_pipeline_preserves_change_classification():
    """
    Ensure changes are classified consistently
    across the document-level analysis.
    """

    draft_rules, final_rules = make_test_rules()

    alignment_report = align_documents(
        draft_rules,
        final_rules,
    )

    analysis = analyze_document_changes(
        draft_rules,
        final_rules,
        alignment_report,
    )

    for rule in analysis["analyzed_rules"]:
        categories = rule["change_categories"]

        assert set(categories) == {
            "addition",
            "deletion",
            "modification",
        }

        assert sum(categories.values()) == rule["change_count"]