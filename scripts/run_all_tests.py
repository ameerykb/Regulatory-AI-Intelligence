import subprocess
import sys

TEST_MODULES = [
    "scripts.test_report_pipeline",
    "scripts.test_consolidated_report",
]

print("=" * 55)
print("REGULATORY AI - AUTOMATED SYSTEM TESTS")
print("=" * 55)

for test_number, module in enumerate(TEST_MODULES, start=1):
    print(
        f"\nRunning test {test_number}: {module}",
        flush=True
    )

    result = subprocess.run(
        [sys.executable, "-m", module],
        check=False,
    )

    if result.returncode != 0:
        print(f"\nFAILED: {module}")
        sys.exit(1)

    print(f"PASSED: {module}")

print("\n" + "=" * 55)
print("ALL AUTOMATED SYSTEM TESTS PASSED")
print("=" * 55)
