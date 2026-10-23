
"""
Generate an evidence-backed DPDP regulatory change report.

Run from the project root:
    python -m scripts.generate_evidence_report
"""

import json
from pathlib import Path

from app.rag_engine.change_evidence_loader import (
    load_regulatory_changes,
)
from app.rag_engine.change_evidence import (
    retrieve_all_change_evidence,
)
from app.report_engine.report_builder import (
    build_regulatory_change_report,
)


ANALYSIS_PATH = Path(
    "data/analysis/dpdp_2025_change_analysis.json"
)

OUTPUT_PATH = Path(
    "data/reports/dpdp_2025_evidence_report.json"
)


def generate_evidence_report() -> Path:
    """Generate and save the regulatory evidence report."""

    changes = load_regulatory_changes(
        file_path=str(ANALYSIS_PATH)
    )

    evidence = retrieve_all_change_evidence(changes)

    report = build_regulatory_change_report(evidence)

    # Preserve unresolved alignments and conflicts.
    with ANALYSIS_PATH.open("r", encoding="utf-8") as file:
        original_analysis = json.load(file)

    report["pending_review"] = original_analysis["pending_review"]
    report["pending_alignment_count"] = len(
        report["pending_review"]
    )

    report["alignment_conflicts"] = original_analysis[
        "alignment_conflicts"
    ]

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(
            report,
            file,
            indent=2,
            ensure_ascii=False,
        )

    return OUTPUT_PATH


if __name__ == "__main__":
    output_path = generate_evidence_report()

    with output_path.open("r", encoding="utf-8") as file:
        saved_report = json.load(file)

    print("=" * 55)
    print("REGULATORY EVIDENCE REPORT GENERATED")
    print("=" * 55)
    print("File:", output_path)
    print("Analyzed changes:", saved_report["total_changes"])
    print(
        "Human reviews required:",
        saved_report["review_required_count"],
    )
    print(
        "Pending alignments:",
        saved_report["pending_alignment_count"],
    )
    print(
        "Alignment conflicts:",
        len(saved_report["alignment_conflicts"]),
    )
    print()
    print("REPORT GENERATION: PASSED")
