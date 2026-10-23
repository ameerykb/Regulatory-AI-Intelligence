
from functools import lru_cache

from sentence_transformers import SentenceTransformer, util
from app.impact_engine.impact_analyzer import (
    group_nearby_changes,
    extract_group_context,
)


@lru_cache(maxsize=1)
def get_semantic_model():
    """Load the local embedding model once and reuse it."""
    return SentenceTransformer(
        "sentence-transformers/all-MiniLM-L6-v2",
        device="cpu",
    )


def calculate_similarity(text_a: str, text_b: str) -> float:
    """Calculate semantic similarity between two texts."""

    if not text_a.strip() or not text_b.strip():
        return 0.0

    model = get_semantic_model()

    embeddings = model.encode(
        [text_a, text_b],
        convert_to_tensor=True,
    )

    similarity = util.cos_sim(
        embeddings[0],
        embeddings[1],
    ).item()

    return round(float(similarity), 4)


def match_regulation_to_policies(
    regulatory_text: str,
    policy_sections: dict,
) -> list[dict]:
    """Rank company policy sections by semantic similarity."""

    if not regulatory_text.strip():
        return []

    results = []

    for title, content in policy_sections.items():
        similarity = calculate_similarity(
            regulatory_text,
            f"{title}. {content}",
        )

        results.append({
            "policy_section": title,
            "similarity_score": similarity,
        })

    results.sort(
        key=lambda item: item["similarity_score"],
        reverse=True,
    )

    return results


def match_change_groups_to_policies(
    change: dict,
    policy_sections: dict,
) -> list[dict]:
    """Find potentially relevant policies for grouped regulatory changes."""

    groups = group_nearby_changes(change)
    results = []

    for index, group in enumerate(groups, start=1):
        context = extract_group_context(change, group)

        if not context.strip():
            continue

        matches = match_regulation_to_policies(
            context,
            policy_sections,
        )
        
        for match in matches:
            match["similarity_label"] = classify_policy_similarity(
                match["similarity_score"]
            )


        
        filtered_matches = filter_policy_matches(matches)
        
        review_reason = (
            "Potential policy matches identified for human review."
            if filtered_matches
            else "No policy match met the preliminary similarity threshold. Manual review required."
        )


        results.append({
            "group_number": index,
            "changed_texts": [
                difference["final_text"]
                for difference in group
            ],
            "regulatory_context": context,
            "policy_matches": matches,
            "filtered_policy_matches": filtered_matches,
            "assessment_status": "preliminary",
            "review_reason": review_reason,
        })


    return results


def classify_policy_similarity(score: float) -> str:
    """Assign a preliminary label to a semantic similarity score."""

    if score >= 0.50:
        return "stronger_semantic_match"

    if score >= 0.35:
        return "moderate_semantic_match"

    return "weak_semantic_match"


def filter_policy_matches(
    matches: list[dict],
    minimum_score: float = 0.35,
) -> list[dict]:
    """Return policy matches meeting the minimum similarity score."""

    return [
        match
        for match in matches
        if match["similarity_score"] >= minimum_score
    ]


def summarize_policy_impact(
    changes: list[dict],
    policy_sections: dict,
) -> dict:
    """Summarize preliminary policy matching across aligned rules."""

    summary = {
        "aligned_rule_pairs": len(changes),
        "total_change_groups": 0,
        "groups_with_potential_matches": 0,
        "groups_requiring_manual_review": 0,
        "rule_pairs_without_change_groups": 0,
    }

    for change in changes:
        results = match_change_groups_to_policies(
            change,
            policy_sections,
        )

        if not results:
            summary["rule_pairs_without_change_groups"] += 1

        for result in results:
            summary["total_change_groups"] += 1

            if result["filtered_policy_matches"]:
                summary["groups_with_potential_matches"] += 1
            else:
                summary["groups_requiring_manual_review"] += 1

    return summary




