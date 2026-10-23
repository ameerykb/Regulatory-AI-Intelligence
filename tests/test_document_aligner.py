"""
Unit Tests for Document Alignment
=================================

Tests validation of regulatory rule collections.

Run:
    python -m pytest tests/test_document_aligner.py -v
"""

import pytest
import json

from app.change_engine.document_aligner import (
    validate_rule_collection,
    align_documents,
    assess_alignment_confidence,
    find_unmatched_final_rules,
    find_unmatched_draft_rules,
    save_alignment_report,
)


def make_rule(number: int) -> dict:
    """
    Create a valid sample regulatory rule.

    Args:
        number: The rule number.

    Returns:
        A rule dictionary matching the parser's structure.
    """
    return {
        "section_id": f"en_rule_{number}",
        "rule_number": number,
        "title": f"Regulatory Rule {number}",
        "text": f"{number}. This is a regulatory provision.",
    }


def test_valid_rule_collection():
    """Verify that a valid collection is accepted."""
    rules = [make_rule(1), make_rule(2)]

    validate_rule_collection(rules)


def test_empty_rule_collection():
    """Verify that an empty collection is rejected."""
    with pytest.raises(ValueError, match="cannot be empty"):
        validate_rule_collection([])


def test_invalid_collection_type():
    """Verify that a non-list collection is rejected."""
    with pytest.raises(TypeError):
        validate_rule_collection("not a list")


def test_duplicate_rule_number():
    """Verify that duplicate rule numbers are rejected."""
    first = make_rule(1)
    second = make_rule(2)
    second["rule_number"] = 1

    with pytest.raises(ValueError, match="Duplicate rule number"):
        validate_rule_collection([first, second])


def test_duplicate_section_id():
    """Verify that duplicate section IDs are rejected."""
    first = make_rule(1)
    second = make_rule(2)
    second["section_id"] = "en_rule_1"

    with pytest.raises(ValueError, match="Duplicate section ID"):
        validate_rule_collection([first, second])


def test_invalid_rule_structure():
    """Verify that invalid rules are rejected."""
    invalid_rule = make_rule(1)
    del invalid_rule["title"]

    with pytest.raises(ValueError, match="Invalid rule at index"):
        validate_rule_collection([invalid_rule])

def test_align_documents_counts():
    """
    Verify that alignment reports the correct number
    of rules, comparisons, and alignment records.
    """
    draft_rules = [make_rule(1), make_rule(2)]
    final_rules = [
        make_rule(1),
        make_rule(2),
        make_rule(3),
    ]

    result = align_documents(
        draft_rules,
        final_rules,
        top_k=2,
    )

    assert result["draft_rule_count"] == 2
    assert result["final_rule_count"] == 3
    assert result["comparisons_performed"] == 6
    assert len(result["alignments"]) == 2


def test_align_documents_renumbered_rule():
    """
    Verify that a corresponding rule can be found
    even when its rule number changes.
    """
    draft_rule = make_rule(1)

    final_rule = make_rule(2)
    final_rule["title"] = draft_rule["title"]
    final_rule["text"] = draft_rule["text"]

    result = align_documents(
        [draft_rule],
        [final_rule],
    )

    alignment = result["alignments"][0]
    best_match = alignment["candidates"][0]

    assert best_match["final_rule_number"] == 2
    assert best_match["combined_similarity"] == 1.0


def test_align_documents_candidate_limit():
    """
    Verify that top_k limits retained candidates
    without changing the comparison count.
    """
    result = align_documents(
        [make_rule(1)],
        [make_rule(1), make_rule(2), make_rule(3)],
        top_k=2,
    )

    assert len(result["alignments"][0]["candidates"]) == 2
    assert result["comparisons_performed"] == 3


def test_align_documents_review_required():
    """
    Verify that candidate matches remain subject
    to review rather than being automatically confirmed.
    """
    result = align_documents(
        [make_rule(1)],
        [make_rule(1)],
    )

    assert result["alignments"][0]["review_required"] is True


def test_align_documents_invalid_top_k():
    """
    Verify that invalid candidate limits are rejected.
    """
    with pytest.raises(ValueError):
        align_documents(
            [make_rule(1)],
            [make_rule(1)],
            top_k=0,
        )


def test_align_documents_invalid_collection():
    """
    Verify that an empty draft collection is rejected.
    """
    with pytest.raises(ValueError):
        align_documents(
            [],
            [make_rule(1)],
        )

def make_candidate(
    rule_number: int,
    similarity: float,
) -> dict:
    """
    Create a sample alignment candidate for testing.

    Args:
        rule_number: Candidate final rule number.
        similarity: Combined similarity score.

    Returns:
        A candidate dictionary containing the fields
        required by the confidence assessment engine.
    """
    return {
        "final_rule_number": rule_number,
        "combined_similarity": similarity,
    }


