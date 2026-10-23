
import re



def validate_source_citations(answer: str, source_count: int) -> dict:
    """Check whether source citations refer to available evidence."""

    if not isinstance(answer, str):
        raise TypeError("Answer must be a string.")

    if not isinstance(source_count, int) or isinstance(source_count, bool):
        raise TypeError("Source count must be an integer.")

    if source_count < 0:
        raise ValueError("Source count cannot be negative.")

    citation_numbers = [
        int(number)
        for number in re.findall(r"\[Source\s+(\d+)\]", answer)
    ]

    invalid_citations = sorted({
        number
        for number in citation_numbers
        if number < 1 or number > source_count
    })

    return {
        "is_valid": len(invalid_citations) == 0,
        "citation_numbers": citation_numbers,
        "invalid_citations": invalid_citations,
        "has_citations": bool(citation_numbers),
    }
