
"""
Connect regulatory change records with supporting source evidence.

Retrieves evidence from draft and final DPDP regulations.
Semantic search results are supporting candidates, not proof
of legal equivalence between provisions.
"""

from typing import Any

from app.rag_engine.evidence_retriever import (
    retrieve_regulatory_evidence,
)


def retrieve_change_evidence(
    query: str,
    top_k: int = 3,
    database_path: str = "data/vector_db",
) -> dict[str, Any]:
    """
    Retrieve draft and final regulatory evidence for a change.

    Args:
        query: Description of the regulatory change or question.
        top_k: Maximum evidence records per document version.
        database_path: Local ChromaDB directory.

    Returns:
        A dictionary containing the query, draft evidence,
        final evidence, and review status.
    """

    # Retrieve evidence from the draft regulation.
    draft_evidence = retrieve_regulatory_evidence(
        query=query,
        document_version="draft_2025",
        top_k=top_k,
        database_path=database_path,
    )

    # Retrieve evidence from the final regulation.
    final_evidence = retrieve_regulatory_evidence(
        query=query,
        document_version="final_2025",
        top_k=top_k,
        database_path=database_path,
    )

    # Keep evidence separate until rule alignment is verified.
    return {
        "query": query,
        "draft_evidence": draft_evidence,
        "final_evidence": final_evidence,
        "review_status": "requires_human_review",
    }


def retrieve_exact_change_evidence(
    change: dict[str, Any],
    database_path: str = "data/vector_db",
) -> dict[str, Any]:
    """
    Attach exact draft and final rule evidence to a detected change.

    Args:
        change: A change record from the change-analysis JSON.
        database_path: Location of the ChromaDB database.

    Returns:
        The original change with exact source evidence and review status.
    """
    from app.rag_engine.semantic_store import get_semantic_collection

    draft_number = change["draft_rule_number"]
    final_number = change["final_rule_number"]

    draft_id = f"dpdp_draft_2025_rule_{draft_number}"
    final_id = f"dpdp_final_2025_rule_{final_number}"

    collection = get_semantic_collection(database_path)

    results = collection.get(
        ids=[draft_id, final_id],
        include=["documents", "metadatas"],
    )

    evidence_by_id = {}

    for rule_id, text, metadata in zip(
        results["ids"],
        results["documents"],
        results["metadatas"],
    ):
        evidence_by_id[rule_id] = {
            "rule_id": rule_id,
            "rule_number": metadata["rule_number"],
            "title": metadata.get("title"),
            "document_version": metadata["document_version"],
            "source_file": metadata.get("source_file"),
            "text": text,
        }

    if draft_id not in evidence_by_id:
        raise ValueError(f"Draft evidence not found: {draft_id}")

    if final_id not in evidence_by_id:
        raise ValueError(f"Final evidence not found: {final_id}")

    return {
        "change": change,
        "draft_evidence": evidence_by_id[draft_id],
        "final_evidence": evidence_by_id[final_id],
        "review_status": "requires_human_review",
    }


def retrieve_all_change_evidence(
    changes: list[dict[str, Any]],
    database_path: str = "data/vector_db",
) -> list[dict[str, Any]]:
    """
    Retrieve exact draft and final evidence for analyzed changes.

    Args:
        changes: Analyzed regulatory change records.
        database_path: Local ChromaDB directory.

    Returns:
        Change records with their supporting source evidence.
    """
    if not isinstance(changes, list):
        raise ValueError("Changes must be a list.")

    evidence_records = []

    for change in changes:
        result = retrieve_exact_change_evidence(
            change=change,
            database_path=database_path,
        )

        evidence_records.append(result)

    return evidence_records

