
"""Streamlit dashboard for regulatory change intelligence."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
import json
import csv
import io
import streamlit as st
from app.review_engine.review_store import save_review, load_reviews

from app.rag_engine.langgraph_workflow import run_regulatory_workflow


REPORT_PATH = Path("data/reports/dpdp_2025_evidence_report.json")



def load_impact_evidence_report():
    """Load the generated regulatory impact evidence report."""

    report_path = Path(
        "data/reports/dpdp_2025_impact_evidence_report.json"
    )

    if not report_path.exists():
        return None

    with report_path.open("r", encoding="utf-8") as file:
        return json.load(file)


st.set_page_config(
    page_title="Regulatory Change Intelligence",
    page_icon="⚖️",
    layout="wide",
)

st.title("⚖️ AI Regulatory Change Intelligence")
st.caption("DPDP Rules 2025 — Draft vs Final Analysis")


st.subheader("📄 Download Regulatory Impact Report")

readable_report_path = Path(
    "data/reports/dpdp_2025_readable_report.md"
)

if readable_report_path.exists():
    report_text = readable_report_path.read_text(
        encoding="utf-8"
    )

    st.download_button(
        label="📥 Download Full Regulatory Impact Report",
        data=report_text.encode("utf-8"),
        file_name="dpdp_2025_regulatory_impact_report.md",
        mime="text/markdown",
        key="download_readable_impact_report",
    )

    st.caption(
        "Includes 69 preliminary evidence records, "
        "review recommendations, and 7 unmatched change groups."
    )

else:
    st.warning(
        "Readable report not found. "
        "Run: python -m scripts.generate_readable_report"
    )


st.subheader("📦 Download Consolidated JSON Report")

consolidated_report_path = Path(
    "data/reports/dpdp_2025_consolidated_report.json"
)

if consolidated_report_path.exists():
    st.download_button(
        label="📥 Download Consolidated JSON",
        data=consolidated_report_path.read_bytes(),
        file_name="dpdp_2025_consolidated_report.json",
        mime="application/json",
        key="download_consolidated_json",
    )
else:
    st.warning(
        "Consolidated report not found. "
        "Run: python -m scripts.generate_consolidated_report"
    )


st.subheader("📊 Regulatory Impact Evidence Overview")

impact_evidence_report = load_impact_evidence_report()

if impact_evidence_report is not None:
    evidence_summary = impact_evidence_report["summary"]
    priority_summary = impact_evidence_report["review_priority_summary"]

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Evidence Records",
            evidence_summary["total_evidence_records"],
        )

    with col2:
        st.metric(
            "Review First",
            priority_summary["review_first"],
        )

    with col3:
        st.metric(
            "Standard Review",
            priority_summary["standard_review"],
        )

    st.caption(
        "Preliminary semantic matching results. "
        "All recommendations require human review."
    )

else:
    st.warning(
        "Impact evidence report not found. "
        "Generate the report before viewing this section."
    )


st.subheader("⚠️ Unmatched Regulatory Changes")

if impact_evidence_report is not None:
    manual_review_groups = impact_evidence_report.get(
        "manual_review_groups", []
    )

    st.write(
        f"**{len(manual_review_groups)} change groups** "
        "require manual policy assessment."
    )

    if manual_review_groups:
        for group in manual_review_groups:
            draft_rule = group["draft_rule_number"]
            final_rule = group["final_rule_number"]
            group_number = group["group_number"]

            with st.expander(
                f"Draft Rule {draft_rule} → Final Rule {final_rule} "
                f"| Change Group {group_number}"
            ):
                st.write("**Detected regulatory changes:**")

                for changed_text in group["changed_texts"]:
                    st.write(f"- {changed_text}")

                st.write("**Review reason:**")
                st.info(group["review_reason"])

                st.warning(
                    "Human assessment required. "
                    "No policy match passed the preliminary "
                    "semantic similarity threshold."
                )
    else:
        st.success("No unmatched change groups in this report.")



st.subheader("🧑‍⚖️ Evidence Review Status")

if impact_evidence_report is not None:
    evidence_records_for_review = impact_evidence_report.get(
        "evidence_records", []
    )

    pending_evidence = sum(
        1
        for record in evidence_records_for_review
        if record.get("requires_human_review", False)
    )

    unmatched_groups = len(
        impact_evidence_report.get("manual_review_groups", [])
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Evidence Awaiting Review",
            pending_evidence,
        )

    with col2:
        st.metric(
            "Unmatched Groups to Assess",
            unmatched_groups,
        )

    with col3:
        st.metric(
            "Evidence Records Generated",
            len(evidence_records_for_review),
        )

    st.info(
        "These are preliminary evidence records. "
        "Individual evidence approval tracking is not yet implemented. "
        "Existing rule-pair reviews are tracked separately."
    )



st.subheader("📑 Company Policy Impact Summary")

if impact_evidence_report is not None:
    evidence_records_for_policy = impact_evidence_report.get(
        "evidence_records", []
    )

    policy_counts = {}

    for record in evidence_records_for_policy:
        policy_name = record["policy_section"]

        policy_counts[policy_name] = (
            policy_counts.get(policy_name, 0) + 1
        )

    if policy_counts:
        policy_summary = [
            {
                "Policy Section": policy_name,
                "Potential Matches": count,
            }
            for policy_name, count in policy_counts.items()
        ]

        policy_summary.sort(
            key=lambda item: item["Potential Matches"],
            reverse=True,
        )

        st.dataframe(
            policy_summary,
            use_container_width=True,
            hide_index=True,
        )


        
        st.write("**Potential Regulatory Matches by Policy Section**")

        chart_data = {
            item["Policy Section"]: item["Potential Matches"]
            for item in policy_summary
        }

        st.bar_chart(
            chart_data,
            x_label="Company Policy Section",
            y_label="Potential Matches",
        )

        st.caption(
            "Counts represent preliminary semantic matches, "
            "not confirmed compliance gaps or legal risk."
        )
    else:
        st.info("No policy evidence records available.")


st.subheader("📋 Regulatory Impact Evidence Records")

if impact_evidence_report is not None:
    evidence_records = impact_evidence_report.get(
        "evidence_records", []
    )

    priority_filter = st.selectbox(
        "Filter by review priority",
        [
            "All",
            "Review First",
            "Standard Review",
            "Manual Assessment",
        ],
        key="evidence_priority_filter",
    )

    priority_mapping = {
        "Review First": "review_first",
        "Standard Review": "standard_review",
        "Manual Assessment": "manual_assessment",
    }

    if priority_filter == "All":
        filtered_records = evidence_records
    else:
        selected_priority = priority_mapping[priority_filter]

        filtered_records = [
            record
            for record in evidence_records
            if record.get("review_recommendation", {}).get(
                "review_priority"
            ) == selected_priority
        ]

    evidence_search = st.text_input(
        "Search evidence records",
        placeholder="Search by policy, rule number, or regulatory text...",
        key="evidence_search",
    )

    if evidence_search.strip():
        search_term = evidence_search.strip().lower()

        filtered_records = [
            record
            for record in filtered_records
            if search_term in record["policy_section"].lower()
            or search_term in str(record["draft_rule_number"]).lower()
            or search_term in str(record["final_rule_number"]).lower()
            or search_term in record["regulatory_context"].lower()
        ]



    st.write(
        f"Showing **{len(filtered_records)}** "
        f"of **{len(evidence_records)}** evidence records."
    )

    
    csv_buffer = io.StringIO()

    csv_writer = csv.writer(csv_buffer)

    csv_writer.writerow([
        "Draft Rule",
        "Final Rule",
        "Policy Section",
        "Similarity Score",
        "Review Priority",
        "Regulatory Context",
        "Company Policy Text",
        "Review Recommendation",
        "Source Metadata Complete",
        "Policy Evidence Complete",
    ])

    for record in filtered_records:
        recommendation = record.get(
            "review_recommendation", {}
        )

        csv_writer.writerow([
            record["draft_rule_number"],
            record["final_rule_number"],
            record["policy_section"],
            record["similarity_score"],
            recommendation.get("review_priority", ""),
            record["regulatory_context"],
            record["policy_text"],
            recommendation.get("recommendation", ""),
            record["source_validation"]["all_sources_valid"],
            record["policy_validation"]["all_policy_evidence_valid"],
        ])

    st.download_button(
        label="📥 Download Evidence Records CSV",
        data=csv_buffer.getvalue().encode("utf-8-sig"),
        file_name="regulatory_impact_evidence.csv",
        mime="text/csv",
        key="download_impact_evidence_csv",
    )


    for index, record in enumerate(filtered_records, start=1):
        recommendation = record.get(
            "review_recommendation", {}
        )

        title = (
            f"{index}. Draft Rule {record['draft_rule_number']} "
            f"→ Final Rule {record['final_rule_number']} "
            f"| {record['policy_section']}"
        )

        with st.expander(title):
            st.write("**Policy section:**")
            st.write(record["policy_section"])

            st.write("**Similarity score:**")
            st.write(record["similarity_score"])

            
            st.write("**Evidence Validation:**")

            source_valid = record.get(
                "source_validation", {}
            ).get("all_sources_valid", False)

            policy_valid = record.get(
                "policy_validation", {}
            ).get("all_policy_evidence_valid", False)

            if source_valid:
                st.success("Regulatory source metadata: Complete")
            else:
                st.error("Regulatory source metadata: Incomplete")

            if policy_valid:
                st.success("Company policy evidence: Complete")
            else:
                st.error("Company policy evidence: Incomplete")


            st.write("**Review priority:**")
            st.write(
                recommendation.get(
                    "review_priority", "Not available"
                )
            )

            st.write("**Regulatory change context:**")
            st.write(record["regulatory_context"])

            st.write("**Company policy text:**")
            st.write(record["policy_text"])

            st.write("**Recommended review action:**")
            st.info(
                recommendation.get(
                    "recommendation",
                    "No recommendation available.",
                )
            )

            st.write("**Recommendation reason:**")
            st.write(
                recommendation.get(
                    "reason", "Not available"
                )
            )

            st.caption(
                "Preliminary AI-generated evidence. "
                "Human approval is required."
            )




if not REPORT_PATH.exists():
    st.error("Report not found. Generate the evidence report first.")
    st.stop()

with REPORT_PATH.open("r", encoding="utf-8") as file:
    report = json.load(file)

st.subheader("Regulatory Change Overview")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Analyzed Rule Pairs", report["total_changes"])

with col2:
    st.metric("Human Reviews Required", report["review_required_count"])

with col3:
    st.metric("Pending Alignments", report["pending_alignment_count"])

st.divider()

st.subheader("Detected Regulatory Changes")

st.subheader("Explore Regulatory Changes")

changes = report["changes"]

# Filter regulatory changes by human review status

review_records = load_reviews()

latest_review_status = {}

for review in review_records:
    rule_pair = (
        review["draft_rule_number"],
        review["final_rule_number"],
    )
    latest_review_status[rule_pair] = review["status"]


review_filter = st.selectbox(
    "Filter by Human Review Status",
    options=[
        "All",
        "Not Reviewed",
        "Under Review",
        "Approved",
        "Rejected",
        "Needs Revision",
    ],
    key="review_status_filter",
)


if review_filter != "All":
    selected_status = review_filter.lower().replace(" ", "_")

    changes = [
        change
        for change in changes
        if latest_review_status.get(
            (
                change["draft_rule_number"],
                change["final_rule_number"],
            ),
            "not_reviewed",
        ) == selected_status
    ]




def clear_search():
    """Reset regulatory search and review filters."""
    st.session_state.search_query = ""
    st.session_state.review_status_filter = "All"


search_query = st.text_input(
    "Search regulatory changes",
    placeholder="Search by rule title or keyword...",
    key="search_query",
)

st.button(
    "Clear Filters",
    on_click=clear_search,
)



search_mode = st.radio(
    "Search within",
    options=["Rule Titles Only", "Full Regulatory Text"],
    horizontal=True,
)



if search_query.strip():
    keyword = search_query.strip().lower()

    if search_mode == "Rule Titles Only":
        changes = [
            change
            for change in changes
            if keyword in change["draft_title"].lower()
            or keyword in change["final_title"].lower()
        ]
    else:
        changes = [
            change
            for change in changes
            if keyword in change["draft_title"].lower()
            or keyword in change["final_title"].lower()
            or keyword in change["draft_source"]["text"].lower()
            or keyword in change["final_source"]["text"].lower()
        ]


st.write(
    f"**Showing {len(changes)} of "
    f"{len(report['changes'])} regulatory rule pairs.**"
)
if not changes:
    st.warning("No regulatory rule pairs match the selected filters. "
        "Click 'Clear Filters' to display all rules.")
    selected_change = None
else:
    selected_change = changes[0]



if changes:
    selected_index = st.selectbox(
        "Select a regulatory rule",
        options=range(len(changes)),
        format_func=lambda i: (
            f"Draft Rule {changes[i]['draft_rule_number']} → "
            f"Final Rule {changes[i]['final_rule_number']}"
        ),
    )

    selected_change = changes[selected_index]
else:
    selected_change = None
    st.info("No rule selected. Clear the filters to review a regulatory change.")
if selected_change is not None:


    st.write("**Draft Title:**", selected_change["draft_title"])
    st.write("**Final Title:**", selected_change["final_title"])
    st.write("**Change Status:**", selected_change["change_status"])
    st.write("**Detected Differences:**", selected_change["change_count"])
    st.write("**Review Status:**", selected_change["review_status"])

    draft_col, final_col = st.columns(2)

    with draft_col:
        st.subheader("Draft Regulation")
        st.write(selected_change["draft_source"]["text"])

    with final_col:
        st.subheader("Final Regulation")
        st.write(selected_change["final_source"]["text"])

    st.subheader("Detected Text Differences")


    for index, difference in enumerate(
        selected_change["detected_changes"],
        start=1,
    ):
        operation = difference["operation"]

        if operation == "insert":
            color = "green"
            label = "ADDED"
        elif operation == "delete":
            color = "red"
            label = "REMOVED"
        elif operation == "replace":
            color = "orange"
            label = "MODIFIED"
        else:
            color = "gray"
            label = operation.upper()

        with st.expander(f"Difference {index}: {label}"):
            st.markdown(f":{color}[**{label}**]")

            st.write(
                "**Draft text:**",
                difference["draft_text"] or "(No text)",
            )

            st.write(
                "**Final text:**",
                difference["final_text"] or "(No text)",
            )



st.divider()

st.subheader("Export Regulatory Changes")

output = io.StringIO()

writer = csv.writer(output)

writer.writerow([
    "Draft Rule",
    "Final Rule",
    "Draft Title",
    "Final Title",
    "Change Status",
    "Detected Differences",
    "Review Status",
])

for item in report["changes"]:
    writer.writerow([
        item["draft_rule_number"],
        item["final_rule_number"],
        item["draft_title"],
        item["final_title"],
        item["change_status"],
        item["change_count"],
        item["review_status"],
    ])

st.download_button(
    label="Download Change Summary (CSV)",
    data=output.getvalue().encode("utf-8-sig"),
    file_name="dpdp_2025_change_summary.csv",
    mime="text/csv",
)


st.divider()
if selected_change is not None:
    st.subheader("Human Review and Approval")

    st.write(
        "Review the selected regulatory change and record "
        "your assessment."
    )

    reviewer_name = st.text_input(
        "Reviewer Name",
        placeholder="Enter your name",
    )

    review_decision = st.selectbox(
        "Review Decision",
        options=[
            "under_review",
            "approved",
            "rejected",
            "needs_revision",
        ],  
     )

    review_comment = st.text_area(
        "Reviewer Comment",
        placeholder="Explain your review decision...",
    )

    def reset_confirmation():
        st.session_state.review_confirmed = False


    confirm_review = st.checkbox(
        "I have reviewed the regulatory evidence and confirm my decision.",
        key="review_confirmed",
    )
    if st.button("Save Review Decision"):
        if not confirm_review:
            st.error("Please Confirm Your review before saving.")
        elif not reviewer_name.strip():
            st.error("Please enter the reviewer name.")

        elif not review_comment.strip():
            st.error("Please enter a review comment.")

        else:
            try:
                saved_review = save_review(
                    draft_rule_number=selected_change["draft_rule_number"],
                    final_rule_number=selected_change["final_rule_number"],
                    status=review_decision,
                    reviewer=reviewer_name,
                    comment=review_comment,
                )

                st.success(
                    "Review decision saved successfully! "
                    f"Draft Rule {saved_review['draft_rule_number']} → "
                    f"Final Rule {saved_review['final_rule_number']}"
                )

            except (OSError, ValueError) as error:
                st.error(f"Unable to save review: {error}")



st.divider()

st.subheader("Human Review Progress")

all_reviews = load_reviews()

latest_decisions = {}

for review in all_reviews:
    rule_pair = (
        review["draft_rule_number"],
        review["final_rule_number"],
    )
    latest_decisions[rule_pair] = review["status"]

valid_rule_pairs = {
    (change["draft_rule_number"], change["final_rule_number"])
    for change in report["changes"]
}

reviewed_count = sum(
    1
    for rule_pair, status in latest_decisions.items()
    if rule_pair in valid_rule_pairs
    and status in {"approved", "rejected"}
)


total_rules = len(valid_rule_pairs)

completion_percentage = (
    (reviewed_count / total_rules) * 100
    if total_rules
    else 0
)

st.progress(
    completion_percentage / 100
)

st.write(f"**Review Completion: {completion_percentage:.1f}%**")


st.write(
    f"**{reviewed_count} of {total_rules} rule pairs "
    "have a completed review decision.**"
)

st.caption(
    "Only approved or rejected decisions count as completed. "
    "Under-review and needs-revision decisions remain incomplete."
)

st.divider()

st.subheader("Review Status Breakdown")

status_counts = {
    "approved": 0,
    "rejected": 0,
    "under_review": 0,
    "needs_revision": 0,
    "not_reviewed": 0,
}

for rule_pair in valid_rule_pairs:
    status = latest_decisions.get(rule_pair, "not_reviewed")
    status_counts[status] += 1

status_col1, status_col2, status_col3 = st.columns(3)

with status_col1:
    st.metric("Approved", status_counts["approved"])
    st.metric("Rejected", status_counts["rejected"])

with status_col2:
    st.metric("Under Review", status_counts["under_review"])
    st.metric("Needs Revision", status_counts["needs_revision"])

with status_col3:
    st.metric("Not Reviewed", status_counts["not_reviewed"])

st.divider()
if selected_change is not None:
    st.subheader("Human Review History")

    saved_reviews = load_reviews()

    rule_reviews = [
        review
        for review in saved_reviews
        if review["draft_rule_number"] == selected_change["draft_rule_number"]
        and review["final_rule_number"] == selected_change["final_rule_number"]
    ]

    st.subheader("Latest Human Review Status")

    if rule_reviews:
        latest_review = rule_reviews[-1]

        st.write("**Current Decision:**", latest_review["status"])
        st.write("**Reviewed By:**", latest_review["reviewer"])
        st.write("**Last Reviewed:**", latest_review["reviewed_at"])
    else:
        st.write("**Current Decision:** requires_human_review")
        st.caption("No human review decision has been recorded yet.")


    if rule_reviews:
        st.write(f"**Total Reviews:** {len(rule_reviews)}")

        for review in reversed(rule_reviews):
            with st.expander(
                f"{review['status']} — {review['reviewer']}"
            ):
                st.write("**Reviewer:**", review["reviewer"])
                st.write("**Decision:**", review["status"])
                st.write("**Comment:**", review["comment"])
                st.write("**Reviewed At:**", review["reviewed_at"])
    else:
        st.info("No human reviews have been recorded for this rule.")

st.subheader("Pending Rule Alignment Reviews")

pending_reviews = report.get("pending_review", [])

st.write(
    f"**{len(pending_reviews)} rule alignments require manual review.**"
)

for review in pending_reviews:
    rule_number = review["draft_rule_number"]

    with st.expander(f"Draft Rule {rule_number} — Pending Review"):
        st.write("**Reason:**", review["reason"])
        st.write("**Relationship:**", review["relationship"])
        st.write("**Confidence:**", review["confidence_level"])

st.caption(
    "Pending alignments are not confirmed rule matches. "
    "They must be reviewed before inclusion in the analyzed changes."
)

st.info(
    "This dashboard presents automated regulatory comparisons. "
    "All findings require human verification before legal use."
)


# ============================================================
# AI REGULATORY ASSISTANT
# ============================================================

st.divider()

st.header("AI Regulatory Assistant")

st.caption(
    "Ask questions about the DPDP Rules 2025 using "
    "locally retrieved regulatory evidence."
)

rag_document_version = st.selectbox(
    "Regulatory document version",
    options=["final_2025", "draft_2025"],
    key="rag_document_version",
)

rag_question = st.text_area(
    "Enter your regulatory question",
    placeholder=(
        "Example: What are the requirements for "
        "personal data breach notification?"
    ),
    height=100,
    key="rag_question",
)

rag_submit = st.button(
    "Ask AI Assistant",
    type="primary",
    key="rag_submit",
)


# Store the latest AI response during the current session
if "rag_latest_result" not in st.session_state:
    st.session_state.rag_latest_result = None


# Store regulatory AI conversation history
if "rag_chat_history" not in st.session_state:
    st.session_state.rag_chat_history = []



if rag_submit:
    if not rag_question.strip():
        st.warning("Please enter a regulatory question.")
    else:
        with st.spinner(
            "Searching regulatory documents and generating AI response..."
        ):
            try:
                rag_result = run_regulatory_workflow(
                    question=rag_question.strip(),
                    document_version=rag_document_version,
                    top_k=3,
                )

                
                st.session_state.rag_latest_result = rag_result

                                # Save the question and AI response to chat history
                st.session_state.rag_chat_history.append(
                    {
                        "question": rag_question.strip(),
                        "document_version": rag_document_version,
                        "result": rag_result,
                    }
                )


            except Exception as error:
                st.error(
                    "The AI assistant could not complete the request. "
                    "Check that Ollama is running and try again."
                )
                st.exception(error)

# Clear the previously generated AI response
if st.button("Clear AI Response", key="rag_clear_response"):
    st.session_state.rag_latest_result = None

rag_result = st.session_state.rag_latest_result


if rag_result is not None:
    st.subheader("AI Response")
    
    source_versions = {
        source["document_version"]
        for source in rag_result.get("sources", [])
    }

    if source_versions:
        st.caption(
            "Answer based on: "
            + ", ".join(sorted(source_versions))
        )

    st.write(rag_result["answer"])

    st.caption(
        f"Pipeline status: {rag_result['status']}"
    )

        # ==========================================
    # CLAIM-LEVEL VERIFICATION PANEL
    # ==========================================
        # ==========================================
    # LANGGRAPH WORKFLOW DETAILS
    # ==========================================

    workflow = rag_result.get("workflow") or {}

    if workflow:
        with st.expander("🔄 LangGraph Workflow Details"):

            st.markdown("**Framework:**")
            st.success(workflow.get("framework", "Unknown"))

            st.markdown("**Review Status:**")
            review_status = workflow.get(
                "review_status",
                "unknown"
            )

            if review_status == "human_review_required":
                st.warning("Human Review Required")
            else:
                st.info(review_status)

            st.markdown("**Execution Path:**")

            execution_path = workflow.get(
                "execution_path", []
            )

            for index, step in enumerate(
                execution_path, start=1
            ):
                st.write(f"{index}. {step}")

            st.markdown("**Review Reasons:**")

            review_reasons = workflow.get(
                "review_reasons", []
            )

            if review_reasons:
                for reason in review_reasons:
                    st.warning(reason)
            else:
                st.info("No review reasons recorded.")
    st.markdown("### Claim-Level Verification")

    claim_data = rag_result.get("claim_verification") or {}
    claim_results = claim_data.get("claims", [])

    if claim_results:

        total_claims = claim_data.get(
            "total_claims", len(claim_results)
        )

        cited_claims = claim_data.get(
            "total_cited_claims",
            sum(
                1 for item in claim_results
                if item.get("source_numbers")
            ),
        )

        uncited_claims = claim_data.get(
            "total_uncited_claims",
            total_claims - cited_claims,
        )

        coverage = claim_data.get(
            "citation_coverage_percent",
            round(
                cited_claims / total_claims * 100, 2
            ) if total_claims else 0.0,
        )

        supported_claims = sum(
            1 for item in claim_results
            if item.get("verification", {}).get("verdict")
            == "SUPPORTED"
        )

        review_claims = total_claims - supported_claims

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Total Claims", total_claims)
        col2.metric("Cited Claims", cited_claims)
        col3.metric("Citation Coverage", f"{coverage}%")
        col4.metric("Needs Review", review_claims)

        st.caption(
            "Citation coverage measures citation presence, "
            "not legal accuracy. Automated verification "
            "requires human review."
        )

        for index, item in enumerate(claim_results, start=1):

            claim_text = item.get("claim", "")
            source_numbers = item.get("source_numbers", [])

            verification_result = (
                item.get("verification") or {}
            )

            verdict = verification_result.get(
                "verdict", "NOT_AVAILABLE"
            )

            with st.expander(
                f"Claim {index} — {verdict}"
            ):

                st.write("**Regulatory Claim:**")
                st.write(claim_text)

                st.write("**Cited Sources:**")

                if source_numbers:
                    st.write(
                        ", ".join(
                            f"Source {number}"
                            for number in source_numbers
                        )
                    )
                else:
                    st.warning("No source citation found.")

                st.write("**Verification Verdict:**")

                if verdict == "SUPPORTED":
                    st.success("AI assessment: SUPPORTED")

                elif verdict == "UNSUPPORTED":
                    st.error("AI assessment: UNSUPPORTED")

                else:
                    st.warning(
                        f"AI assessment: {verdict}"
                    )

                st.write("**Verification Reason:**")
                st.write(
                    verification_result.get(
                        "reason", "No reason provided."
                    )
                )

                evidence_quote = verification_result.get(
                    "evidence_quote", ""
                )

                if evidence_quote:
                    st.write("**Evidence Quotation:**")
                    st.info(evidence_quote)

    else:
        st.info(
            "No claim-level verification results available."
        )

    # Display AI evidence verification result
    verification = rag_result.get("verification", {})
    verdict = verification.get(
        "verdict", "NOT_AVAILABLE"
    )

    st.markdown("### Evidence Verification")

    if verdict == "SUPPORTED":


                if verdict == "SUPPORTED":
                    st.success(
                        "AI verification: SUPPORTED"
                    )

                elif verdict == "UNSUPPORTED":
                    st.error(
                        "AI verification: UNSUPPORTED"
                    )

                elif verdict == "INSUFFICIENT_EVIDENCE":
                    st.warning(
                        "AI verification: INSUFFICIENT EVIDENCE"
                    )

                else:
                    st.warning(
                        "AI verification: REVIEW REQUIRED"
                    )

                st.caption(
                    "Experimental whole-answer AI verification. "
                    "This does not establish that every claim "
                    "is accurate or legally valid."
                )


                st.warning(
                    "AI-generated regulatory analysis requires "
                    "human verification. This is not legal advice."
                )

                
                # Display retrieved regulatory sources
                rag_sources = rag_result.get("sources", [])

                if rag_sources:
                    st.subheader("Regulatory Sources")

                    for source in rag_sources:
                        with st.expander(
                            f"Source {source['source_number']} "
                            f"— Rule {source['rule_number']}"
                        ):
                            st.write(
                                f"**Document Version:** "
                                f"{source['document_version']}"
                            )

                            st.write(
                                f"**Source File:** "
                                f"{source['source_file']}"
                            )

                            st.write(
                                f"**Rule ID:** "
                                f"{source['rule_id']}"
                            )
                            
                            st.markdown("**Retrieved Regulatory Evidence:**")

                            st.text(
                                source.get(
                                    "text",
                                    "Evidence text not available."
                                )
                            )


                else:
                    st.info(
                        "No regulatory sources are available "
                        "for this response."
                    )


# ============================================================
# AI CONVERSATION HISTORY
# ============================================================

st.divider()
st.subheader("AI Conversation History")

# Clear all saved conversations
if st.button("Clear Chat History", key="rag_clear_history"):
    st.session_state.rag_chat_history = []
    st.success("Chat history cleared successfully.")

chat_history = st.session_state.rag_chat_history

if not chat_history:
    st.info("No previous AI conversations in this session.")

else:
    st.caption(f"Total conversations: {len(chat_history)}")

    for index, conversation in enumerate(
        reversed(chat_history), start=1
    ):
        with st.expander(
            f"Conversation {index}: {conversation['question'][:70]}"
        ):
            st.markdown("**Question:**")
            st.write(conversation["question"])

            st.markdown("**Document Version:**")
            st.write(conversation["document_version"])

            st.markdown("**AI Answer:**")
            st.write(conversation["result"]["answer"])

                        # Show verification status for this conversation
            history_verification = conversation["result"].get(
                "verification", {}
            )

            history_verdict = history_verification.get(
                "verdict", "NOT_AVAILABLE"
            )

            st.markdown("**Evidence Verification:**")
            st.write(history_verdict)

                        # Display regulatory sources for this conversation
            history_sources = conversation["result"].get("sources", [])

            st.markdown("**Regulatory Sources:**")

            if history_sources:
                for source in history_sources:
                    with st.expander(
                        f"Source {source['source_number']} "
                        f"— Rule {source['rule_number']}"
                    ):
                        st.write(
                            f"**Document Version:** {source['document_version']}"
                        )
                        st.write(
                            f"**Source File:** {source['source_file']}"
                        )
                        st.write(
                            f"**Rule ID:** {source['rule_id']}"
                        )

                        st.markdown("**Retrieved Evidence:**")
                        st.text(
                            source.get(
                                "text",
                                "Evidence text not available."
                            )
                        )
            else:
                st.info("No regulatory sources available.")

            st.caption(
                "Experimental AI verification. "
                "Human review is required."
            )

                



