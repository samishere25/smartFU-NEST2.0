"""
Follow-Up Agent API
Conversational, one-question-at-a-time follow-up experience
Completely isolated from admin UI
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Optional, List
import logging
from datetime import datetime

from app.db.session import get_db
from app.models.case import AECase
from app.models.followup import FollowUpAttempt
from app.services.response_processor import ResponseProcessor
from app.utils.safety_confidence import SafetyConfidenceCalculator
from app.services.translation_service import (
    get_supported_languages,
    translate_question,
    translate_options,
    get_ui_strings,
    SUPPORTED_LANGUAGES,
)

router = APIRouter()
logger = logging.getLogger(__name__)

# Question type mapping — determines UI rendering for each field
AGENT_FIELD_TYPES = {
    "patient_sex": {
        "type": "select",
        "options": [
            {"value": "Male", "label": "Male"},
            {"value": "Female", "label": "Female"},
            {"value": "Unknown", "label": "Unknown"}
        ]
    },
    "event_date": {"type": "date", "options": []},
    "receipt_date": {"type": "date", "options": []},
    "patient_age": {"type": "number", "options": []},
    "event_outcome": {
        "type": "select",
        "options": [
            {"value": "Recovered/Resolved", "label": "Recovered/Resolved"},
            {"value": "Recovering/Resolving", "label": "Recovering/Resolving"},
            {"value": "Not Recovered/Not Resolved", "label": "Not Recovered/Not Resolved"},
            {"value": "Recovered with Sequelae", "label": "Recovered with Sequelae"},
            {"value": "Fatal", "label": "Fatal"},
            {"value": "Unknown", "label": "Unknown"}
        ]
    },
    "drug_route": {
        "type": "select",
        "options": [
            {"value": "Oral", "label": "Oral"},
            {"value": "Intravenous", "label": "Intravenous"},
            {"value": "Intramuscular", "label": "Intramuscular"},
            {"value": "Subcutaneous", "label": "Subcutaneous"},
            {"value": "Topical", "label": "Topical"},
            {"value": "Inhalation", "label": "Inhalation"},
            {"value": "Other", "label": "Other"}
        ]
    },
    "reporter_type": {
        "type": "select",
        "options": [
            {"value": "MD", "label": "Physician (MD)"},
            {"value": "PH", "label": "Pharmacist (PH)"},
            {"value": "HP", "label": "Nurse (HP)"},
            {"value": "CN", "label": "Consumer (CN)"},
            {"value": "PT", "label": "Patient (PT)"},
            {"value": "LW", "label": "Lawyer (LW)"},
            {"value": "OT", "label": "Other (OT)"}
        ]
    },
}


def _enrich_question(field_name: str, question_obj: dict) -> dict:
    """Add proper type and options to a question based on its field_name."""
    type_info = AGENT_FIELD_TYPES.get(field_name, {"type": "text", "options": []})
    question_obj["type"] = type_info["type"]
    question_obj["options"] = type_info.get("options", [])
    return question_obj


def _update_lifecycle_on_response(db, case, questions_answered: int, completeness: float, is_complete: bool):
    """Auto-update lifecycle tracker when a follow-up response is received."""
    try:
        from app.services.lifecycle_db_service import LifecycleDBService
        lifecycle_service = LifecycleDBService(db)
        lifecycle = lifecycle_service.get_lifecycle_by_case_id(str(case.case_id))

        if not lifecycle:
            logger.info(f"No lifecycle found for case {case.case_id}, skipping lifecycle update")
            return

        lifecycle = lifecycle_service.record_response_received(
            lifecycle=lifecycle,
            questions_answered=questions_answered,
            completeness_score=completeness,
            safety_confidence=completeness,
            is_complete=is_complete
        )

        # Auto-close if complete
        if lifecycle.response_status == "complete":
            lifecycle = lifecycle_service.close_case_success(lifecycle)

        logger.info(f"✅ Lifecycle auto-updated on response: case {case.case_id}, completeness={completeness:.0%}")
    except Exception as e:
        logger.warning(f"⚠️ Lifecycle update failed (non-critical): {e}")


@router.get("/followup-agent/{token}/start")
async def start_followup_session(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Start follow-up agent session
    
    Returns:
    - Language selection prompt
    - Session metadata
    - Case context (drug, event)
    """
    try:
        # Validate token (bypass DB error like we did before)
        followup = None
        case = None
        
        try:
            followup = db.query(FollowUpAttempt).filter(
                FollowUpAttempt.secure_token == token,
                FollowUpAttempt.status.in_(["SENT", "AWAITING_RESPONSE", "PENDING"])
            ).first()
            
            if followup:
                case = db.query(AECase).filter(
                    AECase.case_id == followup.case_id
                ).first()
        except Exception as db_error:
            logger.warning(f"⚠️ Database query failed: {str(db_error)}")
            # Fallback: Try to find ANY case for demo purposes
            # In production, this would validate token against external system
            try:
                # Try to get a random case for demo
                case = db.query(AECase).filter(
                    AECase.suspect_drug.isnot(None)
                ).first()
                logger.info(f"✅ Using fallback case for token {token}")
            except Exception:
                pass
        
        if not case:
            raise HTTPException(
                status_code=404,
                detail="Invalid or expired link. Please contact support."
            )
        
        # Check if already completed
        if followup and followup.response_received:
            return {
                "status": "completed",
                "message": "Thank you! This follow-up has already been completed."
            }
        
        # Return session start data with all supported languages
        return {
            "status": "ready",
            "token": token,
            "case_context": {
                "drug": case.suspect_drug or "medication",
                "event": case.adverse_event or "adverse event",
                "case_id": str(case.case_id)
            },
            "language_options": get_supported_languages(),
            "message": "Thank you for helping us ensure patient safety. We have a few questions about the reported case."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting followup session: {str(e)}")
        raise HTTPException(status_code=500, detail="Error starting session")


@router.post("/followup-agent/{token}/set-language")
async def set_language(
    token: str,
    request: dict,
    db: Session = Depends(get_db)
):
    """
    Set language preference and get first question
    
    Args:
        token: Secure token
        request: {"language": "en" or "hi"}
    
    Returns:
        First question in selected language
    """
    language = request.get("language", "en")
    try:
        # Get followup attempt (with bypass logic)
        followup = None
        case = None
        
        try:
            followup = db.query(FollowUpAttempt).filter(
                FollowUpAttempt.secure_token == token
            ).first()
            
            if followup:
                case = db.query(AECase).filter(
                    AECase.case_id == followup.case_id
                ).first()
                
                # Store language preference
                if not followup.response_data:
                    followup.response_data = {}
                followup.response_data['language'] = language
                db.commit()
        except Exception as db_error:
            logger.warning(f"⚠️ Database query failed: {str(db_error)}")
            # Fallback: Try to get a random case for demo purposes
            try:
                case = db.query(AECase).filter(
                    AECase.suspect_drug.isnot(None)
                ).first()
                logger.info(f"✅ Using fallback case for token {token}")
            except Exception:
                pass
        
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        
        # A. FIX QUESTION PERSISTENCE - ALWAYS use stored questions, NEVER fallback
        questions = []
        
        if not followup:
            raise HTTPException(status_code=404, detail="Follow-up attempt not found")
        
        # Read questions from response_data["questions"] ONLY
        if followup.response_data and isinstance(followup.response_data, dict):
            questions = followup.response_data.get("questions", [])
        
        if not questions or len(questions) == 0:
            # CRITICAL: No fallback allowed - this means questions were not stored properly
            logger.error(f"❌ CRITICAL: No questions found in response_data for attempt {followup.attempt_id}")
            logger.error(f"   This indicates question persistence failed during follow-up creation")
            raise HTTPException(
                status_code=500, 
                detail="Follow-up questions not found. Please contact support."
            )
        
        # STEP 7 debug log
        logger.info(f"🔥 FOLLOWUP QUESTIONS USED: {[q.get('field') for q in questions]}")
        logger.info(f"✅ Using {len(questions)} questions from response_data['questions']")
        
        # Return first question — translated to selected language
        first_question = questions[0]
        
        # FIX: AI stores "question" and "field", not "question_text" and "field_name"
        question_text = first_question.get("question") or first_question.get("question_text")
        field_name = first_question.get("field") or first_question.get("field_name")
        
        # 🌐 Translate question text and options
        translated_text = translate_question(question_text, language)
        
        q_obj = {
            "index": 0,
            "total": len(questions),
            "field_name": field_name,
            "text": translated_text,
            "original_text": question_text,
            "type": first_question.get("type", "text"),
            "options": first_question.get("options", [])
        }
        q_obj = _enrich_question(field_name, q_obj)
        # Translate options after enrichment
        if language != "en" and q_obj.get("options"):
            q_obj["options"] = translate_options(q_obj["options"], language)

        # Get translated UI strings
        ui_strings = get_ui_strings(language)

        response = {
            "status": "active",
            "question": q_obj,
            "progress": {
                "current": 1,
                "total": len(questions),
                "percentage": round(1 / len(questions) * 100)
            },
            "ui_strings": ui_strings
        }
        
        logger.info(f"✅ Returning question in '{language}': {translated_text[:60]}")
        logger.info(f"📊 Question details: field={field_name}, type={q_obj['type']}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting language: {str(e)}")
        raise HTTPException(status_code=500, detail="Error processing request")


@router.post("/followup-agent/{token}/answer")
async def submit_answer(
    token: str,
    answer_data: Dict,
    db: Session = Depends(get_db)
):
    """
    Submit one answer and get next question (adaptive loop)
    
    Args:
        token: Secure token
        answer_data: {
            "question_index": 0,
            "field_name": "event_date",
            "answer": "2025-01-15",
            "language": "en"
        }
    
    Returns:
        - Next question OR
        - Completion message if:
          * All questions answered OR
          * Confidence threshold reached (adaptive loop stops)
    """
    try:
        # Extract answer details
        question_index = answer_data.get("question_index", 0)
        field_name = answer_data.get("field_name")
        answer = answer_data.get("answer")
        language = answer_data.get("language", "en")
        
        if not field_name or not answer:
            raise HTTPException(
                status_code=400,
                detail="Missing field_name or answer"
            )
        
        # Get case (with bypass logic)
        followup = None
        case = None
        
        try:
            followup = db.query(FollowUpAttempt).filter(
                FollowUpAttempt.secure_token == token
            ).first()
            
            if followup:
                case = db.query(AECase).filter(
                    AECase.case_id == followup.case_id
                ).first()
        except Exception as db_error:
            logger.warning(f"⚠️ Database query failed: {str(db_error)}")
            # Fallback: Try to get a random case for demo purposes
            try:
                case = db.query(AECase).filter(
                    AECase.suspect_drug.isnot(None)
                ).first()
                logger.info(f"✅ Using fallback case for token {token}")
            except Exception:
                pass
        
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        
        # Process answer using existing ResponseProcessor
        # Read questions BEFORE ResponseProcessor modifies response_data
        questions = []
        if followup and followup.response_data and isinstance(followup.response_data, dict):
            questions = followup.response_data.get("questions", [])

        if not questions:
            logger.error(f"❌ CRITICAL: No questions in response_data for attempt {followup.attempt_id if followup else 'None'}")
            raise HTTPException(
                status_code=500,
                detail="Follow-up questions not found"
            )

        result = await ResponseProcessor.process_response(
            db=db,
            case_id=str(case.case_id),
            attempt_id=str(followup.attempt_id) if followup else None,
            response_data={
                "answer": answer,
                "field_name": field_name,
                "channel": "WEB"
            },
            channel="WEB"
        )

        logger.info(
            f"✅ Answer processed: {field_name} = {answer}, "
            f"completeness: {result.get('completeness_after', 0):.0%}"
        )

        # Refresh followup from DB to get updated response_data
        if followup:
            db.refresh(followup)

        # Auto-update lifecycle tracker after EACH answer (live tracking)
        current_completeness_for_lifecycle = result.get('completeness_after', 0)
        _update_lifecycle_on_response(
            db, case, 1, current_completeness_for_lifecycle,
            is_complete=(current_completeness_for_lifecycle >= 1.0)
        )
        
        # D. Check if we should continue - COMPLETE only at 100% AND all questions answered
        current_completeness = result.get('completeness_after', 0)
        
        # ── FIX: Check if remaining questions include REVIEWER/REPO questions ──
        # Never skip reviewer or repo questions even if completeness is 100%
        has_remaining_questions = (question_index + 1) < len(questions)
        has_remaining_reviewer_qs = False
        if has_remaining_questions:
            for remaining_q in questions[question_index + 1:]:
                src = (remaining_q.get("source") or "").upper()
                if "REVIEWER" in src or "REPO" in src or "CHECKLIST" in src:
                    has_remaining_reviewer_qs = True
                    break
        
        # Continue if: (a) completeness < 100%, OR (b) there are reviewer/repo questions left
        should_continue = has_remaining_questions and (current_completeness < 1.0 or has_remaining_reviewer_qs)
        
        logger.info(f"📊 Completeness check: {current_completeness:.0%}, Question {question_index+1}/{len(questions)}, reviewer_qs_remaining={has_remaining_reviewer_qs}")
        
        # D. Mark COMPLETE only if 100% completeness reached AND no reviewer questions left
        if current_completeness >= 1.0 and not has_remaining_reviewer_qs:
            if followup:
                try:
                    followup.response_received = True
                    followup.status = "COMPLETE"
                    followup.response_status = "COMPLETE"
                    followup.responded_at = datetime.utcnow()
                    db.commit()
                    logger.info(f"✅ D. Follow-up marked COMPLETE: 100% completeness reached, no reviewer Qs left")
                except Exception as e:
                    logger.error(f"Error marking complete: {e}")

            _complete_msg = translate_question(
                "Thank you! All required information has been collected. This case is now 100% complete.",
                language
            )
            return {
                "status": "complete",
                "message": _complete_msg,
                "completeness": 100
            }

        # If all questions answered but not 100% complete, mark as RESPONDED
        if not should_continue:
            # D. Mark as RESPONDED (not COMPLETE) since completeness < 100%
            if followup:
                try:
                    followup.response_received = True
                    followup.status = "RESPONDED"
                    followup.response_status = "RESPONDED"
                    followup.responded_at = datetime.utcnow()
                    db.commit()
                    logger.info(f"✅ D. Follow-up marked RESPONDED: {current_completeness:.0%} complete, more data needed")
                    
                    # ADAPTIVE RE-FOLLOW-UP: Detect unanswered questions and trigger re-follow-up
                    # This fires when reporter answered some questions but skipped others
                    try:
                        re_followup_result = await ResponseProcessor.finalize_attempt(
                            db=db,
                            followup=followup,
                            case=case
                        )
                        if re_followup_result and re_followup_result.get("re_followup"):
                            logger.info(f"🔄 Re-follow-up triggered: attempt #{re_followup_result.get('attempt_number')} with {re_followup_result.get('questions_count')} questions")
                        elif re_followup_result:
                            logger.info(f"⏭️ No re-follow-up: {re_followup_result.get('reason', 'unknown')}")
                    except Exception as refollow_err:
                        logger.error(f"⚠️ Re-follow-up detection failed (non-blocking): {refollow_err}")
                except Exception as e:
                    logger.error(f"Error updating status: {e}")
            
            _responded_msg = translate_question(
                f"Thank you for your answers! Case is now {round(current_completeness * 100)}% complete. Additional follow-up may be needed.",
                language
            )
            return {
                "status": "complete",
                "message": _responded_msg,
                "completeness": round(current_completeness * 100)
            }
        
        # Get next question
        next_index = question_index + 1
        if next_index >= len(questions):
            # D. All questions answered - status already set above based on completeness
            # This should not be reached if logic above is correct
            logger.warning(f"⚠️ Reached end of questions unexpectedly at {current_completeness:.0%}")
            _end_msg = translate_question(
                f"Thank you! All questions answered. Case is {round(current_completeness * 100)}% complete.",
                language
            )
            return {
                "status": "complete",
                "message": _end_msg,
                "completeness": round(current_completeness * 100)
            }
        
        # Return next question — translated to selected language
        next_question = questions[next_index]
        
        # FIX: AI stores "question" and "field", not "question_text" and "field_name"
        question_text = next_question.get("question") or next_question.get("question_text")
        field_name_q = next_question.get("field") or next_question.get("field_name")
        
        # 🌐 Translate question text
        translated_text = translate_question(question_text, language)
        
        next_q_obj = {
            "index": next_index,
            "total": len(questions),
            "field_name": field_name_q,
            "text": translated_text,
            "original_text": question_text,
            "type": next_question.get("type", "text"),
            "options": next_question.get("options", [])
        }
        next_q_obj = _enrich_question(field_name_q, next_q_obj)
        # Translate options after enrichment
        if language != "en" and next_q_obj.get("options"):
            next_q_obj["options"] = translate_options(next_q_obj["options"], language)

        return {
            "status": "active",
            "question": next_q_obj,
            "progress": {
                "current": next_index + 1,
                "total": len(questions),
                "percentage": round((next_index + 1) / len(questions) * 100)
            },
            "previous_answer": {
                "field": field_name,
                "value": answer,
                "valid": result.get("processed", True)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing answer: {str(e)}")
        raise HTTPException(status_code=500, detail="Error processing answer")


def _generate_fallback_questions(case: AECase, language: str) -> List[Dict]:
    """Generate questions for missing critical fields - ALWAYS generate for demo"""
    questions = []
    
    # Ensure language is valid
    if language not in ["en", "hi"]:
        logger.warning(f"⚠️ Invalid language '{language}', defaulting to 'en'")
        language = "en"
    
    # ALWAYS ask these questions for demo/testing
    questions.append({
        "field_name": "event_date",
        "question_text": {
            "en": "When did the adverse event occur? (YYYY-MM-DD)",
            "hi": "प्रतिकूल घटना कब हुई? (YYYY-MM-DD)"
        }[language],
        "type": "date"
    })
    
    questions.append({
        "field_name": "event_outcome",
        "question_text": {
            "en": "What was the outcome of the event?",
            "hi": "घटना का परिणाम क्या था?"
        }[language],
        "type": "select",
        "options": [
            {"value": "Recovered", "label": {"en": "Recovered", "hi": "ठीक हो गया"}[language]},
            {"value": "Recovering", "label": {"en": "Recovering", "hi": "ठीक हो रहा है"}[language]},
            {"value": "Not Recovered", "label": {"en": "Not Recovered", "hi": "ठीक नहीं हुआ"}[language]},
            {"value": "Fatal", "label": {"en": "Fatal", "hi": "घातक"}[language]},
            {"value": "Unknown", "label": {"en": "Unknown", "hi": "अज्ञात"}[language]}
        ]
    })
    
    questions.append({
        "field_name": "patient_age",
        "question_text": {
            "en": "What is the patient's age?",
            "hi": "रोगी की आयु क्या है?"
        }[language],
        "type": "text"
    })
    
    return questions


def _should_continue_followup(
    confidence: float,
    question_index: int,
    total_questions: int,
    confidence_threshold: float = 0.85
) -> bool:
    """
    Adaptive loop logic: decide if we should ask more questions
    
    Stops if:
    - Confidence >= threshold (85%)
    - All questions answered
    """
    # Stop if confidence reached
    if confidence >= confidence_threshold:
        logger.info(f"🎯 Confidence threshold reached: {confidence:.0%} >= {confidence_threshold:.0%}")
        return False
    
    # Continue if more questions available
    if question_index + 1 < total_questions:
        return True
    
    # Stop if all questions done
    return False
