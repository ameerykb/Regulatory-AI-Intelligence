"""
Retrieve source evidence from indexed regulatory documents.

Evidence is retrieved from local ChromaDB using semantic search.
No LLM or paid API is required.
"""

from typing import Any

from app.rag_engine.semantic_store import search_regulatory_rules


def retrieve_regulatory_evidence(
    query: str,
    document_version: str,
    top_k: int = 3,
    database_path: str = "data/vector_db",
) -> list[dict[str, Any]]:
    """
    Retrieve relevant evidence from one regulatory document version.

    Args:
        query: Natural-language question or regulatory change.
        document_version: Either draft_2025 or final_2025.
        top_k: Maximum number of evidence records to retrieve.
        database_path: Local ChromaDB directory.

    Returns:
        A list of evidence records with source metadata.
    """

    results = search_regulatory_rules(
        query=query,
        top_k=top_k,
        database_path=database_path,
        document_version=document_version,
    )

    evidence_records = []

    for result in results:
        metadata = result["metadata"]

        evidence = {
            "rule_id": result["id"],
            "rule_number": metadata.get("rule_number"),
            "title": metadata.get("title"),
            "document_version": metadata.get("document_version"),
            "source_file": metadata.get("source_file"),
            "text": result["text"],
            "distance": result["distance"],
        }

        evidence_records.append(evidence)

    return evidence_records