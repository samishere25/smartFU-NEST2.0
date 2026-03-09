"""
Case Documents Route — Upload and manage multiple documents per case.

Strictly separated:
- CIOMS documents → run existing extraction pipeline, update AECase, store extracted_json.
- All other types (TAFU, PREGNANCY, REVIEWER_NOTE, RESPONSE) → file + metadata only.

AECase table is NEVER modified by this module except via the existing CIOMS pipeline.
"""

import os
import uuid
import logging
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.models.case import AECase
from app.models.case_document import CaseDocument, DocumentType
from app.core.security import get_current_active_user
from app.schemas.case_document import CaseDocumentOut, CaseDocumentListOut, CombinedFollowUpOut

router = APIRouter()
logger = logging.getLogger(__name__)

# File storage root — relative to backend directory
UPLOAD_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "uploads", "case_documents")


def _ensure_upload_dir(case_id: str) -> str:
    """Create and return the upload directory for a given case."""
    case_dir = os.path.join(UPLOAD_ROOT, case_id)
    os.makedirs(case_dir, exist_ok=True)
    return case_dir


# ──────────────────────────────────────────────────────────────
# POST /cases/{case_id}/documents — Upload a document
# ──────────────────────────────────────────────────────────────
@router.post("/{case_id}/documents", response_model=CaseDocumentOut)
async def upload_case_document(
    case_id: str,
    document_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Upload a document for an existing case.

    - CIOMS → runs existing CIOMS extraction pipeline, updates AECase, stores extracted_json.
    - TAFU / PREGNANCY / REVIEWER_NOTE / RESPONSE → stores file + metadata only.
    """
    # Validate document_type
    try:
        doc_type = DocumentType(document_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid document_type '{document_type}'. Allowed: {[e.value for e in DocumentType]}",
        )

    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No file provided.")

    # Validate case exists
    case = db.query(AECase).filter(AECase.case_id == case_id).first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case {case_id} not found.")

    # Read file bytes
    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")

    # Save file to disk
    case_dir = _ensure_upload_dir(str(case.case_id))
    safe_name = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(case_dir, safe_name)
    with open(file_path, "wb") as f:
        f.write(file_bytes)

    logger.info(f"Document saved: {file_path} ({len(file_bytes)} bytes) type={doc_type.value}")

    extracted_json = None

    # ── CIOMS document: run existing extraction pipeline ──
    if doc_type == DocumentType.CIOMS:
        extracted_json = _run_cioms_extraction(file_bytes, case, db)

    # ── All other types: file + metadata only (no extraction, no AI, no AECase modification) ──

    # Create CaseDocument record
    doc = CaseDocument(
        case_id=case.case_id,
        document_type=doc_type,
        file_name=file.filename,
        file_path=file_path,
        uploaded_by=current_user.username if current_user else None,
        uploaded_at=datetime.utcnow(),
        extracted_json=extracted_json,
        is_active=True,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    logger.info(f"CaseDocument created: id={doc.id} case_id={case_id} type={doc_type.value}")

    return doc


def _run_cioms_extraction(file_bytes: bytes, case: AECase, db: Session) -> dict:
    """
    Run the existing CIOMS extraction pipeline on file_bytes.
    Updates AECase fields exactly as the current system does.
    Returns the extracted JSON dict.

    This function calls into existing code — zero rewrite.
    """
    from app.services.cioms_extractor import extract_cioms_fields
    from app.services.completeness import detect_missing_fields, compute_cioms_completeness_score
    from app.services.feature_adapter import build_model_features
    from app.api.routes.pdf_upload import _cioms_to_aecase

    try:
        cioms_data = extract_cioms_fields(file_bytes=file_bytes)
        cioms_missing = detect_missing_fields(cioms_data)
        cioms_score = compute_cioms_completeness_score(cioms_data)
        ml_input = build_model_features(cioms_data)
        normalized = _cioms_to_aecase(cioms_data, ml_input)

        # Update existing AECase fields (only non-None values)
        for key, value in normalized.items():
            if value is not None and hasattr(case, key):
                setattr(case, key, value)

        case.data_completeness_score = cioms_score
        case.updated_at = datetime.utcnow()
        db.flush()

        logger.info(f"CIOMS extraction updated case {case.case_id}: score={cioms_score:.2f}")

        return {
            "cioms_fields": cioms_data,
            "missing_fields": cioms_missing,
            "completeness_score": cioms_score,
            "fields_extracted": sum(1 for v in cioms_data.values() if v is not None),
        }

    except Exception as e:
        logger.error(f"CIOMS extraction failed for case {case.case_id}: {e}", exc_info=True)
        return {"error": str(e)}


# ──────────────────────────────────────────────────────────────
# GET /cases/{case_id}/documents — List documents for a case
# ──────────────────────────────────────────────────────────────
@router.get("/{case_id}/documents", response_model=CaseDocumentListOut)
async def list_case_documents(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List all documents attached to a case, grouped by type."""
    case = db.query(AECase).filter(AECase.case_id == case_id).first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case {case_id} not found.")

    docs = (
        db.query(CaseDocument)
        .filter(CaseDocument.case_id == case.case_id, CaseDocument.is_active == True)
        .order_by(CaseDocument.uploaded_at.desc())
        .all()
    )

    return CaseDocumentListOut(total=len(docs), documents=docs)


# ──────────────────────────────────────────────────────────────
# DELETE /cases/{case_id}/documents/{doc_id} — Soft-delete
# ──────────────────────────────────────────────────────────────
@router.delete("/{case_id}/documents/{doc_id}")
async def deactivate_case_document(
    case_id: str,
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Soft-delete a document (set is_active=False)."""
    doc = (
        db.query(CaseDocument)
        .filter(CaseDocument.id == doc_id, CaseDocument.case_id == case_id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    doc.is_active = False
    db.commit()

    return {"success": True, "message": f"Document {doc_id} deactivated."}


# ──────────────────────────────────────────────────────────────
# POST /cases/{case_id}/build-combined-followup
# ──────────────────────────────────────────────────────────────
@router.post("/{case_id}/build-combined-followup", response_model=CombinedFollowUpOut)
async def build_combined_followup_endpoint(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Consolidated follow-up builder.

    Combines:
    1. AI-generated missing-field questions (from existing logic).
    2. Reviewer questions (from REVIEWER_NOTE documents).
    3. Checklist documents (TAFU, PREGNANCY).

    Returns aggregated payload — no email send, no hardcoding.
    """
    from app.services.combined_followup import build_combined_followup

    case = db.query(AECase).filter(AECase.case_id == case_id).first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case {case_id} not found.")

    result = build_combined_followup(case, db)
    return result
