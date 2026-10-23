"""
Tests for the local ChromaDB vector store.

All tests use temporary directories to avoid modifying
the project's real regulatory vector database.
"""

from pathlib import Path

import pytest

from app.rag_engine.vector_store import create_vector_store


def test_create_vector_store(tmp_path):
    """A persistent database should be created successfully."""
    database_path = tmp_path / "vector_db"

    client = create_vector_store(database_path)

    assert client is not None
    assert database_path.is_dir()


def test_create_nested_database_directory(tmp_path):
    """Missing parent directories should be created automatically."""
    database_path = tmp_path / "nested" / "storage" / "vectors"

    create_vector_store(database_path)

    assert database_path.is_dir()


def test_store_and_retrieve_rule(tmp_path):
    """A regulatory provision should be stored and retrieved."""
    client = create_vector_store(tmp_path / "database")

    collection = client.get_or_create_collection(
        name="test_regulatory_rules"
    )

    collection.add(
        ids=["rule_1"],
        documents=["Organizations must notify users within 24 hours."],
        embeddings=[[0.1, 0.2, 0.3]],
        metadatas=[{"rule_number": 1}],
    )

    result = collection.get(
        ids=["rule_1"],
        include=["documents", "metadatas"],
    )

    assert result["ids"] == ["rule_1"]
    assert result["documents"][0] == (
        "Organizations must notify users within 24 hours."
    )
    assert result["metadatas"][0]["rule_number"] == 1


def test_database_persistence(tmp_path):
    """Data should remain accessible after reconnecting."""
    database_path = tmp_path / "persistent_database"

    first_client = create_vector_store(database_path)

    collection = first_client.get_or_create_collection(
        name="persistent_rules"
    )

    collection.upsert(
        ids=["rule_2"],
        documents=["Organizations must maintain accurate records."],
        embeddings=[[0.4, 0.5, 0.6]],
    )

    second_client = create_vector_store(database_path)

    reopened_collection = second_client.get_collection(
        name="persistent_rules"
    )

    result = reopened_collection.get(
        ids=["rule_2"],
        include=["documents"],
    )

    assert result["ids"] == ["rule_2"]
    assert result["documents"][0] == (
        "Organizations must maintain accurate records."
    )


def test_reject_empty_database_path():
    """Empty database paths must be rejected."""
    with pytest.raises(ValueError, match="cannot be empty"):
        create_vector_store("")


def test_reject_invalid_database_path():
    """Invalid database path types must be rejected."""
    with pytest.raises(TypeError, match="must be a string or Path"):
        create_vector_store(123)
