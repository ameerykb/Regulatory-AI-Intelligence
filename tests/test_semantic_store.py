"""
Tests for semantic regulatory storage and retrieval.

Use temporary ChromaDB directories and deterministic fake
embeddings to avoid network requests and model downloads.
"""

import pytest

from app.rag_engine import semantic_store


def fake_generate_embeddings(texts):
    """Generate deterministic 384-dimensional test vectors."""
    return [
        [1.0 if index == 0 else 0.0 for index in range(384)]
        if "breach" in text.lower()
        else [1.0 if index == 1 else 0.0 for index in range(384)]
        for text in texts
    ]


def fake_generate_embedding(text):
    """Generate a deterministic search-query vector."""
    if "breach" in text.lower():
        return [1.0 if index == 0 else 0.0 for index in range(384)]

    return [1.0 if index == 1 else 0.0 for index in range(384)]


@pytest.fixture
def fake_embeddings(monkeypatch):
    """Replace real embedding generation with local test functions."""
    monkeypatch.setattr(
        semantic_store,
        "generate_embeddings",
        fake_generate_embeddings,
    )

    monkeypatch.setattr(
        semantic_store,
        "generate_embedding",
        fake_generate_embedding,
    )


@pytest.fixture
def sample_rules():
    """Return two fictional regulatory provisions."""
    return [
        {
            "id": "rule_1",
            "rule_number": 1,
            "text": "Organizations must report a data breach.",
        },
        {
            "id": "rule_2",
            "rule_number": 2,
            "text": "Organizations must maintain accurate records.",
        },
    ]


def test_store_regulatory_rules(tmp_path, fake_embeddings, sample_rules):
    """Valid rules should be stored in ChromaDB."""
    database_path = str(tmp_path / "database")

    stored = semantic_store.store_regulatory_rules(
        sample_rules,
        database_path=database_path,
    )

    collection = semantic_store.get_semantic_collection(database_path)

    assert stored == 2
    assert collection.count() == 2


def test_semantic_search_returns_relevant_rule(
    tmp_path,
    fake_embeddings,
    sample_rules,
):
    """The breach query should retrieve the breach rule first."""
    database_path = str(tmp_path / "database")

    semantic_store.store_regulatory_rules(
        sample_rules,
        database_path=database_path,
    )

    results = semantic_store.search_regulatory_rules(
        query="When must a breach be reported?",
        top_k=2,
        database_path=database_path,
    )

    assert len(results) == 2
    assert results[0]["id"] == "rule_1"
    assert results[0]["metadata"]["rule_number"] == 1
    assert results[0]["distance"] <= results[1]["distance"]


def test_search_empty_collection(tmp_path, fake_embeddings):
    """Searching an empty collection should return an empty list."""
    results = semantic_store.search_regulatory_rules(
        query="data breach",
        database_path=str(tmp_path / "empty_database"),
    )

    assert results == []


def test_reject_duplicate_rule_ids(tmp_path):
    """Duplicate IDs in one batch must be rejected."""
    rules = [
        {"id": "same", "rule_number": 1, "text": "First rule."},
        {"id": "same", "rule_number": 2, "text": "Second rule."},
    ]

    with pytest.raises(ValueError, match="must be unique"):
        semantic_store.store_regulatory_rules(
            rules,
            database_path=str(tmp_path / "database"),
        )


def test_reject_invalid_rule_number(tmp_path):
    """Rule numbers must be positive integers."""
    rules = [
        {"id": "invalid", "rule_number": 0, "text": "Some rule."}
    ]

    with pytest.raises(ValueError, match="positive rule number"):
        semantic_store.store_regulatory_rules(
            rules,
            database_path=str(tmp_path / "database"),
        )


def test_reject_empty_search_query():
    """Empty search queries must be rejected."""
    with pytest.raises(ValueError, match="cannot be empty"):
        semantic_store.search_regulatory_rules("   ")


def test_reject_invalid_top_k():
    """The result limit must be a positive integer."""
    with pytest.raises(ValueError, match="must be positive"):
        semantic_store.search_regulatory_rules(
            "data breach",
            top_k=0,
        )


def test_upsert_updates_existing_rule(
    tmp_path,
    fake_embeddings,
):
    """Updating an existing ID should replace its stored text."""
    database_path = str(tmp_path / "database")

    original = [{
        "id": "rule_1",
        "rule_number": 1,
        "text": "Organizations must report a breach.",
    }]

    updated = [{
        "id": "rule_1",
        "rule_number": 1,
        "text": "Organizations must report a breach within 24 hours.",
    }]

    semantic_store.store_regulatory_rules(original, database_path)
    semantic_store.store_regulatory_rules(updated, database_path)

    collection = semantic_store.get_semantic_collection(database_path)

    result = collection.get(
        ids=["rule_1"],
        include=["documents"],
    )

    assert collection.count() == 1
    assert result["documents"][0] == updated[0]["text"]

def test_search_filters_by_document_version(
    tmp_path,
    fake_embeddings,
):
    """Search results must belong to the requested document version."""

    database_path = str(tmp_path / "database")

    rules = [
        {
            "id": "draft_rule_7",
            "rule_number": 7,
            "text": "Organizations must report personal data breaches.",
            "document_version": "draft_2025",
        },
        {
            "id": "final_rule_7",
            "rule_number": 7,
            "text": "Organizations must notify affected individuals of breaches.",
            "document_version": "final_2025",
        },
    ]

    semantic_store.store_regulatory_rules(
        rules,
        database_path=database_path,
    )

    draft_results = semantic_store.search_regulatory_rules(
        query="personal data breach",
        top_k=3,
        database_path=database_path,
        document_version="draft_2025",
    )

    final_results = semantic_store.search_regulatory_rules(
        query="personal data breach",
        top_k=3,
        database_path=database_path,
        document_version="final_2025",
    )

    assert len(draft_results) == 1
    assert draft_results[0]["id"] == "draft_rule_7"

    assert len(final_results) == 1
    assert final_results[0]["id"] == "final_rule_7"

def test_search_rejects_invalid_document_version(tmp_path):
    """Reject unsupported regulatory document versions."""

    database_path = str(tmp_path / "database")

    with pytest.raises(ValueError, match="document_version"):
        semantic_store.search_regulatory_rules(
            query="personal data breach",
            top_k=3,
            database_path=database_path,
            document_version="draft_2024",
        )