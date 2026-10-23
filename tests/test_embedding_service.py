"""
Tests for the local embedding service.

Uses a fake model to keep tests fast and offline.
"""

import numpy as np
import pytest

from app.rag_engine import embedding_service


class FakeEmbeddingModel:
    """Provide predictable embeddings without loading a real model."""

    def encode(self, texts, normalize_embeddings=False):
        assert normalize_embeddings is True

        if isinstance(texts, str):
            return np.full(384, 0.05, dtype=np.float32)

        return np.full(
            (len(texts), 384),
            0.05,
            dtype=np.float32,
        )


@pytest.fixture
def fake_model(monkeypatch):
    """Replace the real model loader with a lightweight fake."""
    model = FakeEmbeddingModel()

    monkeypatch.setattr(
        embedding_service,
        "load_embedding_model",
        lambda: model,
    )

    return model


def test_generate_single_embedding(fake_model):
    """A single passage should produce 384 values."""
    result = embedding_service.generate_embedding(
        "Organizations must report a data breach."
    )

    assert isinstance(result, list)
    assert len(result) == 384
    assert all(isinstance(value, float) for value in result)


def test_generate_batch_embeddings(fake_model):
    """Multiple passages should produce matching vectors."""
    result = embedding_service.generate_embeddings([
        "Report data breaches.",
        "Maintain accurate records.",
    ])

    assert len(result) == 2
    assert all(len(vector) == 384 for vector in result)


def test_reject_empty_single_text():
    """Blank input must be rejected before model loading."""
    with pytest.raises(ValueError, match="cannot be empty"):
        embedding_service.generate_embedding("   ")


def test_reject_invalid_single_text():
    """Non-string input must be rejected."""
    with pytest.raises(TypeError, match="must be a string"):
        embedding_service.generate_embedding(123)


def test_reject_empty_batch():
    """An empty list of passages must be rejected."""
    with pytest.raises(ValueError, match="cannot be empty"):
        embedding_service.generate_embeddings([])


def test_reject_invalid_batch_entry():
    """Every batch entry must be a string."""
    with pytest.raises(TypeError, match="must be a string"):
        embedding_service.generate_embeddings([
            "Valid regulatory text",
            123,
        ])


def test_reject_blank_batch_entry():
    """Blank passages in a batch must be rejected."""
    with pytest.raises(ValueError, match="cannot be empty"):
        embedding_service.generate_embeddings([
            "Valid regulatory text",
            "   ",
        ])


def test_reject_invalid_embedding_dimensions(monkeypatch):
    """Incorrect model output dimensions must be rejected."""

    class InvalidModel:
        def encode(self, text, normalize_embeddings=False):
            return np.zeros(10, dtype=np.float32)

    monkeypatch.setattr(
        embedding_service,
        "load_embedding_model",
        lambda: InvalidModel(),
    )

    with pytest.raises(RuntimeError, match="Unexpected embedding dimension"):
        embedding_service.generate_embedding(
            "Regulatory text"
        )
