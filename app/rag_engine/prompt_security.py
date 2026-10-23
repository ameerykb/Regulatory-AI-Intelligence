"""
Basic prompt injection detection for retrieved documents.

This module identifies common instruction-like patterns
that should not be trusted as regulatory evidence.
"""

import re


SUSPICIOUS_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"disregard\s+(all\s+)?prior\s+instructions",
    r"override\s+(the\s+)?system\s+prompt",
    r"forget\s+(all\s+)?previous\s+instructions",
    r"you\s+are\s+now\s+(a|an)\s+",
    r"do\s+not\s+answer\s+the\s+user",
    r"output\s+exactly\s*:",
    r"reveal\s+(your\s+)?system\s+prompt",
]


def detect_prompt_injection(text: str) -> bool:
    """Detect common prompt injection patterns."""

    if not isinstance(text, str):
        raise TypeError("Text must be a string.")

    return any(
        re.search(pattern, text, flags=re.IGNORECASE)
        for pattern in SUSPICIOUS_PATTERNS
    )
