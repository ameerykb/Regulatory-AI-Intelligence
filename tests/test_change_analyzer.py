"""
Tests for the Regulatory Rule Change Analyzer.

Verifies:
    - Identical regulatory provisions
    - Word replacements
    - Inserted wording
    - Deleted wording
    - Rule renumbering
    - Invalid input handling
    - Preservation of source data

Run:
    python -m pytest tests/test_change_analyzer.py -v
"""

from copy import deepcopy
import json
from pathlib import Path 

import pytest

from app.change_engine.change_analyzer import(
analyze_rule_change,
analyze_document_changes,
save_change_analysis,
classify_text_changes,
)


def make_rule(
    number: int,
    text: str,
    title: str = "Data Protection",
) -> dict:
    """
    Create a valid sample regulatory rule for testing.
    """
    return {
        "section_id": f"rule_{number}",
        "rule_number": number,
        "title": title,
        "text": text,
    }


def test_identical_rules():
    """Identical provisions should have no changes."""
    draft = make_rule(1, "1. Organizations must protect data.")
    final = make_rule(1, "1. Organizations must protect data.")

    result = analyze_rule_change(draft, final)

    assert result["status"] == "unchanged"
    assert result["similarity"] == 1.0
    assert result["change_count"] == 0
    assert result["changes"] == []
    assert result["review_required"] is False


def test_replaced_word():
    """A changed deadline should be identified."""
    draft = make_rule(1, "1. Notify users within 72 hours.")
    final = make_rule(1, "1. Notify users within 24 hours.")

    result = analyze_rule_change(draft, final)

    assert result["status"] == "modified"
    assert result["change_count"] == 1
    assert result["changes"][0]["operation"] == "replace"
    assert result["changes"][0]["draft_text"] == "72"
    assert result["changes"][0]["final_text"] == "24"


def test_inserted_word():
    """New wording should be identified."""
    draft = make_rule(1, "1. Organizations must notify users.")
    final = make_rule(
        1,
        "1. Organizations must immediately notify users.",
    )

    result = analyze_rule_change(draft, final)

    assert result["change_count"] == 1
    assert result["changes"][0]["operation"] == "insert"
    assert result["changes"][0]["final_text"] == "immediately"


def test_deleted_word():
    """Removed wording should be identified."""
    draft = make_rule(
        1,
        "1. Organizations must immediately notify users.",
    )
    final = make_rule(1, "1. Organizations must notify users.")

    result = analyze_rule_change(draft, final)

    assert result["change_count"] == 1
    assert result["changes"][0]["operation"] == "delete"
    assert result["changes"][0]["draft_text"] == "immediately"


def test_rule_renumbering():
    """Renumbering alone should not count as a text change."""
    draft = make_rule(13, "13. Organizations must protect data.")
    final = make_rule(14, "14. Organizations must protect data.")

    result = analyze_rule_change(draft, final)

    assert result["draft_rule_number"] == 13
    assert result["final_rule_number"] == 14
    assert result["status"] == "unchanged"
    assert result["change_count"] == 0


def test_preserves_source_rules():
    """Analysis must not modify original parsed data."""
    draft = make_rule(1, "1. Notify users within 72 hours.")
    final = make_rule(1, "1. Notify users within 24 hours.")

    original_draft = deepcopy(draft)
    original_final = deepcopy(final)

    analyze_rule_change(draft, final)

    assert draft == original_draft
    assert final == original_final


def test_invalid_draft_rule():
    """Invalid draft rule input should be rejected."""
    final = make_rule(1, "1. Protect personal data.")

    with pytest.raises((TypeError, ValueError)):
        analyze_rule_change(None, final)


def test_invalid_final_rule():
    """Invalid final rule input should be rejected."""
    draft = make_rule(1, "1. Protect personal data.")

    with pytest.raises((TypeError, ValueError)):
        analyze_rule_change(draft, None)

