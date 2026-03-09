"""
PDF Upload Route - Upload pharmacovigilance PDFs for case creation.
Reuses existing CaseService.create_case() — same path as CSV upload.
After creation, frontend calls existing /analyze endpoint.
"""

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
import logging

from app.db.session import get_db
from app.models.user import User
from app.models.case import AECase
from app.core.security import get_current_active_user
from app.services.case_service import CaseService
from app.services.pdf_intake.pdf_extractor import extract_from_pdf, extract_pdf_text, detect_template
from app.services.pdf_intake.pdf_normalizer import (
    normalize_to_aecase,
    validate_pv_case,
    generate_primaryid,
)
from app.services.cioms_extractor import extract_cioms_fields
from app.services.feature_adapter import build_model_features
from app.services.completeness import detect_missing_fields, compute_cioms_completeness_score

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/pdf-uploads")
async def list_pdf_uploads(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    List all cases created via PDF upload.
    Returns summary info for each, ordered by newest first.
    """
    cases = (
        db.query(AECase)
        .filter(AECase.intake_source == "PDF")
        .order_by(desc(AECase.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    total = db.query(AECase).filter(AECase.intake_source == "PDF").count()
    
    return {
        "total": total,
        "uploads": [
            {
                "case_id": str(c.case_id),
                "primaryid": c.primaryid,
                "filename": c.source_filename or "Unknown",
                "suspect_drug": c.suspect_drug,
                "adverse_event": c.adverse_event,
                "patient_age": c.patient_age,
                "patient_sex": c.patient_sex,
                "data_completeness_score": c.data_completeness_score,
                "case_status": c.case_status,
                "is_serious": c.is_serious,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in cases
        ],
    }


@router.post("/upload-pdf")
async def upload_pdf_case(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Upload a pharmacovigilance PDF to create an AECase.

    Flow:
    1. Parse PDF → extract text
    2. Detect template (CIOMS / STRUCTURED / GENERIC)
    3. Rule-based field extraction
    4. LLM fallback (Ollama mistral) if GENERIC + low confidence
    5. Normalize to AECase schema
    6. Validate ICH minimum criteria
    7. Insert into ae_cases table (same as CSV path)

    After this endpoint returns, frontend should call:
    POST /api/cases/by-primaryid/{primaryid}/analyze
    to trigger the full SmartFU orchestration pipeline.
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed. Please upload a .pdf file.",
        )

    try:
        # Read file bytes
        file_bytes = await file.read()

        if len(file_bytes) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded PDF file is empty.",
            )

        logger.info(f"PDF upload: {file.filename} ({len(file_bytes)} bytes)")

        # Detect template type first
        pdf_text = extract_pdf_text(file_bytes)
        template = detect_template(pdf_text) if pdf_text.strip() else "UNKNOWN"

        cioms_data = None
        cioms_missing = []

        if template == "CIOMS":
            # --- CIOMS pathway: dedicated extractor → feature adapter ---
            logger.info("CIOMS template detected — using dedicated CIOMS extractor")
            try:
                cioms_data = extract_cioms_fields(file_bytes=file_bytes)

                # ── CIOMS VALIDATION GATE ──────────────────────────────────
                # A CIOMS file is valid only if at least ONE of these exists:
                #   reaction_description, suspect_drug_name, report_source
                # If none exist → reject upload, do NOT create a case.
                _has_reaction = bool(cioms_data.get("reaction_description"))
                _has_drug     = bool(cioms_data.get("suspect_drug_name"))
                _has_source   = bool(cioms_data.get("report_source"))

                if not (_has_reaction or _has_drug or _has_source):
                    logger.warning(
                        f"CIOMS extraction returned no identifiable safety data — "
                        f"reaction_description={cioms_data.get('reaction_description')}, "
                        f"suspect_drug_name={cioms_data.get('suspect_drug_name')}, "
                        f"report_source={cioms_data.get('report_source')}"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=(
                            "Invalid CIOMS document — no identifiable safety data extracted. "
                            "At least one of reaction_description, suspect_drug_name, or "
                            "report_source must be present."
                        ),
                    )
                # ──────────────────────────────────────────────────────────

                cioms_missing = detect_missing_fields(cioms_data)
                cioms_score = compute_cioms_completeness_score(cioms_data)

                # Map CIOMS fields → ML-compatible case_data
                ml_input = build_model_features(cioms_data)

                # Build normalized dict for AECase creation (merge ML fields + CIOMS extras)
                normalized = _cioms_to_aecase(cioms_data, ml_input)
                normalized["data_completeness_score"] = cioms_score

                metadata = {
                    "template": "CIOMS",
                    "rule_confidence": cioms_score,
                    "final_confidence": cioms_score,
                    "llm_used": False,
                }
            except Exception as e:
                # Fallback: if CIOMS extraction fails, use existing pipeline
                logger.warning(f"CIOMS extraction failed, falling back to generic pipeline: {e}")
                template = "CIOMS_FALLBACK"
                cioms_data = None

        if cioms_data is None:
            # --- Existing pipeline: generic/structured extraction ---
            extraction_result = extract_from_pdf(file_bytes)
            metadata = extraction_result.get("metadata", {})

            if metadata.get("error"):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"PDF extraction failed: {metadata['error']}",
                )

            normalized = normalize_to_aecase(extraction_result)

            # ── GENERIC PIPELINE VALIDATION GATE ──────────────────────
            # Reject if both drug and event are unknown placeholders
            drug = (normalized.get("suspect_drug_name") or "").strip()
            event = (normalized.get("adverse_event") or "").strip()
            if drug.upper() in ("", "UNKNOWN DRUG") and event.upper() in ("", "UNKNOWN EVENT"):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="PDF does not contain identifiable pharmacovigilance data. "
                           "No suspect drug or adverse event could be extracted.",
                )

        # Validate PV case criteria
        is_complete, missing_criteria = validate_pv_case(normalized)

        # Generate primaryid and create case
        primaryid = generate_primaryid()
        normalized["primaryid"] = primaryid
        normalized["intake_source"] = "PDF"
        normalized["source_filename"] = file.filename

        # Reuse existing CaseService.create_case() — same as CSV upload path
        case_service = CaseService(db)
        case = await case_service.create_case(normalized)

        logger.info(f"PDF case created: case_id={case.case_id}, primaryid={primaryid}")

        response = {
            "success": True,
            "case_id": str(case.case_id),
            "primaryid": primaryid,
            "filename": file.filename,
            "template_detected": metadata.get("template", "UNKNOWN"),
            "extraction_confidence": round(metadata.get("final_confidence", 0.0), 2),
            "rule_confidence": round(metadata.get("rule_confidence", 0.0), 2),
            "llm_used": metadata.get("llm_used", False),
            "is_complete": is_complete,
            "missing_criteria": missing_criteria,
            "data_completeness_score": case.data_completeness_score,
            "message": (
                f"Case created from PDF ({metadata.get('template', 'UNKNOWN')} template). "
                f"Call POST /api/cases/by-primaryid/{primaryid}/analyze to run SmartFU analysis."
            ),
        }

        # Include CIOMS-specific data when available
        if cioms_data is not None:
            response["cioms_missing_fields"] = cioms_missing
            response["cioms_fields_extracted"] = sum(
                1 for v in cioms_data.values() if v is not None
            )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF upload failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF processing failed: {str(e)}",
        )


def _cioms_to_aecase(cioms_data: dict, ml_input: dict) -> dict:
    """
    Map CIOMS extracted data + ML-adapted fields to AECase column dict.

    Combines:
    - ML-compatible fields (suspect_drug, adverse_event, patient_age, etc.)
    - CIOMS-specific fields (patient_initials, indication, therapy dates, etc.)
    """
    from dateutil import parser as date_parser

    normalized = {
        # ML-mapped fields (core AECase columns)
        "suspect_drug": ml_input.get("suspect_drug") or "UNKNOWN DRUG",
        "adverse_event": ml_input.get("adverse_event") or "UNKNOWN EVENT",
        "reporter_type": ml_input.get("reporter_type"),
        "drug_dose": ml_input.get("dose"),
        "drug_route": ml_input.get("route"),
        "event_outcome": ml_input.get("event_outcome"),
        "reporter_country": cioms_data.get("country"),
        "case_status": "INITIAL_RECEIVED",
    }

    # Patient age
    age = ml_input.get("patient_age")
    if age is not None:
        try:
            age_val = int(age)
            if 0 < age_val < 150:
                normalized["patient_age"] = age_val
        except (ValueError, TypeError):
            pass

    # Patient sex
    sex = ml_input.get("sex")
    if sex:
        normalized["patient_sex"] = str(sex).upper()[:10]

    # Event date (from reaction_onset)
    event_date = ml_input.get("event_date")
    if event_date:
        try:
            normalized["event_date"] = date_parser.parse(str(event_date), fuzzy=True)
        except (ValueError, TypeError):
            pass

    # Seriousness
    is_serious = ml_input.get("is_serious")
    if is_serious is not None:
        normalized["is_serious"] = bool(is_serious)

    # CIOMS-specific fields (new columns on AECase)
    normalized["patient_initials"] = cioms_data.get("patient_initials")
    normalized["indication"] = cioms_data.get("indication")
    normalized["dechallenge"] = cioms_data.get("dechallenge")
    normalized["rechallenge"] = cioms_data.get("rechallenge")
    normalized["concomitant_drugs"] = cioms_data.get("concomitant_drugs")
    normalized["medical_history"] = cioms_data.get("medical_history")
    normalized["report_type"] = cioms_data.get("report_type")
    normalized["reporter_email"] = cioms_data.get("reporter_email")
    normalized["reporter_phone"] = cioms_data.get("reporter_phone")
    normalized["manufacturer_name"] = cioms_data.get("manufacturer_name")

    # Therapy dates
    for date_field, cioms_key in [("therapy_start", "therapy_start"), ("therapy_end", "therapy_end")]:
        raw = cioms_data.get(cioms_key)
        if raw:
            try:
                normalized[date_field] = date_parser.parse(str(raw), fuzzy=True)
            except (ValueError, TypeError):
                pass

    # Therapy duration
    duration = cioms_data.get("therapy_duration")
    if duration is not None:
        try:
            normalized["therapy_duration"] = int(duration)
        except (ValueError, TypeError):
            pass

    # ── Truncate string fields to match DB column max lengths ──
    _FIELD_MAX_LENGTHS = {
        "suspect_drug": 500,
        "adverse_event": 1000,
        "reporter_type": 10,
        "reporter_country": 5,
        "drug_dose": 500,
        "drug_route": 100,
        "event_outcome": 100,
        "patient_sex": 10,
        "patient_age_group": 20,
        "case_priority": 20,
        "case_status": 50,
        "risk_level": 20,
        "priority_score": 20,
        "intake_source": 20,
        "source_filename": 500,
        "patient_initials": 20,
        "indication": 500,
        "dechallenge": 50,
        "rechallenge": 50,
        "report_type": 50,
        "reporter_email": 200,
        "reporter_phone": 50,
        "manufacturer_name": 500,
        "reviewed_by": 100,
    }
    for field, max_len in _FIELD_MAX_LENGTHS.items():
        val = normalized.get(field)
        if isinstance(val, str) and len(val) > max_len:
            normalized[field] = val[:max_len]

    return normalized
