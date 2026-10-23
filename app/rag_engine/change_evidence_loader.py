
"""
Load detected regulatory changes for evidence integration.
"""

import json
from pathlib import Path
from typing import Any


def load_regulatory_changes(
    file_path: str = "data/analysis/dpdp_2025_change_analysis.json",
) -> list[dict[str, Any]]:
    """Load analyzed regulatory changes from a JSON file."""

    path = Path(file_path)

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("Change analysis must be a JSON object.")

    analyzed_rules = data.get("analyzed_rules")

    if not isinstance(analyzed_rules, list):
        raise ValueError("Missing or invalid analyzed_rules list.")

    for rule in analyzed_rules:
        if not isinstance(rule, dict):
            raise ValueError("Each analyzed rule must be an object.")

        required_fields = (
            "draft_rule_number",
            "final_rule_number",
            "changes",
            "review_required",
        )

        for field in required_fields:
            if field not in rule:
                raise ValueError(
                    f"Analyzed rule is missing required field: {field}"
                )

    return analyzed_rules
