"""
WhatsApp Routes
Handles WhatsApp follow-up messages via Twilio
"""

from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.db.session import get_db
from app.models.followup import FollowUpAttempt
from app.models.case import AECase
from app.services.response_processor import ResponseProcessor
from app.services.communication_service import CommunicationService

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/webhook")
async def whatsapp_webhook(
    request: Request,
    From: str = Form(...),
    Body: str = Form(...),
    MessageSid: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Handle incoming WhatsApp messages from Twilio
    Maps responses to unanswered questions
    """
    logger.info("=" * 80)
    logger.info(f"📱 WHATSAPP MESSAGE RECEIVED")
    logger.info(f"   From: {From}")
    logger.info(f"   Body: {Body}")
    logger.info(f"   MessageSid: {MessageSid}")
    logger.info("=" * 80)
    
    # Extract phone number (Twilio format: whatsapp:+1234567890)
    phone_number = From.replace("whatsapp:", "")
    
    # Find the most recent active follow-up attempt for this phone number
    # FIX: Include "AWAITING_RESPONSE" (set by followup_trigger after successful send)
    # Also check sent_to OR recipient_email fields (sent_to may not have been set in older attempts)
    attempt = (
        db.query(FollowUpAttempt)
        .join(AECase, FollowUpAttempt.case_id == AECase.case_id)
        .filter(FollowUpAttempt.channel == "WHATSAPP")
        .filter(FollowUpAttempt.status.in_(["SENT", "RESPONDED", "AWAITING_RESPONSE", "PENDING"]))
        .filter(FollowUpAttempt.sent_to == phone_number)
        .order_by(FollowUpAttempt.created_at.desc())
        .first()
    )
    
    # FIX: If not found by sent_to, try finding by channel only (sent_to may be NULL)
    if not attempt:
        logger.info(f"🔍 No attempt found with sent_to={phone_number}, trying channel-only lookup...")
        attempt = (
            db.query(FollowUpAttempt)
            .join(AECase, FollowUpAttempt.case_id == AECase.case_id)
            .filter(FollowUpAttempt.channel == "WHATSAPP")
            .filter(FollowUpAttempt.status.in_(["SENT", "RESPONDED", "AWAITING_RESPONSE", "PENDING"]))
            .filter(FollowUpAttempt.sent_to.is_(None))  # sent_to was never set
            .order_by(FollowUpAttempt.created_at.desc())
            .first()
        )
        if attempt:
            # Backfill sent_to for future lookups
            attempt.sent_to = phone_number
            db.commit()
            logger.info(f"✅ Found attempt {attempt.attempt_id} (backfilled sent_to={phone_number})")
    
    if not attempt:
        logger.warning(f"⚠️ No active WhatsApp follow-up found for {phone_number}")
        # Send friendly message
        comm_service = CommunicationService()
        comm_service.send_whatsapp_message(
            to_number=phone_number,
            message="Sorry, we couldn't find an active follow-up for this number. Please contact support."
        )
        return {"status": "no_active_followup"}
    
    # Get questions from response_data
    questions = attempt.response_data.get("questions", []) if attempt.response_data else []
    
    if not questions:
        logger.error(f"❌ No questions found in attempt {attempt.id}")
        return {"status": "no_questions"}
    
    # Get case
    case = db.query(AECase).filter(AECase.case_id == attempt.case_id).first()
    if not case:
        logger.error(f"❌ Case not found: {attempt.case_id}")
        return {"status": "case_not_found"}
    
    # Find next unanswered question
    unanswered_question = None
    question_index = 0
    
    for idx, q in enumerate(questions):
        field_name = q.get("field")
        field_value = getattr(case, field_name, None) if field_name else None
        
        if field_value is None or field_value == "":
            unanswered_question = q
            question_index = idx
            break
    
    if not unanswered_question:
        logger.info(f"✅ All questions answered for attempt {attempt.id}")
        
        # Mark as complete
        if case.data_completeness_score >= 1.0:
            attempt.status = "COMPLETE"
            logger.info(f"🎉 Case {case.case_id} is now 100% complete!")
        else:
            attempt.status = "RESPONDED"
        
        db.commit()
        
        # Send thank you message
        comm_service = CommunicationService()
        comm_service.send_whatsapp_message(
            to_number=phone_number,
            message="Thank you for providing all the required information. This completes the follow-up."
        )
        
        return {"status": "completed"}
    
    # Process the response for the current unanswered question
    field_name = unanswered_question.get("field")
    
    logger.info(f"💾 Processing WhatsApp response for field: {field_name}")
    logger.info(f"   Answer: {Body}")
    
    response_data = {
        "answer": Body,
        "field_name": field_name,
        "channel": "WHATSAPP"
    }
    
    # Use ResponseProcessor to save answer
    try:
        result = await ResponseProcessor.process_response(
            db=db,
            case_id=str(attempt.case_id),
            attempt_id=str(attempt.attempt_id),
            response_data=response_data,
            channel="WHATSAPP"
        )
        
        if not result.get("processed"):
            logger.error(f"❌ Response processing failed: {result.get('error', 'Unknown')}")
        else:
            logger.info(f"✅ Response processed: {result}")
    except Exception as proc_error:
        logger.error(f"❌ ResponseProcessor exception: {proc_error}", exc_info=True)
        result = {"processed": False, "error": str(proc_error)}
    
    # Refresh case after update
    db.refresh(case)
    
    # Find next unanswered question to ask
    next_question = None
    for idx in range(question_index + 1, len(questions)):
        q = questions[idx]
        f = q.get("field")
        field_value = getattr(case, f, None) if f else None
        
        if field_value is None or field_value == "":
            next_question = q
            break
    
    comm_service = CommunicationService()
    
    if next_question:
        # Ask next question
        next_question_text = next_question.get("question_text", "") or next_question.get("question", "")
        
        logger.info(f"📝 Sending next WhatsApp question: {next_question.get('field')}")
        
        send_result = comm_service.send_whatsapp_message(
            to_number=phone_number,
            message=next_question_text
        )
        
        if send_result.get("success"):
            logger.info(f"✅ Next question sent successfully: {next_question.get('field')}")
        else:
            logger.error(f"❌ Failed to send next question: {send_result.get('error')}")
        
        # Update status to RESPONDED (more questions pending)
        attempt.status = "RESPONDED"
        db.commit()
    else:
        # All questions answered
        logger.info(f"✅ All questions answered")
        
        # Check completeness
        if case.data_completeness_score >= 1.0:
            attempt.status = "COMPLETE"
            logger.info(f"🎉 Case {case.case_id} is now 100% complete!")
            thank_you_msg = "Thank you! All required information has been collected. This case is now complete."
        else:
            attempt.status = "RESPONDED"
            completeness_pct = int(case.data_completeness_score * 100)
            logger.info(f"📊 Case {case.case_id} completeness: {completeness_pct}%")
            thank_you_msg = f"Thank you for the information. Case is now {completeness_pct}% complete."
        
        db.commit()
        
        comm_service.send_whatsapp_message(
            to_number=phone_number,
            message=thank_you_msg
        )
    
    return {"status": "processed", "field": field_name}


@router.get("/status")
async def whatsapp_status():
    """Health check for WhatsApp webhook"""
    return {"status": "ok", "service": "whatsapp"}
