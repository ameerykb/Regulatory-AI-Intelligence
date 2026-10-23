
def analyze_impact(change: dict) -> dict:
    """Create a preliminary impact assessment for a regulatory change."""

    draft_rule = change["draft_rule_number"]
    final_rule = change["final_rule_number"]
    change_count = change["change_count"]

    
    if change_count == 0:
        impact_level = "low"
        impact_reason = "No textual differences were detected."

    elif change_count <= 3:
        impact_level = "medium"
        impact_reason = (
            "A small number of textual differences were detected "
            "and should be reviewed."
        )

    else:
        impact_level = "high"
        impact_reason = (
            "Multiple textual differences were detected. "
            "Detailed human review is recommended."
        )


    return {
        "draft_rule_number": draft_rule,
        "final_rule_number": final_rule,
        "impact_level": impact_level,
        "impact_reason":impact_reason,
        "change_count": change_count,
        "requires_human_review": True,
        "assessment_status": "preliminary",
    }


import re


def extract_change_keywords(change: dict) -> list[str]:
    """Extract basic keywords from detected regulatory differences."""

    detected_changes = change.get("detected_changes", [])

    if not isinstance(detected_changes, list):
        return []

    texts = []

    for difference in detected_changes:
        if not isinstance(difference, dict):
            continue

        for value in difference.values():
            if isinstance(value, str):
                texts.append(value)

    combined_text = " ".join(texts).lower()

    words = re.findall(r"\b[a-z]{4,}\b", combined_text)

    
    stopwords = {
        "that", "this", "with", "from", "shall", "have",
        "been", "were", "which", "their", "there", "under",
        "rule", "rules", "text", "replace", "insert", "delete",
        "purposes", "purpose", "such", "other", "more",
        "than", "into", "each", "also", "same", "only",
        "following", "provided", "specified", "including",
    }

    keywords = []

    for word in words:
        if word not in stopwords and word not in keywords:
            keywords.append(word)

    return keywords[:20]


def match_change_to_policy(
    change: dict,
    policy_sections: dict,
) -> dict:
    """Find policy sections sharing keywords with a regulatory change."""

    keywords = extract_change_keywords(change)

    matches = {}

    for title, content in policy_sections.items():
        policy_text = f"{title} {content}".lower()
        policy_words = set(re.findall(r"\b[a-z]+\b", policy_text))

        matched_keywords = [
            keyword
            for keyword in keywords
            if keyword in policy_words
        ]

        if matched_keywords:
            matches[title] = matched_keywords

    return matches




def extract_changed_regulatory_text(change: dict) -> str:
    """Extract final-side text, ignoring formatting-only differences."""

    detected_changes = change.get("detected_changes", [])

    changed_texts = []

    for difference in detected_changes:
        if not isinstance(difference, dict):
            continue

        draft_text = difference.get("draft_text", "")
        final_text = difference.get("final_text", "")

        if not isinstance(draft_text, str) or not isinstance(final_text, str):
            continue

        draft_words = re.findall(r"\w+", draft_text.lower())
        final_words = re.findall(r"\w+", final_text.lower())

        if draft_words == final_words:
            continue

        if final_text.strip():
            changed_texts.append(final_text.strip())

    return " ".join(changed_texts)


def extract_change_context(
    change: dict,
    difference: dict,
    window: int = 20,
) -> str:
    """Extract surrounding words from the final regulatory rule."""

    final_text = change["final_source"]["text"]
    final_words = final_text.split()

    word_range = difference.get("final_word_range", [])

    if len(word_range) != 2:
        return ""

    start, end = word_range

    context_start = max(0, start - window)
    context_end = min(len(final_words), end + window)

    return " ".join(final_words[context_start:context_end])


def is_formatting_only_change(difference: dict) -> bool:
    """Check whether a replacement changes only formatting."""

    if difference.get("operation") != "replace":
        return False

    draft_text = difference.get("draft_text", "")
    final_text = difference.get("final_text", "")

    if not isinstance(draft_text, str) or not isinstance(final_text, str):
        return False

    draft_words = re.findall(r"\w+", draft_text.lower())
    final_words = re.findall(r"\w+", final_text.lower())

    return draft_words == final_words


def group_nearby_changes(
    change: dict,
    max_gap: int = 20,
) -> list[list[dict]]:
    """Group nearby non-formatting regulatory differences."""

    differences = [
        difference
        for difference in change.get("detected_changes", [])
        if not is_formatting_only_change(difference)
        and len(difference.get("final_word_range", [])) == 2
    ]

    differences.sort(
        key=lambda item: item["final_word_range"][0]
    )

    groups = []

    for difference in differences:
        start, end = difference["final_word_range"]

        if not groups:
            groups.append([difference])
            continue

        previous_end = groups[-1][-1]["final_word_range"][1]

        if start - previous_end <= max_gap:
            groups[-1].append(difference)
        else:
            groups.append([difference])

    return groups


def extract_group_context(
    change: dict,
    group: list[dict],
    window: int = 20,
) -> str:
    """Extract one surrounding context for a group of changes."""

    if not group:
        return ""

    final_text = change["final_source"]["text"]
    final_words = final_text.split()

    start = min(
        difference["final_word_range"][0]
        for difference in group
    )

    end = max(
        difference["final_word_range"][1]
        for difference in group
    )

    context_start = max(0, start - window)
    context_end = min(len(final_words), end + window)

    return " ".join(final_words[context_start:context_end])




