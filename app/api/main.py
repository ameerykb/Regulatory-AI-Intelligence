
import json
from datetime import datetime, timezone
import logging
import re
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel, Field, model_validator

from app.rag_engine.rag_pipeline import answer_regulatory_question
from app.document_engine.pdf_extractor import extract_pdf, save_extraction
from app.document_engine.section_parser import parse_sections, save_sections
from app.change_engine.document_aligner import (
    align_documents,
    save_alignment_report,
)
from app.change_engine.change_analyzer import (
    analyze_document_changes,
    save_change_analysis,
)


logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[2]

UPLOAD_DIR = BASE_DIR / "data" / "uploads"
EXTRACTED_DIR = BASE_DIR / "data" / "extracted"
PARSED_DIR = BASE_DIR / "data" / "parsed"
COMPARISON_DIR = BASE_DIR / "data" / "comparisons"

MAX_UPLOAD_SIZE = 20 * 1024 * 1024
DOCUMENT_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")

app = FastAPI(
    title="Regulatory AI Intelligence API",
    description="REST API for regulatory document intelligence and AI analysis",
    version="1.2.0",
)


# --------------------------------------------------
# Health endpoints
# --------------------------------------------------

@app.get("/")
def root():
    return {
        "message": "Regulatory AI Intelligence API",
        "status": "running",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "regulatory-ai-intelligence",
    }


# --------------------------------------------------
# RAG endpoint
# --------------------------------------------------

class RegulatoryQuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    document_version: Literal[
        "draft_2025", "final_2025"
    ] = "final_2025"
    top_k: int = Field(default=3, ge=1, le=10)


@app.post("/rag/query")
def query_regulatory_rag(request: RegulatoryQuestionRequest):
    try:
        return answer_regulatory_question(
            question=request.question,
            document_version=request.document_version,
            top_k=request.top_k,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        logger.exception("Regulatory RAG query failed")
        raise HTTPException(
            status_code=500,
            detail="Regulatory query failed. Check server logs.",
        ) from exc


# --------------------------------------------------
# PDF upload endpoint
# --------------------------------------------------

@app.post("/documents/upload")
def upload_regulatory_document(file: UploadFile = File(...)):
    original_filename = Path(
        (file.filename or "").replace("\\", "/")
    ).name

    if not original_filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported.",
        )

    document_id = uuid4().hex

    pdf_path = UPLOAD_DIR / f"{document_id}.pdf"
    json_path = EXTRACTED_DIR / f"{document_id}.json"

    try:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)

        total_size = 0

        with pdf_path.open("wb") as destination:
            while chunk := file.file.read(1024 * 1024):
                total_size += len(chunk)

                if total_size > MAX_UPLOAD_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail="PDF exceeds the 20 MB upload limit.",
                    )

                destination.write(chunk)

        extraction = extract_pdf(pdf_path)

        if extraction["pages_with_text"] == 0:
            raise HTTPException(
                status_code=422,
                detail="No extractable text found in the PDF.",
            )

        save_extraction(extraction, json_path)

        return {
            "status": "uploaded",
            "document_id": document_id,
            "filename": original_filename,
            "total_pages": extraction["total_pages"],
            "pages_with_text": extraction["pages_with_text"],
            "sha256": extraction["sha256"],
            "extraction_status": "completed",
        }

    except HTTPException:
        pdf_path.unlink(missing_ok=True)
        json_path.unlink(missing_ok=True)
        raise

    except (ValueError, FileNotFoundError) as exc:
        pdf_path.unlink(missing_ok=True)
        json_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        pdf_path.unlink(missing_ok=True)
        json_path.unlink(missing_ok=True)
        logger.exception("PDF upload failed")
        raise HTTPException(
            status_code=500,
            detail="PDF processing failed. Check server logs.",
        ) from exc

    finally:
        file.file.close()


# --------------------------------------------------
# Document comparison request
# --------------------------------------------------

