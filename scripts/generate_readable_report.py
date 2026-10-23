
"""Generate a readable preliminary regulatory impact report."""

import json
from pathlib import Path


REPORTS_DIR = Path("data/reports")


def main():
    input_path = REPORTS_DIR / "dpdp_2025_consolidated_report.json"
    output_path = REPORTS_DIR / "dpdp_2025_readable_report.md"

    with input_path.open("r", encoding="utf-8") as file:
        report = json.load(file)

    summary = report["evidence_summary"]
    priorities = report["review_priority_summary"]
    records = report["evidence_records"]
    unmatched = report["manual_review_groups"]

    lines = [
        "# DPDP Rules 2025 — Regulatory Impact Intelligence Report",
        "",
        "**Report status:** Preliminary — Human review required",
        "",
        f"**Generated at (UTC):** {report['generated_at_utc']}",
        "",
        "## Executive Summary",
        "",
        f"- Aligned regulatory rule pairs: {summary['aligned_rule_pairs']}",
        f"- Preliminary evidence records: {len(records)}",
        f"- Review-first recommendations: {priorities['review_first']}",
        f"- Standard-review recommendations: {priorities['standard_review']}",
        f"- Unmatched change groups requiring review: {len(unmatched)}",
        f"- Rule pairs without generated evidence: {summary['rule_pairs_without_evidence']}",
        "",
        "## Regulatory Impact Evidence",
        "",
    ]

    for index, record in enumerate(records, start=1):
        recommendation = record["review_recommendation"]

        lines.extend([
            f"### Evidence Record {index}",
            "",
            f"**Draft Rule:** {record['draft_rule_number']}",
            "",
            f"**Final Rule:** {record['final_rule_number']}",
            "",
            f"**Company Policy:** {record['policy_section']}",
            "",
            f"**Similarity Score:** {record['similarity_score']}",
            "",
            f"**Review Priority:** {recommendation['review_priority']}",
            "",
            "**Regulatory Context:**",
            "",
            record["regulatory_context"],
            "",
            "**Company Policy Text:**",
            "",
            record["policy_text"],
            "",
            "**Recommended Review Action:**",
            "",
            recommendation["recommendation"],
            "",
            "---",
            "",
        ])

    lines.extend([
        "## Unmatched Regulatory Change Groups",
        "",
        "The following groups require independent manual assessment.",
        "",
    ])

    for group in unmatched:
        lines.extend([
            (
                f"### Draft Rule {group['draft_rule_number']} "
                f"→ Final Rule {group['final_rule_number']} "
                f"| Group {group['group_number']}"
            ),
            "",
            "**Detected Changes:**",
            "",
        ])

        for changed_text in group["changed_texts"]:
            lines.append(f"- {changed_text}")

        lines.extend([
            "",
            f"**Review Reason:** {group['review_reason']}",
            "",
        ])

    lines.extend([
        "## Limitations",
        "",
    ])

    for limitation in report["limitations"]:
        lines.append(f"- {limitation}")

    lines.extend([
        "",
        "**Disclaimer:** This is an automated preliminary analysis, "
        "not a legal compliance determination.",
        "",
    ])

    output_path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    print("Readable report generated successfully!")
    print("Saved to:", output_path)
    print("Evidence records included:", len(records))
    print("Unmatched groups included:", len(unmatched))


if __name__ == "__main__":
    main()
