"""Extract structured regulatory claims from AI-generated answers."""

import re


def extract_structured_claims(answer: str) -> list[dict]:
    """
    Extract regulatory claims while preserving nested bullet context.

    Uses indentation to associate nested bullets with their
    parent requirements.

    This remains an experimental rule-based extractor.
    """

    if not isinstance(answer, str):
        raise TypeError("Answer must be a string.")

    claims = []
    introduction = ""
    current_heading = ""

    # Stores active bullet contexts:
    # (indentation_level, bullet_text)
    bullet_stack = []

    for raw_line in answer.splitlines():
        line = raw_line.strip()

        if not line:
            continue

        indentation = len(raw_line) - len(raw_line.lstrip())

        citations = sorted({
            int(number)
            for number in re.findall(r"\[Source\s+(\d+)\]", line)
        })

        clean_line = re.sub(
            r"\[Source\s+\d+\]",
            "",
            line,
        ).strip()

        # Numbered headings
        numbered = re.match(r"^\d+\.\s+(.+):$", clean_line)

        if numbered:
            current_heading = numbered.group(1)
            bullet_stack = []
            continue

        # Bullet points
        if clean_line.startswith("- "):
            bullet_text = clean_line[2:].strip()

            # Remove contexts from the same or deeper level.
            while bullet_stack and bullet_stack[-1][0] >= indentation:
                bullet_stack.pop()

            parent_context = [
                item[1]
                for item in bullet_stack
            ]

            # A bullet ending in ":" introduces nested requirements.
            if bullet_text.endswith(":"):
                bullet_stack.append(
                    (indentation, bullet_text[:-1].strip())
                )
                continue

            claim_parts = []

            if introduction:
                claim_parts.append(introduction)

            if current_heading:
                claim_parts.append(current_heading)

            claim_parts.extend(parent_context)
            claim_parts.append(bullet_text)

            claim_text = " ".join(claim_parts)

            claims.append({
                "claim": format_claim_text(claim_text),
                "source_numbers": citations,
            })

            continue

        # Introductory statements
        if clean_line.endswith(":"):
            introduction = clean_line[:-1].strip()
            current_heading = ""
            bullet_stack = []
            continue

        # Skip citation summaries.
        if is_citation_summary(clean_line):
            continue

        # Regular statements
        claims.append({
            "claim": format_claim_text(clean_line),
            "source_numbers": citations,
        })

    return claims



def is_citation_summary(text: str) -> bool:
    """
    Identify concluding statements that primarily reference sources.

    This is a conservative, rule-based check.
    """

    if not isinstance(text, str):
        raise TypeError("Text must be a string.")

    normalized = text.strip().lower()

    patterns = (
        "these obligations are detailed in",
        "these requirements are detailed in",
        "these provisions are outlined in",
        "these obligations are outlined in",
        "the above obligations are",
    )

    return any(
        normalized.startswith(pattern)
        for pattern in patterns
    )


def format_claim_text(text: str) -> str:
    """
    Apply conservative formatting to extracted claims.

    Does not rewrite regulatory requirements or
    change their substantive wording.
    """

    if not isinstance(text, str):
        raise TypeError("Claim text must be a string.")

    import re

    # Remove unnecessary whitespace.
    text = re.sub(r"\s+", " ", text).strip()

    # Remove spaces before punctuation.
    text = re.sub(r"\s+([.,;:])", r"\1", text)

    # Ensure the claim ends with punctuation.
    if text and text[-1] not in ".!?":
        text += "."

    return text