class DocumentPageRange(BaseModel):
    start_page: int = Field(default=1, ge=1)
    end_page: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_range(self):
        if self.end_page < self.start_page:
            raise ValueError(
                "end_page must be greater than or equal to start_page."
            )
        return self


class DocumentComparisonRequest(BaseModel):
    original_document_id: str = Field(
        pattern=r"^[0-9a-f]{32}$"
    )
    updated_document_id: str = Field(
        pattern=r"^[0-9a-f]{32}$"
    )

    original_pages: DocumentPageRange
    updated_pages: DocumentPageRange

    top_k: int = Field(default=3, ge=1, le=10)


# --------------------------------------------------
# Load and parse an uploaded document
# --------------------------------------------------

def load_uploaded_rules(
    document_id: str,
    page_range: DocumentPageRange,
) -> dict:

    if not DOCUMENT_ID_PATTERN.fullmatch(document_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid document ID.",
        )

    extraction_path = EXTRACTED_DIR / f"{document_id}.json"

    if not extraction_path.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"Document not found: {document_id}",
        )

    with extraction_path.open("r", encoding="utf-8") as source:
        extraction = json.load(source)

    pages = extraction.get("pages", [])

    if not pages:
        raise HTTPException(
            status_code=422,
            detail=f"Document has no extracted pages: {document_id}",
        )

    total_pages = len(pages)

    if page_range.end_page > total_pages:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Page range exceeds document length. "
                f"Document {document_id} has {total_pages} pages."
            ),
        )

    parsed = parse_sections(
        extraction,
        start_page=page_range.start_page,
        end_page=page_range.end_page,
    )

    if not parsed["sections"]:
        raise HTTPException(
            status_code=422,
            detail=(
                f"No numbered regulatory rules detected "
                f"in document {document_id}. "
                f"Check the selected pages and heading format."
            ),
        )

    return parsed


# --------------------------------------------------
# Compare two uploaded regulatory documents
# --------------------------------------------------

@app.post("/documents/compare")
def compare_regulatory_documents(
    request: DocumentComparisonRequest,
):
    if request.original_document_id == request.updated_document_id:
        raise HTTPException(
            status_code=400,
            detail="Upload two different document versions for comparison.",
        )

    try:
        original = load_uploaded_rules(
            request.original_document_id,
            request.original_pages,
        )

        updated = load_uploaded_rules(
            request.updated_document_id,
            request.updated_pages,
        )

        original_rules = original["sections"]
        updated_rules = updated["sections"]

        # Match corresponding rules.
        alignment_report = align_documents(
            original_rules,
            updated_rules,
            top_k=request.top_k,
        )

        # Detect word-level changes in high-confidence matches.
        change_report = analyze_document_changes(
            original_rules,
            updated_rules,
            alignment_report,
        )

        comparison_id = uuid4().hex

        # Save structured outputs.
        original_parsed_path = (
            PARSED_DIR / f"{comparison_id}_original.json"
        )
        updated_parsed_path = (
            PARSED_DIR / f"{comparison_id}_updated.json"
        )
        alignment_path = (
            COMPARISON_DIR / f"{comparison_id}_alignment.json"
        )
        changes_path = (
            COMPARISON_DIR / f"{comparison_id}_changes.json"
        )

        save_sections(original, original_parsed_path)
        save_sections(updated, updated_parsed_path)

        save_alignment_report(
            alignment_report,
            alignment_path,
        )

        save_change_analysis(
            change_report,
            changes_path,
        )

        return {
            "status": "completed",
            "comparison_id": comparison_id,
            "original_document_id": request.original_document_id,
            "updated_document_id": request.updated_document_id,
            "summary": {
                "original_rule_count": len(original_rules),
                "updated_rule_count": len(updated_rules),
                "analyzed_rule_count": change_report[
                    "analyzed_rule_count"
                ],
                "modified_rule_count": change_report[
                    "modified_rule_count"
                ],
                "pending_review_count": change_report[
                    "pending_review_count"
                ],
                "potential_addition_count": alignment_report[
                    "potential_addition_count"
                ],
                "potential_removal_count": alignment_report[
                    "potential_removal_count"
                ],
                "alignment_conflict_count": len(
                    change_report["alignment_conflicts"]
                ),
            },
            "analyzed_rules": change_report["analyzed_rules"],
            "pending_review": change_report["pending_review"],
            "potential_additions": alignment_report[
                "unmatched_final_rules"
            ],
            "potential_removals": alignment_report[
                "unmatched_draft_rules"
            ],
            "alignment_conflicts": change_report[
                "alignment_conflicts"
            ],
            "parsing_warnings": {
                "original": original["warnings"],
                "updated": updated["warnings"],
            },
            "review_required": True,
        }

    except HTTPException:
        raise

    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        logger.exception("Document comparison failed")
        raise HTTPException(
            status_code=500,
            detail="Document comparison failed. Check server logs.",
        ) from exc



