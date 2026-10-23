"""
Local embedding service for regulatory intelligence.

Converts regulatory text into semantic vectors using
Sentence Transformers without requiring a paid API.
"""

from functools import lru_cache

from sentence_transformers import SentenceTransformer


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384


@lru_cache(maxsize=1)
def load_embedding_model() -> SentenceTransformer:
    """
    Load and cache the local embedding model.

    The first call loads the model into memory.
    Subsequent calls reuse the same model instance.

    Returns:
        Loaded SentenceTransformer model.

    Raises:
        OSError: If model files cannot be loaded.
    """
    return SentenceTransformer(
        MODEL_NAME,
        device="cpu",
    )


def generate_embedding(text: str) -> list[float]:
    """
    Convert one text passage into a semantic embedding.

    Args:
        text: Nonempty regulatory or policy text.

    Returns:
        A normalized 384-dimensional embedding.

    Raises:
        TypeError: If text is not a string.
        ValueError: If text is empty.
        RuntimeError: If the embedding dimensions are invalid.
    """
    if not isinstance(text, str):
        raise TypeError("Text must be a string.")

    if not text.strip():
        raise ValueError("Text cannot be empty.")

    model = load_embedding_model()

    embedding = model.encode(
        text.strip(),
        normalize_embeddings=True,
    )

    result = embedding.tolist()

    if len(result) != EMBEDDING_DIMENSION:
        raise RuntimeError(
            "Unexpected embedding dimension: "
            f"{len(result)}"
        )

    return result


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Generate semantic embeddings for multiple passages.

    Args:
        texts: List of nonempty text passages.

    Returns:
        List of normalized 384-dimensional embeddings.

    Raises:
        TypeError: If texts is not a list or contains
            non-string values.
        ValueError: If texts is empty or contains
            empty text.
    """
    if not isinstance(texts, list):
        raise TypeError("Texts must be a list.")

    if not texts:
        raise ValueError("Texts cannot be empty.")

    for text in texts:
        if not isinstance(text, str):
            raise TypeError("Each text must be a string.")

        if not text.strip():
            raise ValueError("Text entries cannot be empty.")

    model = load_embedding_model()

    embeddings = model.encode(
        [text.strip() for text in texts],
        normalize_embeddings=True,
    )

    results = embeddings.tolist()

    if (
        len(results) != len(texts)
        or any(len(vector) != EMBEDDING_DIMENSION for vector in results)
    ):
        raise RuntimeError("Unexpected embedding output shape.")

    return results
