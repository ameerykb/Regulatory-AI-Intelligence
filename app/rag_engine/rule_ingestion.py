"""
Prepare parsed regulatory rules for semantic indexing.

This module converts the existing DPDP JSON documents into
records with unique identifiers and source metadata.

It does not modify the source JSON or write to ChromaDB.
"""

import json
from pathlib import Path
from typing import Any


def prepare_regulatory_rules(
    file_path: str | Path,
    document_version: str,
) -> list[dict[str, Any]]:
    """
    Read parsed regulatory rules and prepare indexing records.

    Args:
        file_path: Path to an existing parsed regulatory JSON file.
        document_version: Version label, such as 'draft_2025'
            or 'final_2025'.

    Returns:
        A list of records containing IDs, rule numbers,
        text, titles, document versions, and source files.

    Raises:
        TypeError: If arguments have invalid types.
        ValueError: If document data is invalid.
        FileNotFoundError: If the JSON file does not exist.
    """
    if not isinstance(file_path, (str, Path)):
        raise TypeError("File path must be a string or Path.")

    if not isinstance(document_version, str):
        raise TypeError("Document version must be a string.")

    if not document_version.strip():
        raise ValueError("Document version cannot be empty.")

    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    with path.open("r", encoding="utf-8-sig") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("Parsed document must be a dictionary.")

    sections = data.get("sections")

    if not isinstance(sections, list):
        raise ValueError("Document must contain a sections list.")

    if not sections:
        raise ValueError("Document sections cannot be empty.")

    prepared_rules = []
    seen_ids = set()

    for section in sections:
        if not isinstance(section, dict):
            raise ValueError("Each section must be a dictionary.")

        rule_number = section.get("rule_number")
        title = section.get("title")
        text = section.get("text")

        if type(rule_number) is not int or rule_number <= 0:
            raise ValueError("Invalid rule number.")

        if not isinstance(title, str) or not title.strip():
            raise ValueError("Invalid rule title.")

        if not isinstance(text, str) or not text.strip():
            raise ValueError("Invalid rule text.")

        rule_id = f"dpdp_{document_version.strip()}_rule_{rule_number}"

        if rule_id in seen_ids:
            raise ValueError(f"Duplicate rule ID: {rule_id}")

        seen_ids.add(rule_id)

        prepared_rules.append({
            "id": rule_id,
            "rule_number": rule_number,
            "title": title.strip(),
            "text": text.strip(),
            "document_version": document_version.strip(),
            "source_file": path.name,
        })

    return prepared_rules
