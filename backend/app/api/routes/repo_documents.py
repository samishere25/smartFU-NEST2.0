"""
Global Document Repository — CRUD routes.

Upload form templates (TAFU, Pregnancy, Custom) once, AI auto-extracts
questions on upload, forms are reusable across any case.
"""

import os
import uuid
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_active_user
from app.models.repo_document import RepoDocument
from app.schemas.repo_document import (
    RepoDocumentOut,
    RepoDocumentListItem,
    RepoDocumentListResponse,
    RepoDocumentQuestionsOut,
)

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_active_user)])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads", "repo_documents")


def _ensure_upload_dir():
    os.makedirs(UPLOAD_DIR, exist_ok=True)


def _doc_to_list_item(doc: RepoDocument) -> dict:
    questions = doc.extracted_questions or []
    return {
        "id": doc.id,
        "display_name": doc.display_name,
        "form_type": doc.form_type,
        "file_name": doc.file_name,
        "uploaded_by": doc.uploaded_by,
        "uploaded_at": doc.uploaded_at,
        "extraction_status": doc.extraction_status,
        "is_active": doc.is_active,
        "description": doc.description,
        "questions_count": len(questions) if isinstance(questions, list) else 0,
    }


def _doc_to_full(doc: RepoDocument) -> dict:
    questions = doc.extracted_questions or []
    data = _doc_to_list_item(doc)
    data["extracted_questions"] = questions
    data["extraction_error"] = doc.extraction_error
    return data


# ── POST /upload ──
@router.post("/upload", response_model=RepoDocumentOut)
async def upload_repo_document(
    file: UploadFile = File(...),
    display_name: str = Form(...),
    form_type: str = Form("CUSTOM"),
    description: str = Form(""),
    uploaded_by: str = Form("system"),
    db: Session = Depends(get_db),
):
    """Upload a form PDF to the global repository. AI extracts questions on upload."""
    _ensure_upload_dir()

    # Save file to disk
    doc_id = uuid.uuid4()
    safe_name = file.filename or "document.pdf"
    file_name_on_disk = f"{doc_id}_{safe_name}"
    file_path = os.path.join(UPLOAD_DIR, file_name_on_disk)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    logger.info(f"Saved repo document: {file_path} ({len(content)} bytes)")

    # Create DB record
    doc = RepoDocument(
        id=doc_id,
        display_name=display_name,
        form_type=form_type.upper(),
        file_name=safe_name,
        file_path=file_path,
        uploaded_by=uploaded_by,
        description=description or None,
        extraction_status="PENDING",
    )
    db.add(doc)
    db.flush()

    # Extract questions synchronously
    try:
        from app.services.checklist_extractor import extract_checklist_items

        items = extract_checklist_items(
            file_bytes=content,
            document_type=form_type.upper(),
        )
        doc.extracted_questions = items
        doc.extraction_status = "DONE"
        logger.info(f"Extracted {len(items)} questions from repo document {doc_id}")
    except Exception as e:
        doc.extraction_status = "FAILED"
        doc.extraction_error = str(e)
        logger.error(f"Extraction failed for repo document {doc_id}: {e}")

    db.commit()
    db.refresh(doc)

    return _doc_to_full(doc)


# ── GET / ──
@router.get("/", response_model=RepoDocumentListResponse)
async def list_repo_documents(
    form_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List all active repo documents (lightweight, no extracted_questions)."""
    query = db.query(RepoDocument).filter(RepoDocument.is_active == True)

    if form_type:
        query = query.filter(RepoDocument.form_type == form_type.upper())

    docs = query.order_by(RepoDocument.uploaded_at.desc()).all()

    return {
        "total": len(docs),
        "documents": [_doc_to_list_item(d) for d in docs],
    }


# ── GET /{doc_id}/questions ──
@router.get("/{doc_id}/questions", response_model=RepoDocumentQuestionsOut)
async def get_repo_document_questions(
    doc_id: str,
    db: Session = Depends(get_db),
):
    """Get extracted questions for a specific repo document."""
    doc = db.query(RepoDocument).filter(
        RepoDocument.id == doc_id,
        RepoDocument.is_active == True,
    ).first()

    if not doc:
        raise HTTPException(status_code=404, detail="Repo document not found")

    return {
        "id": doc.id,
        "display_name": doc.display_name,
        "form_type": doc.form_type,
        "extracted_questions": doc.extracted_questions or [],
        "extraction_status": doc.extraction_status,
    }


# ── POST /{doc_id}/re-extract ──
@router.post("/{doc_id}/re-extract", response_model=RepoDocumentOut)
async def re_extract_questions(
    doc_id: str,
    db: Session = Depends(get_db),
):
    """Re-run question extraction for a repo document."""
    doc = db.query(RepoDocument).filter(
        RepoDocument.id == doc_id,
        RepoDocument.is_active == True,
    ).first()

    if not doc:
        raise HTTPException(status_code=404, detail="Repo document not found")

    try:
        from app.services.checklist_extractor import extract_checklist_items

        items = extract_checklist_items(
            file_path=doc.file_path,
            document_type=doc.form_type,
        )
        doc.extracted_questions = items
        doc.extraction_status = "DONE"
        doc.extraction_error = None
        logger.info(f"Re-extracted {len(items)} questions from repo document {doc_id}")
    except Exception as e:
        doc.extraction_status = "FAILED"
        doc.extraction_error = str(e)
        logger.error(f"Re-extraction failed for repo document {doc_id}: {e}")

    db.commit()
    db.refresh(doc)

    return _doc_to_full(doc)


# ── DELETE /{doc_id} ──
@router.delete("/{doc_id}")
async def delete_repo_document(
    doc_id: str,
    db: Session = Depends(get_db),
):
    """Soft-delete a repo document."""
    doc = db.query(RepoDocument).filter(
        RepoDocument.id == doc_id,
        RepoDocument.is_active == True,
    ).first()

    if not doc:
        raise HTTPException(status_code=404, detail="Repo document not found")

    doc.is_active = False
    db.commit()

    return {"message": f"Document '{doc.display_name}' deleted", "id": str(doc.id)}
