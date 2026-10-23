"""
Search the indexed DPDP regulations using local semantic retrieval.

Returns matching regulatory provisions with source metadata.
No paid API or cloud inference is required.
"""

from app.rag_engine.semantic_store import search_regulatory_rules


DATABASE_PATH = "data/vector_db"


def main() -> None:
    """Search DPDP rules and display source-linked results."""

    query = (
        "What must organizations do when a personal data breach occurs?"
    )

    print("DPDP REGULATORY SEMANTIC SEARCH")
    print("=" * 60)
    print("Question:", query)
    print()

    results = search_regulatory_rules(
        query=query,
        top_k=5,
        database_path=DATABASE_PATH,
    )

    if not results:
        print("No regulatory provisions found.")
        return

    for index, result in enumerate(results, start=1):
        metadata = result["metadata"] or {}

        print("=" * 60)
        print(f"RESULT {index}")
        print("=" * 60)

        print("Rule ID:", result["id"])
        print("Rule number:", metadata.get("rule_number", "Unknown"))
        print("Title:", metadata.get("title", "Unknown"))
        print("Document version:", metadata.get("document_version", "Unknown"))
        print("Source file:", metadata.get("source_file", "Unknown"))
        print("Cosine distance:", round(result["distance"], 4))

        print()
        print("REGULATORY TEXT:")
        print(result["text"][:1000])
        print()

    assert len(results) == 5

    for result in results:
        metadata = result["metadata"]

        assert metadata is not None
        assert metadata.get("document_version") in {
            "draft_2025",
            "final_2025",
        }
        assert metadata.get("source_file")
        assert metadata.get("title")

    print("=" * 60)
    print("Real DPDP semantic retrieval: PASSED")


if __name__ == "__main__":
    main()