def test_high_confidence_alignment():
    """A strong, unambiguous match receives high confidence."""
    candidates = [
        make_candidate(14, 0.9631),
        make_candidate(3, 0.3495),
    ]

    result = assess_alignment_confidence(candidates)

    assert result["confidence_level"] == "high"
    assert result["relationship"] == "possible_one_to_one"
    assert result["candidate_rule_numbers"] == [14]
    assert result["review_required"] is True


def test_possible_split_alignment():
    """Two substantial candidates trigger possible split detection."""
    candidates = [
        make_candidate(10, 0.7036),
        make_candidate(11, 0.6537),
        make_candidate(12, 0.2910),
    ]

    result = assess_alignment_confidence(candidates)

    assert result["confidence_level"] == "medium"
    assert result["relationship"] == "possible_split"
    assert result["candidate_rule_numbers"] == [10, 11]


def test_low_confidence_alignment():
    """A weak best candidate is classified as uncertain."""
    candidates = [
        make_candidate(2, 0.5895),
        make_candidate(1, 0.2704),
    ]

    result = assess_alignment_confidence(candidates)

    assert result["confidence_level"] == "low"
    assert result["relationship"] == "uncertain"
    assert result["candidate_rule_numbers"] == [2]


def test_empty_candidate_collection():
    """No candidates should produce an uncertain assessment."""
    result = assess_alignment_confidence([])

    assert result["confidence_level"] == "low"
    assert result["relationship"] == "uncertain"
    assert result["candidate_rule_numbers"] == []
    assert result["review_required"] is True


def test_unsorted_candidates():
    """Confidence assessment should rank candidates by score."""
    candidates = [
        make_candidate(3, 0.20),
        make_candidate(14, 0.95),
        make_candidate(7, 0.35),
    ]

    result = assess_alignment_confidence(candidates)

    assert result["confidence_level"] == "high"
    assert result["candidate_rule_numbers"] == [14]


def test_invalid_similarity_score():
    """Similarity scores outside the valid range are rejected."""
    candidates = [make_candidate(1, 1.5)]

    with pytest.raises(ValueError, match="Invalid candidate similarity"):
        assess_alignment_confidence(candidates)


def test_invalid_threshold_order():
    """The split threshold must be below the strong threshold."""
    candidates = [make_candidate(1, 0.90)]

    with pytest.raises(ValueError, match="split_threshold"):
        assess_alignment_confidence(
            candidates,
            strong_threshold=0.60,
            split_threshold=0.80,
        )


def test_invalid_candidate_structure():
    """Missing candidate fields should produce a validation error."""
    candidates = [{"final_rule_number": 1}]

    with pytest.raises(ValueError, match="missing required fields"):
        assess_alignment_confidence(candidates)

def test_alignment_includes_confidence_fields():
    """
    Verify that document alignment automatically includes
    confidence, relationship, and human-review information.
    """
    result = align_documents(
        [make_rule(1)],
        [make_rule(1)],
    )

    alignment = result["alignments"][0]

    assert alignment["confidence_level"] == "high"
    assert alignment["relationship"] == "possible_one_to_one"
    assert alignment["candidate_rule_numbers"] == [1]
    assert alignment["review_required"] is True


def test_alignment_detects_possible_split():
    """
    Verify that multiple substantially similar final rules
    are flagged as a possible split during document alignment.
    """
    draft_rule = make_rule(1)

    final_rule_1 = make_rule(1)
    final_rule_2 = make_rule(2)

    # Both final rules use the same title and text as the
    # draft rule, creating two equally strong candidates.
    final_rule_2["title"] = draft_rule["title"]
    final_rule_2["text"] = draft_rule["text"]

    result = align_documents(
        [draft_rule],
        [final_rule_1, final_rule_2],
        top_k=2,
    )

    alignment = result["alignments"][0]

    assert alignment["confidence_level"] == "medium"
    assert alignment["relationship"] == "possible_split"
    assert set(alignment["candidate_rule_numbers"]) == {1, 2}
    assert alignment["review_required"] is True


def test_alignment_flags_uncertain_match():
    """
    Verify that a low-similarity candidate is flagged
    as uncertain by the complete alignment workflow.
    """
    draft_rule = make_rule(1)
    final_rule = make_rule(2)

    draft_rule["title"] = "Children's data protection"
    draft_rule["text"] = "Consent requirements for children."

    final_rule["title"] = "Financial reporting requirements"
    final_rule["text"] = "Quarterly financial statements."

    result = align_documents(
        [draft_rule],
        [final_rule],
    )

    alignment = result["alignments"][0]

    assert alignment["confidence_level"] == "low"
    assert alignment["relationship"] == "uncertain"
    assert alignment["candidate_rule_numbers"] == [2]
    assert alignment["review_required"] is True

