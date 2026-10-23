"""
Local persistent vector database for regulatory intelligence.

Uses ChromaDB to store and retrieve regulatory provisions
without requiring a cloud database or paid API.
"""

from pathlib import Path

import chromadb


DEFAULT_DATABASE_PATH = Path("data/vector_db")


def create_vector_store(
    database_path: str | Path = DEFAULT_DATABASE_PATH,
):
    """
    Create or connect to a persistent local ChromaDB database.

    Args:
        database_path: Directory where ChromaDB stores its data.

    Returns:
        A persistent ChromaDB client.

    Raises:
        TypeError: If database_path has an invalid type.
        ValueError: If database_path is empty.
    """
    if not isinstance(database_path, (str, Path)):
        raise TypeError(
            "Database path must be a string or Path."
        )

    if isinstance(database_path, str) and not database_path.strip():
        raise ValueError("Database path cannot be empty.")

    path = Path(database_path)
    path.mkdir(parents=True, exist_ok=True)

    return chromadb.PersistentClient(path=str(path))
