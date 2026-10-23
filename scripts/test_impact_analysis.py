
import json
from pathlib import Path

from app.impact_engine.semantic_matcher import match_regulation_to_policies



from app.impact_engine.impact_analyzer import (
    analyze_impact,
    match_change_to_policy,
    extract_change_context,
    is_formatting_only_change,
    group_nearby_changes,
    extract_group_context,
)


from app.impact_engine.policy_loader import (
    load_company_policy,
    extract_policy_sections,
    find_relevant_policy_sections,
)



report_path = Path("data/reports/dpdp_2025_evidence_report.json")

with report_path.open("r", encoding="utf-8") as file:
    report = json.load(file)

changes = report["changes"]

print("Total regulatory rule pairs:", len(changes))


for change in changes:
    result = analyze_impact(change)

    print(
        f"Draft Rule {result['draft_rule_number']} "
        f"→ Final Rule {result['final_rule_number']} "
        f"| Impact: {result['impact_level']}"
    )


policy_text = load_company_policy()
policy_sections = extract_policy_sections(policy_text)

matching_sections = find_relevant_policy_sections(
    policy_sections,
    "consent",
)

print("\nCompany Policy Matching Test")
print("Search keyword: consent")
print("Matching policy sections:", len(matching_sections))

for title in matching_sections:
    print("-", title)



print("\nReal Regulatory Change to Policy Matching")

first_change = changes[0]

matches = match_change_to_policy(
    first_change,
    policy_sections,
)

print(
    "Regulatory Rule:",
    first_change["draft_rule_number"],
    "->",
    first_change["final_rule_number"],
)

print("Potentially matching policy sections:", len(matches))

for title, keywords in matches.items():
    print(title, "->", keywords)



print("\nReal Regulatory Semantic Matching")

final_regulatory_text = first_change["final_source"]["text"]

semantic_matches = match_regulation_to_policies(
    final_regulatory_text,
    policy_sections,
)

print(
    "Regulatory Rule:",
    first_change["draft_rule_number"],
    "->",
    first_change["final_rule_number"],
)

print("Top 3 potentially relevant company policies:")

for match in semantic_matches[:3]:
    print(
        match["policy_section"],
        "->",
        match["similarity_score"],
    )


print("\nDetected Regulatory Differences")

detected_differences = first_change["detected_changes"]

print("Number of differences:", len(detected_differences))

if detected_differences:
    first_difference = detected_differences[0]

    print("Available difference fields:")
    print(list(first_difference.keys()))

    print("First difference:")
    print(first_difference)
else:
    print("No textual differences found.")



print("\nSemantic Matching Using Regulatory Change Context")

meaningful_differences = [
    difference
    for difference in first_change["detected_changes"]
    if not is_formatting_only_change(difference)
]

print("Non-formatting differences:", len(meaningful_differences))

if meaningful_differences:
    difference = meaningful_differences[0]

    context = extract_change_context(first_change, difference)

    print("Changed text:", difference["final_text"])
    print("Regulatory context:", context)

    if context.strip():
        context_matches = match_regulation_to_policies(
            context,
            policy_sections,
        )

        print("\nTop 3 potentially relevant policies:")

        for match in context_matches[:3]:
            print(
                match["policy_section"],
                "->",
                match["similarity_score"],
            )
    else:
        print("No regulatory context available.")
else:
    print("No non-formatting differences found.")



print("\nAll Non-Formatting Differences — Rule 3")

for index, difference in enumerate(meaningful_differences, start=1):
    context = extract_change_context(first_change, difference)

    print(f"\nDifference {index}")
    print("Operation:", difference["operation"])
    print("Draft text:", repr(difference["draft_text"]))
    print("Final text:", repr(difference["final_text"]))

    if not context.strip():
        print("No regulatory context available.")
        continue

    matches = match_regulation_to_policies(
        context,
        policy_sections,
    )

    print("Top 2 potentially relevant policies:")

    for match in matches[:2]:
        print(
            match["policy_section"],
            "->",
            match["similarity_score"],
        )


print("\nGrouped Regulatory Change Semantic Matching")

change_groups = group_nearby_changes(first_change)

print("Number of groups:", len(change_groups))

for index, group in enumerate(change_groups, start=1):
    context = extract_group_context(first_change, group)

    print(f"\nGroup {index}")
    print("Grouped changes:", [item["final_text"] for item in group])

    if not context.strip():
        print("No regulatory context available.")
        continue

    matches = match_regulation_to_policies(
        context,
        policy_sections,
    )

    print("Top 3 potentially relevant company policies:")

    for match in matches[:3]:
        print(
            match["policy_section"],
            "->",
            match["similarity_score"],
        )





