
"""
Claim-level verification workflow for regulatory RAG answers.

Extracts claims, maps citations to evidence,
verifies individual claims, and calculates
the overall claim-verification status.
"""

from app.rag_engine.structured_claim_extractor import (
    extract_structured_claims,
)

from app.rag_engine.claim_evidence_mapper import (
    map_claims_to_evidence,
)

from app.rag_engine.claim_verifier import (
    verify_individual_claim,
)


def is_verified_claim(item: dict) -> bool:
    """Check whether an individual claim passed verification."""

    verification = item.get("verification")

    if not isinstance(verification, dict):
        return False

    return (
        verification.get("verdict") == "SUPPORTED"
        and verification.get("quote_valid") is True
        and bool(item.get("source_numbers"))
        and not item.get("missing_sources")
        and bool(item.get("matched_sources"))
    )


def verify_answer_claims(
    answer: str,
    sources: list[dict],
) -> dict:
    """
    Extract and verify cited regulatory claims.

    Every claim must have:
    - A valid source citation.
    - Matching regulatory evidence.
    - A SUPPORTED verification verdict.
    - An exact validated evidence quotation.
    """

    # --------------------------------------------------
    # Step 1: Extract claims
    # --------------------------------------------------

    claims = extract_structured_claims(answer)

    # --------------------------------------------------
    # Step 2: Map claims to evidence
    # --------------------------------------------------

    mapped_claims = map_claims_to_evidence(
        claims=claims,
        sources=sources,
    )

    results = []

    # --------------------------------------------------
    # Step 3: Verify each claim
    # --------------------------------------------------

    for item in mapped_claims:

        source_numbers = item.get("source_numbers", [])
        missing_sources = item.get("missing_sources", [])
        matched_sources = item.get("matched_sources", [])

        if not source_numbers:

            verification = {
                "verdict": "REVIEW_REQUIRED",
                "quote_valid": False,
                "evidence_quote": "",
                "reason": (
                    "This claim has no regulatory source citation."
                ),
            }

        elif missing_sources:

            verification = {
                "verdict": "REVIEW_REQUIRED",
                "quote_valid": False,
                "evidence_quote": "",
                "reason": (
                    "One or more cited sources were not found."
                ),
            }

        elif not matched_sources:

            verification = {
                "verdict": "REVIEW_REQUIRED",
                "quote_valid": False,
                "evidence_quote": "",
                "reason": (
                    "No cited regulatory evidence could be matched."
                ),
            }

        else:

            evidence = "\n\n".join(
                source["text"]
                for source in matched_sources
            )

            verification = verify_individual_claim(
                claim=item["claim"],
                evidence=evidence,
            )

            if not isinstance(verification, dict):
                verification = {
                    "verdict": "REVIEW_REQUIRED",
                    "quote_valid": False,
                    "evidence_quote": "",
                    "reason": (
                        "The claim verifier returned an invalid result."
                    ),
                }

        results.append(
            {
                "claim": item["claim"],
                "source_numbers": source_numbers,
                "matched_sources": matched_sources,
                "missing_sources": missing_sources,
                "verification": verification,
            }
        )

    # --------------------------------------------------
    # Step 4: Citation statistics
    # --------------------------------------------------

    total_claims = len(results)

    cited_claims = sum(
        1
        for item in results
        if item["source_numbers"]
    )

    uncited_claims = total_claims - cited_claims

    citation_coverage = (
        round(
            (cited_claims / total_claims) * 100,
            2,
        )
        if total_claims > 0
        else 0.0
    )

    # --------------------------------------------------
    # Step 5: Verification statistics
    # --------------------------------------------------

    supported_claims = sum(
        1
        for item in results
        if is_verified_claim(item)
    )

    review_required_claims = (
        total_claims - supported_claims
    )

    all_claims_verified = (
        total_claims > 0
        and supported_claims == total_claims
    )

    # --------------------------------------------------
    # Step 6: Determine status
    # --------------------------------------------------

    if all_claims_verified:
        status = "verified"

    else:
        status = "completed_requires_human_review"

    # --------------------------------------------------
    # Step 7: Return results
    # --------------------------------------------------

    return {
        "total_claims": total_claims,
        "total_cited_claims": cited_claims,
        "total_uncited_claims": uncited_claims,
        "citation_coverage_percent": citation_coverage,
        "total_supported_claims": supported_claims,
        "total_review_required_claims": review_required_claims,
        "all_claims_verified": all_claims_verified,
        "claims": results,
        "status": status,
    }