def make_alignment(
    draft_number: int,
    final_number: int,
    confidence: str = "high",
    relationship: str = "possible_one_to_one",
) -> dict:
    """
    Create a sample alignment for document-level testing.

    The candidate represents a possible correspondence,
    not a legally verified match.
    """
    return {
        "draft_rule_number": draft_number,
        "confidence_level": confidence,
        "relationship": relationship,
        "candidates": [
            {
                "final_rule_number": final_number,
                "combined_similarity": 0.95,
            }
        ],
    }


def test_document_analysis_without_conflicts():
    """Distinct candidate assignments should be analyzed."""
    draft_rules = [
        make_rule(1, "1. Notify users within 72 hours."),
        make_rule(2, "2. Protect personal data."),
    ]

    final_rules = [
        make_rule(1, "1. Notify users within 24 hours."),
        make_rule(2, "2. Protect personal data."),
    ]

    alignment_report = {
        "alignments": [
            make_alignment(1, 1),
            make_alignment(2, 2),
        ]
    }

    result = analyze_document_changes(
        draft_rules,
        final_rules,
        alignment_report,
    )

    assert result["analyzed_rule_count"] == 2
    assert result["modified_rule_count"] == 1
    assert result["pending_review_count"] == 0
    assert result["alignment_conflicts"] == []


def test_conflicting_assignments_require_review():
    """Two draft rules targeting one final rule must be flagged."""
    draft_rules = [
        make_rule(1, "1. Notify users."),
        make_rule(2, "2. Notify users immediately."),
    ]

    final_rules = [
        make_rule(1, "1. Notify users promptly."),
    ]

    alignment_report = {
        "alignments": [
            make_alignment(1, 1),
            make_alignment(2, 1),
        ]
    }

    result = analyze_document_changes(
        draft_rules,
        final_rules,
        alignment_report,
    )

    assert result["analyzed_rule_count"] == 0
    assert result["pending_review_count"] == 2
    assert len(result["alignment_conflicts"]) == 1

    assert all(
        item["reason"] == "Conflicting final-rule assignment"
        for item in result["pending_review"]
    )


def test_uncertain_alignment_requires_review():
    """Low-confidence candidate matches must not be auto-analyzed."""
    draft_rules = [
        make_rule(1, "1. Notify users."),
    ]

    final_rules = [
        make_rule(1, "1. Notify users promptly."),
    ]

    alignment_report = {
        "alignments": [
            make_alignment(
                1,
                1,
                confidence="low",
                relationship="uncertain",
            )
        ]
    }

    result = analyze_document_changes(
        draft_rules,
        final_rules,
        alignment_report,
    )

    assert result["analyzed_rule_count"] == 0
    assert result["pending_review_count"] == 1
    assert result["alignment_conflicts"] == []


def test_analyzed_candidates_still_require_human_review():
    """High-confidence comparisons are not confirmed legal matches."""
    draft_rules = [
        make_rule(1, "1. Notify users within 72 hours."),
    ]

    final_rules = [
        make_rule(1, "1. Notify users within 24 hours."),
    ]

    alignment_report = {
        "alignments": [
            make_alignment(1, 1),
        ]
    }

    result = analyze_document_changes(
        draft_rules,
        final_rules,
        alignment_report,
    )

    assert result["analyzed_rule_count"] == 1
    assert result["analyzed_rules"][0]["review_required"] is True
    assert result["analyzed_rules"][0]["alignment_confidence"] == "high"

def test_save_change_analysis(tmp_path):
    """
    Verify that a valid analysis report is saved
    and can be loaded without losing information.
    """
    report = {
        "draft_rule_count": 22,
        "final_rule_count": 23,
        "analyzed_rule_count": 17,
        "modified_rule_count": 17,
    }

    output_path = tmp_path / "change_analysis.json"

    saved_path = save_change_analysis(
        report,
        output_path,
    )

    assert saved_path == output_path
    assert output_path.exists()

    with output_path.open("r", encoding="utf-8") as file:
        loaded_report = json.load(file)

    assert loaded_report == report


def test_save_change_analysis_creates_directory(tmp_path):
    """
    Verify that missing output directories are
    created automatically.
    """
    report = {"analyzed_rule_count": 1}

    output_path = (
        tmp_path
        / "reports"
        / "regulatory"
        / "analysis.json"
    )

    save_change_analysis(report, output_path)

    assert output_path.exists()
    assert output_path.parent.is_dir()


