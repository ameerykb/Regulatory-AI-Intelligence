"""
LangGraph orchestration for regulatory intelligence.

The existing RAG pipeline performs retrieval, generation,
citation validation, and claim verification.

LangGraph controls execution and review routing.
"""

from typing import Any, TypedDict

from langgraph.graph import StateGraph, START, END

from app.rag_engine.rag_pipeline import answer_regulatory_question


class RegulatoryState(TypedDict, total=False):
    question: str
    document_version: str
    top_k: int

    result: dict[str, Any]
    review_status: str
    review_reasons: list[str]
    workflow_path: list[str]


def validate_input(state: RegulatoryState) -> dict:
    question = state.get("question", "")

    if not isinstance(question, str) or not question.strip():
        raise ValueError("Question cannot be empty.")

    version = state.get("document_version", "final_2025")

    if version not in ("draft_2025", "final_2025"):
        raise ValueError("Invalid document version.")

    top_k = state.get("top_k", 3)

    if not isinstance(top_k, int) or not 1 <= top_k <= 20:
        raise ValueError("top_k must be between 1 and 20.")

    return {
        "question": question.strip(),
        "document_version": version,
        "top_k": top_k,
        "workflow_path": ["validate_input"],
    }


def run_rag_pipeline(state: RegulatoryState) -> dict:
    result = answer_regulatory_question(
        question=state["question"],
        document_version=state["document_version"],
        top_k=state["top_k"],
    )

    return {
        "result": result,
        "workflow_path": state["workflow_path"] + ["run_rag_pipeline"],
    }


def route_result(state: RegulatoryState) -> str:
    result = state["result"]

    if result.get("status") != "generated_requires_review":
        return "blocked_or_insufficient"

    return "assess_verification"


def assess_verification(state: RegulatoryState) -> dict:
    result = state["result"]

    claims = result.get("claim_verification") or {}

    reasons = []

    uncited = claims.get("total_uncited_claims", 0)

    if uncited:
        reasons.append(
            f"{uncited} claim(s) lack source citations."
        )

    for claim in claims.get("claims", []):
        if not isinstance(claim, dict):
            continue

        verdict = str(
            claim.get("verdict")
            or claim.get("status")
            or ""
        ).upper()

        if verdict and verdict != "SUPPORTED":
            reasons.append(
                f"Claim verification requires attention: {verdict}"
            )

    if not reasons:
        reasons.append(
            "Regulatory answers require human approval "
            "even when automated checks pass."
        )

    return {
        "review_status": "human_review_required",
        "review_reasons": list(dict.fromkeys(reasons)),
        "workflow_path": (
            state["workflow_path"] + ["assess_verification"]
        ),
    }


def handle_blocked_result(state: RegulatoryState) -> dict:
    status = state["result"].get("status", "unknown")

    return {
        "review_status": "blocked_or_insufficient",
        "review_reasons": [
            f"Pipeline stopped with status: {status}"
        ],
        "workflow_path": (
            state["workflow_path"] + ["handle_blocked_result"]
        ),
    }


def finalize(state: RegulatoryState) -> dict:
    return {
        "workflow_path": state["workflow_path"] + ["finalize"]
    }


def build_regulatory_graph():
    builder = StateGraph(RegulatoryState)

    builder.add_node("validate_input", validate_input)
    builder.add_node("run_rag_pipeline", run_rag_pipeline)
    builder.add_node("assess_verification", assess_verification)
    builder.add_node("handle_blocked_result", handle_blocked_result)
    builder.add_node("finalize", finalize)

    builder.add_edge(START, "validate_input")
    builder.add_edge("validate_input", "run_rag_pipeline")

    builder.add_conditional_edges(
        "run_rag_pipeline",
        route_result,
        {
            "assess_verification": "assess_verification",
            "blocked_or_insufficient": "handle_blocked_result",
        },
    )

    builder.add_edge("assess_verification", "finalize")
    builder.add_edge("handle_blocked_result", "finalize")
    builder.add_edge("finalize", END)

    return builder.compile()


regulatory_graph = build_regulatory_graph()


def run_regulatory_workflow(
    question: str,
    document_version: str = "final_2025",
    top_k: int = 3,
) -> dict:
    """Execute the regulatory workflow using LangGraph."""

    state = regulatory_graph.invoke(
        {
            "question": question,
            "document_version": document_version,
            "top_k": top_k,
        }
    )

    result = dict(state["result"])

    result["workflow"] = {
        "framework": "LangGraph",
        "review_status": state["review_status"],
        "review_reasons": state["review_reasons"],
        "execution_path": state["workflow_path"],
    }

    return result