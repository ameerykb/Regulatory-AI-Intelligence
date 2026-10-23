"""Claim-level verification workflow for regulatory RAG answers."""

from app.rag_engine.structured_claim_extractor import extract_structured_claims
from app.rag_engine.claim_evidence_mapper import map_claims_to_evidence
from app.rag_engine.claim_verifier import verify_individual_claim


def verify_answer_claims(
    answer: str,
    sources: list[dict],
) -> dict:
    """
    Extract cited claims, map evidence, and verify each claim.

    Claims without citations are not verified by this initial workflow.
    """

    # Step 1: Extract claims from the AI answer.
    claims = extract_structured_claims(answer)

    # Step 2: Match claims to their cited sources.
    mapped_claims = map_claims_to_evidence(
        claims=claims,
        sources=sources,
    )

    results = []

    # Step 3: Verify each extracted claim.
    for item in mapped_claims:

        # Case 1: Claim has no source citation.
        if not item["source_numbers"]:
            verification = {
                "verdict": "REVIEW_REQUIRED",
                "quote_valid": False,
                "evidence_quote": "",
                "reason": "This statement has no regulatory source citation.",
            }

        # Case 2: Claim cites a source that does not exist.
        elif item["missing_sources"]:
            verification = {
                "verdict": "REVIEW_REQUIRED",
                "quote_valid": False,
                "evidence_quote": "",
                "reason": "One or more cited sources were not found.",
            }

        # Case 3: No regulatory evidence was matched.
        elif not item["matched_sources"]:
            verification = {
                "verdict": "REVIEW_REQUIRED",
                "quote_valid": False,
                "evidence_quote": "",
                "reason": "No cited regulatory evidence could be matched.",
            }

        else:
            # Combine evidence from the cited sources only.
            evidence = "\n\n".join(
                source["text"]
                for source in item["matched_sources"]
            )

            verification = verify_individual_claim(
                claim=item["claim"],
                evidence=evidence,
            )

        results.append(
            {
                "claim": item["claim"],
                "source_numbers": item["source_numbers"],
                "matched_sources": item["matched_sources"],
                "missing_sources": item["missing_sources"],
                "verification": verification,
            }
        )

        # Calculate claim citation statistics.
    total_claims = len(results)

    cited_claims = sum(
        1 for item in results
        if item["source_numbers"]
    )

    uncited_claims = total_claims - cited_claims

    citation_coverage = (
        round((cited_claims / total_claims) * 100, 2)
        if total_claims > 0
        else 0.0
    )

    return {
        "total_claims": total_claims,
        "total_cited_claims": cited_claims,
        "total_uncited_claims": uncited_claims,
        "citation_coverage_percent": citation_coverage,
        "claims": results,
        "status": "completed_requires_human_review",
    }