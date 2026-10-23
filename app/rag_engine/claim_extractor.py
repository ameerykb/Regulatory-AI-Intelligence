"""Extract cited claims from AI-generated regulatory answers."""

import re


def extract_cited_claims(answer: str) -> list[dict]:
    """
    Extract individual lines containing regulatory source citations.

    This is an initial rule-based extractor.
    """

    if not isinstance(answer, str):
        raise TypeError("Answer must be a string.")

    claims = []

    for line in answer.splitlines():
        line = line.strip()

        if not line:
            continue

        # Identify citations such as [Source 1]
        citation_numbers = re.findall(
            r"\[Source\s+(\d+)\]",
            line,
        )

        if not citation_numbers:
            claims.append(
                {
                    "claim":line,
                    "source_numbers":[]
                }
            )
            continue

        # Remove citations to obtain the claim text
        claim_text = re.sub(
            r"\[Source\s+\d+\]",
            "",
            line,
        ).strip()

        if not claim_text:
            continue

        claims.append(
            {
                "claim": claim_text,
                "source_numbers": sorted(
                    {int(number) for number in citation_numbers}
                ),
            }
        )

    return claims