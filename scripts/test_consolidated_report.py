import json
from pathlib import Path

report_path = Path(
    "data/reports/dpdp_2025_consolidated_report.json"
)

with report_path.open("r", encoding="utf-8") as file:
    report = json.load(file)

checks = {
    "Correct report type": (
        report.get("report_type")
        == "consolidated_regulatory_impact_report"
    ),
    "17 regulatory rule pairs": (
        len(report.get("regulatory_changes", [])) == 17
    ),
    "69 evidence records": (
        len(report.get("evidence_records", [])) == 69
    ),
    "7 unmatched groups": (
        len(report.get("manual_review_groups", [])) == 7
    ),
    "Limitations documented": (
        bool(report.get("limitations"))
    ),
}

print("=" * 55)
print("CONSOLIDATED REPORT VALIDATION")
print("=" * 55)

for name, passed in checks.items():
    print(f"{name}: {'PASS' if passed else 'FAIL'}")

if all(checks.values()):
    print("\nALL 5 VALIDATION CHECKS PASSED")
else:
    raise SystemExit("\nREPORT VALIDATION FAILED")
