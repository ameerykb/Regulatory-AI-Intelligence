import subprocess
import sys

PIPELINE_STAGES = [
    "scripts.generate_evidence_report",
    "scripts.generate_policy_impact_report",
    "scripts.generate_impact_evidence_report",
    "scripts.generate_consolidated_report",
    "scripts.generate_readable_report",
]

print("=" * 55)
print("REGULATORY AI - END-TO-END PIPELINE TEST")
print("=" * 55)

for stage_number, module in enumerate(PIPELINE_STAGES, start=1):
    print(f"\nRunning stage {stage_number}: {module}", flush=True)

    result = subprocess.run(
        [sys.executable, "-m", module],
        check=False,
    )

    if result.returncode != 0:
        print(f"\nFAILED: {module}")
        sys.exit(1)

    print(f"PASSED: {module}")

print("\n" + "=" * 55)
print("ALL 5 PIPELINE STAGES PASSED")
print("=" * 55)
