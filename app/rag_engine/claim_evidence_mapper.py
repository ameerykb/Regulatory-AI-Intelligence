"""Map extracted regulatory claims to their cited evidence."""


def map_claims_to_evidence(
    claims: list[dict],
    sources: list[dict],
) -> list[dict]:
    """
    Match each extracted claim to its cited regulatory sources.

    Only evidence from explicitly cited sources is included.
    """

    if not isinstance(claims, list):
        raise TypeError("Claims must be a list.")

    if not isinstance(sources, list):
        raise TypeError("Sources must be a list.")

    # Build a lookup using citation numbers.
    source_lookup = {
        source["source_number"]: source
        for source in sources
    }

    mapped_claims = []

    for claim in claims:
        matched_sources = []
        missing_sources = []

        for source_number in claim["source_numbers"]:
            source = source_lookup.get(source_number)

            if source is None:
                missing_sources.append(source_number)
                continue

            matched_sources.append(
                {
                    "source_number": source_number,
                    "rule_number": source.get("rule_number"),
                    "document_version": source.get("document_version"),
                    "source_file": source.get("source_file"),
                    "text": source.get("text", ""),
                }
            )

        mapped_claims.append(
            {
                "claim": claim["claim"],
                "source_numbers": claim["source_numbers"],
                "matched_sources": matched_sources,
                "missing_sources": missing_sources,
            }
        )

    return mapped_claims