# --------------------------------------------------
# Retrieve saved comparison results
# --------------------------------------------------

# --------------------------------------------------
# Comparison history and structured export
# --------------------------------------------------

@app.get("/documents/comparisons")
def list_saved_comparisons():
    entries = []
    if not COMPARISON_DIR.exists():
        return {"comparisons": entries}
    for path in COMPARISON_DIR.glob("*_changes.json"):
        comparison_id = path.name.removesuffix("_changes.json")
        if not DOCUMENT_ID_PATTERN.fullmatch(comparison_id):
            continue
        if not all((PARSED_DIR / f"{comparison_id}_{suffix}.json").is_file()
                   for suffix in ("original", "updated")):
            continue
        try:
            changes = json.loads(path.read_text(encoding="utf-8"))
            rules = changes.get("analyzed_rules", [])
            if not isinstance(rules, list):
                continue
            entries.append({
                "comparison_id": comparison_id,
                "created_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
                "analyzed_rule_count": len(rules),
                "modified_rule_count": sum(r.get("status") == "modified" for r in rules if isinstance(r, dict)),
                "pending_review_count": sum(bool(r.get("review_required")) for r in rules if isinstance(r, dict)),
            })
        except (OSError, ValueError, TypeError, KeyError):
            logger.warning("Skipping unreadable comparison history entry: %s", path.name)
    entries.sort(key=lambda x: x["created_at"], reverse=True)
    return {"comparisons": entries}


@app.get("/documents/comparisons/{comparison_id}/export")
def export_saved_comparison(comparison_id: str):
    from fastapi.responses import JSONResponse
    payload = get_saved_comparison(comparison_id)
    return JSONResponse(
        content=payload,
        headers={"Content-Disposition": f'attachment; filename="{comparison_id}_comparison.json"'},
    )


@app.get("/documents/comparisons/{comparison_id}")
def get_saved_comparison(comparison_id: str):
    if not DOCUMENT_ID_PATTERN.fullmatch(comparison_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid comparison ID.",
        )

    paths = {
        "changes": COMPARISON_DIR / f"{comparison_id}_changes.json",
        "draft": PARSED_DIR / f"{comparison_id}_original.json",
        "final": PARSED_DIR / f"{comparison_id}_updated.json",
    }

    if any(not path.is_file() for path in paths.values()):
        raise HTTPException(
            status_code=404,
            detail="Saved comparison files not found.",
        )

    try:
        data = {
            name: json.loads(path.read_text(encoding="utf-8"))
            for name, path in paths.items()
        }
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        logger.exception("Failed to load saved comparison %s", comparison_id)
        raise HTTPException(
            status_code=500,
            detail="Unable to read saved comparison files.",
        ) from exc

    return {
        "comparison_id": comparison_id,
        **data,
    }




# Phase 5: Policy impact API
from app.api.impact_routes import router as impact_router

# Register each endpoint explicitly for compatibility with
# this application's router behavior.
for impact_route in impact_router.routes:
    app.add_api_route(
        impact_route.path,
        impact_route.endpoint,
        methods=list(impact_route.methods),
        name=impact_route.name,
        response_model=impact_route.response_model,
        tags=impact_route.tags,
    )
