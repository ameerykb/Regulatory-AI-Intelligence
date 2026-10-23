"""
Semantic storage and retrieval for regulatory provisions.

Uses a local Sentence Transformers embedding model and
a persistent ChromaDB database. No paid API is required.
"""

from typing import Any

from app.rag_engine.embedding_service import (
    EMBEDDING_DIMENSION,
    generate_embedding,
    generate_embeddings,
)
from app.rag_engine.vector_store import create_vector_store


COLLECTION_NAME = "regulatory_semantic_rules"


def get_semantic_collection(
    database_path: str = "data/vector_db",
) -> Any:
    """
    Open or create the persistent regulatory collection.

    Uses cosine distance for normalized embeddings.

    Args:
        database_path: Directory containing the local database.

    Returns:
        ChromaDB collection for semantic regulatory search.
    """
    client = create_vector_store(database_path)

    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        configuration={"hnsw": {"space": "cosine"}},
    )


def store_regulatory_rules(
    rules: list[dict[str, Any]],
    database_path: str = "data/vector_db",
) -> int:
    """
    Generate embeddings and store regulatory provisions.

    Each rule must contain:
        - id: Unique string identifier.
        - text: Nonempty regulatory text.
        - rule_number: Positive integer.

    Args:
        rules: Regulatory provisions to store.
        database_path: Local ChromaDB directory.

    Returns:
        Number of rules successfully submitted for storage.

    Raises:
        TypeError: If the input has an invalid type.
        ValueError: If required rule fields are invalid.

    Notes:
        Existing IDs are updated using upsert().
        Source documents are not modified.
    """
    if not isinstance(rules, list):
        raise TypeError("Rules must be a list.")

    if not rules:
        raise ValueError("Rules cannot be empty.")

    ids = []
    texts = []
    metadatas = []

    for rule in rules:
        if not isinstance(rule, dict):
            raise TypeError("Each rule must be a dictionary.")

        rule_id = rule.get("id")
        text = rule.get("text")
        rule_number = rule.get("rule_number")

        if not isinstance(rule_id, str) or not rule_id.strip():
            raise ValueError("Each rule must have a valid ID.")

        if not isinstance(text, str) or not text.strip():
            raise ValueError("Each rule must have valid text.")

        if (
            type(rule_number) is not int
            or rule_number <= 0
        ):
            raise ValueError("Each rule must have a positive rule number.")

        ids.append(rule_id.strip())
        texts.append(text.strip())
        # Step 1: Define metadata for the current rule.
                # Define metadata for the current regulatory rule.
        metadata = {
            "rule_number": rule_number,
            "source_type": "regulation",
        }

        # Add optional source metadata.
        for field in ("title", "document_version", "source_file"):
            value = rule.get(field)

            if value is not None:
                if not isinstance(value, str) or not value.strip():
                    raise ValueError(
                        f"Invalid regulatory metadata: {field}"
                    )

                metadata[field] = value.strip()

        # Save this rule's metadata.
        

# Step 3: Add this rule's metadata to the list.
        metadatas.append(metadata)

    if len(set(ids)) != len(ids):
        raise ValueError("Rule IDs must be unique.")

    # Generate all embeddings locally.
    embeddings = generate_embeddings(texts)

    if any(len(vector) != EMBEDDING_DIMENSION for vector in embeddings):
        raise RuntimeError("Invalid embedding dimensions.")

    collection = get_semantic_collection(database_path)

    collection.upsert(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    return len(ids)


def search_regulatory_rules(
    query: str,
    top_k: int = 3,
    database_path: str = "data/vector_db",
    document_version: str | None = None,
) -> list[dict[str, Any]]:
    """
    Search regulatory provisions using semantic similarity.

    Args:
        query: Natural-language search question.
        top_k: Maximum number of results.
        database_path: Local database directory.

    Returns:
        Ranked matching provisions with IDs, text,
        metadata, and cosine-distance values.

    Raises:
        TypeError: If query or top_k has an invalid type.
        ValueError: If query is empty or top_k is invalid.

    Notes:
        Lower cosine distance indicates a closer vector match.
        Distance is not a legal confidence score.
    """
    if not isinstance(query, str):
        raise TypeError("Query must be a string.")

    if not query.strip():
        raise ValueError("Query cannot be empty.")

    if type(top_k) is not int:
        raise TypeError("top_k must be an integer.")

    if top_k <= 0:
        raise ValueError("top_k must be positive.")

    if document_version is not None:
     if document_version not in ("draft_2025", "final_2025"):
        raise ValueError(
                "document_version must be 'draft_2025' or 'final_2025'."
            )

    collection = get_semantic_collection(database_path)

    
    if collection.count() == 0:
        return []
    query_embedding = generate_embedding(query)

    query_options = {
        "query_embeddings": [query_embedding],
        "n_results": min(top_k, collection.count()),
        "include": ["documents", "metadatas", "distances"],
    }

    if document_version is not None:
        query_options["where"] = {
            "document_version": document_version
        }

    results = collection.query(**query_options)
    
    

    matches = []

    for rule_id, document, metadata, distance in zip(
        results["ids"][0],
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        matches.append({
            "id": rule_id,
            "text": document,
            "metadata": metadata,
            "distance": float(distance),
        })

    return matches
