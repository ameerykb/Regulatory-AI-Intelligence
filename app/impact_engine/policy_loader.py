
from pathlib import Path


def load_company_policy(
    file_path: str = "data/company_policies/privacy_policy.txt",
) -> str:
    """Load a company policy from a text file."""

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Company policy file not found: {file_path}"
        )

    policy_text = path.read_text(encoding="utf-8")

    if not policy_text.strip():
        raise ValueError("Company policy file is empty.")

    return policy_text


def extract_policy_sections(policy_text: str) -> dict:
    """Extract numbered sections from a company policy."""

    import re

    sections = {}
    current_section = None

    for line in policy_text.splitlines():
        line = line.strip()

        if re.match(r"^\d+\.\s+[A-Z]", line):
            current_section = line
            sections[current_section] = ""

        elif current_section and line:
            sections[current_section] += line + " "

    return {
        title: content.strip()
        for title, content in sections.items()
    }


def find_relevant_policy_sections(
    sections: dict,
    keyword: str,
) -> dict:
    """Find policy sections containing a keyword."""

    if not keyword.strip():
        return {}

    keyword = keyword.lower().strip()

    return {
        title: content
        for title, content in sections.items()
        if keyword in title.lower() or keyword in content.lower()
    }