def test_no_unmatched_final_rules():
    """All final rules are covered by alignment results."""
    final_rules = [make_rule(1), make_rule(2)]

    alignments = [
        {"candidate_rule_numbers": [1]},
        {"candidate_rule_numbers": [2]},
    ]

    result = find_unmatched_final_rules(final_rules, alignments)

    assert result == []


def test_detect_unmatched_final_rule():
    """An uncovered final rule is flagged as a potential addition."""
    final_rules = [
        make_rule(1),
        make_rule(2),
        make_rule(3),
    ]

    alignments = [
        {"candidate_rule_numbers": [1]},
        {"candidate_rule_numbers": [2]},
    ]

    result = find_unmatched_final_rules(final_rules, alignments)

    assert len(result) == 1
    assert result[0]["final_rule_number"] == 3
    assert result[0]["status"] == "potential_addition"
    assert result[0]["review_required"] is True


def test_possible_split_covers_multiple_final_rules():
    """A possible split covers multiple final rules."""
    final_rules = [make_rule(10), make_rule(11)]

    alignments = [
        {"candidate_rule_numbers": [10, 11]},
    ]

    result = find_unmatched_final_rules(final_rules, alignments)

    assert result == []


def test_empty_alignments():
    """Without alignments, all final rules are potentially unmatched."""
    final_rules = [make_rule(1), make_rule(2)]

    result = find_unmatched_final_rules(final_rules, [])

    assert len(result) == 2
    assert all(
        rule["status"] == "potential_addition"
        for rule in result
    )


def test_invalid_alignment_candidate_numbers():
    """Invalid candidate rule numbers raise an error."""
    final_rules = [make_rule(1)]

    alignments = [
        {"candidate_rule_numbers": ["invalid"]},
    ]

    with pytest.raises(
        ValueError,
        match="Invalid final rule number",
    ):
        find_unmatched_final_rules(final_rules, alignments)
def test_alignment_reports_no_potential_additions():
    """
    Verify that fully covered final rules produce
    an empty unmatched-rule list.
    """
    draft_rules = [make_rule(1), make_rule(2)]
    final_rules = [make_rule(1), make_rule(2)]

    result = align_documents(draft_rules, final_rules)

    assert result["potential_addition_count"] == 0
    assert result["unmatched_final_rules"] == []


def test_alignment_reports_potential_addition():
    """
    Verify that a substantially different final rule
    is flagged as a potential addition.
    """
    draft_rule = make_rule(1)

    final_rule_1 = make_rule(1)
    final_rule_2 = make_rule(2)

    # Give the second final rule unrelated content
    # to prevent it from being treated as a strong match.
    final_rule_2["title"] = "Financial audit requirements"
    final_rule_2["text"] = (
        "Independent financial audits are required annually."
    )

    result = align_documents(
        [draft_rule],
        [final_rule_1, final_rule_2],
    )

    assert result["potential_addition_count"] == 1
    assert result["unmatched_final_rules"][0][
        "final_rule_number"
    ] == 2
    assert result["unmatched_final_rules"][0][
        "review_required"
    ] is True


def test_alignment_possible_split_has_no_additions():
    """
    Verify that a possible split covering two final
    rules does not create a false addition flag.
    """
    draft_rule = make_rule(1)

    final_rule_1 = make_rule(1)
    final_rule_2 = make_rule(2)

    final_rule_2["title"] = draft_rule["title"]
    final_rule_2["text"] = draft_rule["text"]

    result = align_documents(
        [draft_rule],
        [final_rule_1, final_rule_2],
    )

    assert result["potential_addition_count"] == 0
    assert result["unmatched_final_rules"] == []

def test_no_unmatched_draft_rules():
    """
    Verify that draft rules with acceptable candidate
    relationships are not flagged as removals.
    """
    draft_rules = [make_rule(1), make_rule(2)]

    alignments = [
        {
            "draft_rule_number": 1,
            "relationship": "possible_one_to_one",
        },
        {
            "draft_rule_number": 2,
            "relationship": "possible_split",
        },
    ]

    result = find_unmatched_draft_rules(
        draft_rules,
        alignments,
    )

    assert result == []


def test_detect_potential_draft_removal():
    """
    Verify that an uncertain draft rule is flagged
    for further review.
    """
    draft_rules = [make_rule(1), make_rule(2)]

    alignments = [
        {
            "draft_rule_number": 1,
            "relationship": "possible_one_to_one",
        },
        {
            "draft_rule_number": 2,
            "relationship": "uncertain",
        },
    ]

    result = find_unmatched_draft_rules(
        draft_rules,
        alignments,
    )

    assert len(result) == 1
    assert result[0]["draft_rule_number"] == 2
    assert result[0]["status"] == "potential_removal"
    assert result[0]["review_required"] is True


