"""
Index the parsed DPDP draft and final rules into ChromaDB.

Uses the local embedding model to generate semantic vectors.
The original parsed JSON files are not modified.
"""

from app.rag_engine.rule_ingestion import prepare_regulatory_rules
from app.rag_engine.semantic_store import (
    get_semantic_collection,
    store_regulatory_rules,
)


DATABASE_PATH = "data/vector_db"
EXPECTED_DRAFT_RULES = 22
EXPECTED_FINAL_RULES = 23


def main() -> None:
    """Prepare, validate, and index the DPDP regulatory rules."""

    print("DPDP REGULATORY SEMANTIC INDEXING")
    print("=" * 50)

    draft_rules = prepare_regulatory_rules(
        "data/parsed/dpdp_draft_2025_sections.json",
        "draft_2025",
    )

    final_rules = prepare_regulatory_rules(
        "data/parsed/dpdp_final_2025_sections.json",
        "final_2025",
    )

    print("Draft rules prepared:", len(draft_rules))
    print("Final rules prepared:", len(final_rules))

    if len(draft_rules) != EXPECTED_DRAFT_RULES:
        raise RuntimeError("Unexpected draft rule count.")

    if len(final_rules) != EXPECTED_FINAL_RULES:
        raise RuntimeError("Unexpected final rule count.")

    all_rules = draft_rules + final_rules

    if len({rule["id"] for rule in all_rules}) != len(all_rules):
        raise RuntimeError("Duplicate regulatory IDs detected.")

    print("Generating local embeddings and indexing rules...")

    stored = store_regulatory_rules(
        all_rules,
        database_path=DATABASE_PATH,
    )

    collection = get_semantic_collection(DATABASE_PATH)

    # Verify that all expected IDs exist in the collection.
    expected_ids = {rule["id"] for rule in all_rules}
    stored_records = collection.get(
        ids=sorted(expected_ids),
        include=["metadatas"],
    )

    actual_ids = set(stored_records["ids"])

    if actual_ids != expected_ids:
        raise RuntimeError("Not all expected rules were indexed.")

    metadata_by_id = dict(
        zip(stored_records["ids"], stored_records["metadatas"])
    )

    for rule in all_rules:
        metadata = metadata_by_id[rule["id"]]

        if metadata["document_version"] != rule["document_version"]:
            raise RuntimeError(
                f"Incorrect source version for {rule['id']}"
            )

    print()
    print("Rules submitted:", stored)
    print("Verified indexed IDs:", len(actual_ids))
    print("Collection total:", collection.count())
    print("Indexing verification: PASSED")


if __name__ == "__main__":
    main()
