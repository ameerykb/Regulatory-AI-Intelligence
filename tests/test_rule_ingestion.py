"""
Tests for preparing parsed regulatory rules for indexing.

Uses temporary JSON documents to avoid modifying real DPDP data.
"""

import json

import pytest

from app.rag_engine.rule_ingestion import prepare_regulatory_rules


@pytest.fixture
def sample_document(tmp_path):
    """Create a temporary fictional regulatory document."""
    path = tmp_path / "sample_rules.json"

    data = {
        "sections": [
            {
                "rule_number": 1,
                "title": "Data breach notification",
                "text": "Organizations must report a data breach.",
            },
            {
                "rule_number": 2,
                "title": "Record maintenance",
                "text": "Organizations must maintain accurate records.",
            },
        ]
    }

    path.write_text(json.dumps(data), encoding="utf-8")

    return path


def test_prepare_rules(sample_document):
    """Valid rules should be prepared successfully."""
    rules = prepare_regulatory_rules(
        sample_document,
        "draft_2025",
    )

    assert len(rules) == 2
    assert rules[0]["rule_number"] == 1
    assert rules[1]["rule_number"] == 2


def test_unique_versioned_ids(sample_document):
    """Draft and final versions must receive different IDs."""
    draft = prepare_regulatory_rules(
        sample_document,
        "draft_2025",
    )

    final = prepare_regulatory_rules(
        sample_document,
        "final_2025",
    )

    assert draft[0]["id"] != final[0]["id"]
    assert draft[0]["id"] == "dpdp_draft_2025_rule_1"
    assert final[0]["id"] == "dpdp_final_2025_rule_1"


def test_source_metadata(sample_document):
    """Prepared rules must retain source information."""
    rules = prepare_regulatory_rules(
        sample_document,
        "draft_2025",
    )

    assert rules[0]["title"] == "Data breach notification"
    assert rules[0]["document_version"] == "draft_2025"
    assert rules[0]["source_file"] == "sample_rules.json"


def test_reject_missing_file(tmp_path):
    """Missing JSON files must raise FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        prepare_regulatory_rules(
            tmp_path / "missing.json",
            "draft_2025",
        )


def test_reject_empty_version(sample_document):
    """Blank document versions must be rejected."""
    with pytest.raises(ValueError, match="cannot be empty"):
        prepare_regulatory_rules(
            sample_document,
            "   ",
        )


def test_reject_invalid_file_path():
    """File paths must be strings or Path objects."""
    with pytest.raises(TypeError, match="File path"):
        prepare_regulatory_rules(
            123,
            "draft_2025",
        )


def test_reject_missing_sections(tmp_path):
    """Documents must contain a sections list."""
    path = tmp_path / "invalid.json"
    path.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="sections list"):
        prepare_regulatory_rules(
            path,
            "draft_2025",
        )


def test_reject_duplicate_rule_numbers(tmp_path):
    """Duplicate rule numbers must not create duplicate IDs."""
    path = tmp_path / "duplicates.json"

    data = {
        "sections": [
            {
                "rule_number": 1,
                "title": "First rule",
                "text": "First regulatory requirement.",
            },
            {
                "rule_number": 1,
                "title": "Second rule",
                "text": "Second regulatory requirement.",
            },
        ]
    }

    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="Duplicate rule ID"):
        prepare_regulatory_rules(
            path,
            "draft_2025",
        )