def test_empty_draft_alignments():
    """
    Verify that all draft rules are flagged when
    no alignment results exist.
    """
    draft_rules = [make_rule(1), make_rule(2)]

    result = find_unmatched_draft_rules(
        draft_rules,
        [],
    )

    assert len(result) == 2


def test_invalid_draft_alignment_relationship():
    """
    Verify that an unsupported relationship
    raises a validation error.
    """
    draft_rules = [make_rule(1)]

    alignments = [
        {
            "draft_rule_number": 1,
            "relationship": "confirmed_removed",
        },
    ]

    with pytest.raises(ValueError, match="Invalid relationship"):
        find_unmatched_draft_rules(
            draft_rules,
            alignments,
        )


def test_invalid_draft_alignment_number():
    """
    Verify that invalid draft rule numbers
    are rejected.
    """
    draft_rules = [make_rule(1)]

    alignments = [
        {
            "draft_rule_number": "invalid",
            "relationship": "uncertain",
        },
    ]

    with pytest.raises(ValueError, match="Invalid draft rule number"):
        find_unmatched_draft_rules(
            draft_rules,
            alignments,
        )

def test_alignment_report_includes_removal_fields():
    """
    Verify that the document-level report contains
    potential removal information.
    """
    result = align_documents(
        [make_rule(1)],
        [make_rule(1)],
    )

    assert "unmatched_draft_rules" in result
    assert "potential_removal_count" in result
    assert result["potential_removal_count"] == 0
    assert result["unmatched_draft_rules"] == []


def test_alignment_report_detects_potential_removal():
    """
    Verify that an uncertain rule relationship appears
    in the document-level potential removal report.
    """
    draft_rule = make_rule(1)
    final_rule = make_rule(2)

    draft_rule["title"] = "Children's data protection"
    draft_rule["text"] = "Consent requirements for children."

    final_rule["title"] = "Financial reporting requirements"
    final_rule["text"] = "Quarterly financial statements."

    result = align_documents(
        [draft_rule],
        [final_rule],
    )

    assert result["potential_removal_count"] == 1
    assert result["unmatched_draft_rules"][0][
        "draft_rule_number"
    ] == 1
    assert result["unmatched_draft_rules"][0][
        "review_required"
    ] is True


def test_alignment_report_removal_count_consistency():
    """
    Verify that the reported removal count matches
    the number of flagged draft rules.
    """
    draft_rules = [make_rule(1), make_rule(2)]
    final_rules = [make_rule(1)]

    result = align_documents(
        draft_rules,
        final_rules,
    )

    assert result["potential_removal_count"] == len(
        result["unmatched_draft_rules"]
    )
def test_save_alignment_report(tmp_path):
    """
    Verify that an alignment report is saved as valid JSON.

    The pytest tmp_path fixture provides a temporary
    directory without modifying actual project data.
    """
    report = align_documents(
        [make_rule(1)],
        [make_rule(1)],
    )

    output_path = tmp_path / "alignment.json"

    saved_path = save_alignment_report(
        report,
        output_path,
    )

    assert saved_path == output_path
    assert output_path.exists()

    with output_path.open("r", encoding="utf-8") as file:
        loaded_report = json.load(file)

    assert loaded_report == report


def test_save_alignment_report_creates_directory(tmp_path):
    """
    Verify that missing parent directories are
    automatically created before saving.
    """
    output_path = (
        tmp_path / "reports" / "aligned" / "alignment.json"
    )

    report = {"draft_rule_count": 1}

    save_alignment_report(report, output_path)

    assert output_path.exists()
    assert output_path.parent.is_dir()


def test_save_alignment_report_rejects_empty_report(tmp_path):
    """
    Verify that an empty report cannot be saved.
    """
    output_path = tmp_path / "alignment.json"

    with pytest.raises(
        ValueError,
        match="cannot be empty",
    ):
        save_alignment_report({}, output_path)


def test_save_alignment_report_rejects_invalid_type(tmp_path):
    """
    Verify that report data must be a dictionary.
    """
    output_path = tmp_path / "alignment.json"

    with pytest.raises(
        TypeError,
        match="must be a dictionary",
    ):
        save_alignment_report(
            ["invalid report"],
            output_path,
        )


def test_save_alignment_report_rejects_empty_path():
    """
    Verify that an empty destination path is rejected.
    """
    with pytest.raises(
        ValueError,
        match="Output path cannot be empty",
    ):
        save_alignment_report(
            {"draft_rule_count": 1},
            "",
        )