def test_save_change_analysis_preserves_unicode(tmp_path):
    """
    Verify that regulatory text containing Unicode
    characters is preserved in the JSON file.
    """
    report = {
        "regulation": "Digital Personal Data Protection",
        "hindi_text": "\u092d\u093e\u0930\u0924",
        "change": "72 hours \u2192 24 hours",
    }

    output_path = tmp_path / "unicode_analysis.json"

    save_change_analysis(report, output_path)

    with output_path.open("r", encoding="utf-8") as file:
        loaded_report = json.load(file)

    assert loaded_report == report

    # Ensure Unicode is written directly rather than
    # serialized entirely as ASCII escape sequences.
    raw_content = output_path.read_text(encoding="utf-8")

    assert "\u092d\u093e\u0930\u0924" in raw_content


def test_save_change_analysis_rejects_empty_report(tmp_path):
    """An empty analysis report must be rejected."""
    with pytest.raises(ValueError, match="cannot be empty"):
        save_change_analysis(
            {},
            tmp_path / "analysis.json",
        )


def test_save_change_analysis_rejects_invalid_report(tmp_path):
    """The report must be a dictionary."""
    with pytest.raises(TypeError, match="must be a dictionary"):
        save_change_analysis(
            ["invalid", "report"],
            tmp_path / "analysis.json",
        )


def test_save_change_analysis_rejects_empty_path():
    """An empty output path must be rejected."""
    with pytest.raises(ValueError, match="cannot be empty"):
        save_change_analysis(
            {"analyzed_rule_count": 1},
            "",
        )

def test_classify_addition():
    """Inserted wording should be classified as an addition."""
    changes = [
        {
            "operation": "insert",
            "draft_text": "",
            "final_text": "within ninety days",
            "draft_word_range": [4, 4],
            "final_word_range": [4, 7],
        }
    ]

    result = classify_text_changes(changes)

    assert result["total_changes"] == 1
    assert result["category_counts"]["addition"] == 1
    assert result["classified_changes"][0]["category"] == "addition"
    assert result["classified_changes"][0]["review_required"] is True


def test_classify_deletion():
    """Deleted wording should be classified as a deletion."""
    changes = [
        {
            "operation": "delete",
            "draft_text": "immediately",
            "final_text": "",
            "draft_word_range": [2, 3],
            "final_word_range": [2, 2],
        }
    ]

    result = classify_text_changes(changes)

    assert result["category_counts"]["deletion"] == 1
    assert result["classified_changes"][0]["category"] == "deletion"


def test_classify_modification():
    """Replaced wording should be classified as a modification."""
    changes = [
        {
            "operation": "replace",
            "draft_text": "72 hours",
            "final_text": "24 hours",
            "draft_word_range": [3, 5],
            "final_word_range": [3, 5],
        }
    ]

    result = classify_text_changes(changes)

    assert result["category_counts"]["modification"] == 1
    assert result["classified_changes"][0]["category"] == "modification"


def test_classify_mixed_changes():
    """Different operation types should be counted correctly."""
    changes = [
        {
            "operation": "insert",
            "draft_text": "",
            "final_text": "prominently",
        },
        {
            "operation": "replace",
            "draft_text": "published",
            "final_text": "required",
        },
        {
            "operation": "delete",
            "draft_text": "immediately",
            "final_text": "",
        },
    ]

    result = classify_text_changes(changes)

    assert result["total_changes"] == 3
    assert result["category_counts"] == {
        "addition": 1,
        "deletion": 1,
        "modification": 1,
    }

    assert [
        change["change_id"]
        for change in result["classified_changes"]
    ] == [1, 2, 3]


def test_classify_rejects_unsupported_operation():
    """Unsupported operations must raise an error."""
    changes = [
        {
            "operation": "unknown",
            "draft_text": "old",
            "final_text": "new",
        }
    ]

    with pytest.raises(ValueError, match="Unsupported change operation"):
        classify_text_changes(changes)