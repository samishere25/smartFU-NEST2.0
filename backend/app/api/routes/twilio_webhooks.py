"""
Twilio Webhook Handlers
Handle incoming responses from PHONE calls and WHATSAPP messages.
Updates case data and triggers re-analysis per STEP 4 rules.
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Dict
import logging

from app.db.session import get_db
from app.models.case import AECase
from app.models.followup import FollowUpAttempt
from datetime import datetime

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/followup/{case_id}/status")
async def get_followup_status(
    case_id: str,
    db: Session = Depends(get_db)
):
    """
    TEST ENDPOINT: Get follow-up status for a case
    
    Returns:
    - channel
    - language
    - questions asked
    - answers received
    - completeness %
    - current status
    """
    from app.models.case import AECase
    
    case = db.query(AECase).filter(AECase.case_id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    try:
        followup = db.query(FollowUpAttempt).filter(
            FollowUpAttempt.case_id == case_id
        ).order_by(FollowUpAttempt.sent_at.desc()).first()
    except Exception as e:
        # Database type error workaround
        logger.error(f"Database error querying follow-up: {e}")
        followup = None
    
    if not followup:
        return {
            "case_id": str(case_id),
            "primaryid": case.primaryid,
            "followup_active": False,
            "message": "No follow-up initiated for this case"
        }
    
    # Extract metadata
    metadata = followup.metadata or {}
    language = metadata.get("language", "not_set")
    answers = metadata.get("answers", [])
    current_idx = metadata.get("current_question_index", 0)
    
    # Build response
    return {
        "case_id": str(case_id),
        "primaryid": case.primaryid,
        "followup_active": True,
        "channel": followup.channel,
        "language": language,
        "status": followup.status,
        "questions_sent": len(followup.questions_sent or []),
        "questions_answered": followup.questions_answered or 0,
        "current_question_index": current_idx,
        "completeness_score": case.data_completeness_score,
        "answers": answers,
        "sent_at": followup.sent_at.isoformat() if followup.sent_at else None,
        "responded_at": followup.responded_at.isoformat() if followup.responded_at else None,
        "questions": followup.questions_sent or [],
        "response_received": followup.response_received
    }


@router.post("/twilio/voice/{case_id}")
async def handle_voice_call(
    case_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    PRODUCTION Voice Call Flow (TwiML):
    1. Identity + Language IVR (Press 1/2)
    2. Ask ONE question (first unanswered)
    3. Capture speech
    4. Confirm answer
    5. Update case
    6. Thank and end call
    
    CRITICAL CASES ONLY - enforced by channel selection
    """
    from twilio.twiml.voice_response import VoiceResponse, Gather
    
    form_data = await request.form()
    digits = form_data.get("Digits", "")
    
    response = VoiceResponse()
    
    # Get case and follow-up
    case = db.query(AECase).filter(AECase.case_id == case_id).first()
    if not case:
        response.say("Invalid case reference. Goodbye.", language="en-US")
        return Response(content=str(response), media_type="application/xml")
    
    followup = db.query(FollowUpAttempt).filter(
        FollowUpAttempt.case_id == case_id,
        FollowUpAttempt.channel == "PHONE"
    ).order_by(FollowUpAttempt.sent_at.desc()).first()
    
    if not followup:
        response.say("No active follow-up found. Goodbye.", language="en-US")
        return Response(content=str(response), media_type="application/xml")
    
    # Initialize metadata
    if not followup.metadata:
        followup.metadata = {}
    
    # STEP 1: Language Selection
    if not followup.metadata.get("language"):
        if digits:
            if digits == "1":
                followup.metadata["language"] = "en"
                followup.metadata["current_question_index"] = 0
                db.commit()
                logger.info(f"📞 Voice call - Language: English for case {case_id}")
                
                # Proceed to first question
                if followup.questions_sent and len(followup.questions_sent) > 0:
                    q = followup.questions_sent[0]
                    gather = Gather(
                        input='speech',
                        timeout=5,
                        action=f'/api/twilio/voice/{case_id}/response',
                        method='POST',
                        language="en-US"
                    )
                    gather.say(
                        f"Thank you. Question: {q.get('question', 'Please provide information.')}",
                        language="en-US"
                    )
                    response.append(gather)
                    response.say("I did not receive a response. Goodbye.", language="en-US")
                else:
                    response.say("No questions available. Thank you for your time. Goodbye.", language="en-US")
                    followup.status = "COMPLETE"
                    db.commit()
                    
            elif digits == "2":
                followup.metadata["language"] = "hi"
                followup.metadata["current_question_index"] = 0
                db.commit()
                logger.info(f"📞 Voice call - Language: Hindi for case {case_id}")
                
                # Proceed to first question in Hindi
                if followup.questions_sent and len(followup.questions_sent) > 0:
                    q = followup.questions_sent[0]
                    gather = Gather(
                        input='speech',
                        timeout=5,
                        action=f'/api/twilio/voice/{case_id}/response',
                        method='POST',
                        language="hi-IN"
                    )
                    gather.say(
                        f"धन्यवाद। प्रश्न: {q.get('question', 'कृपया जानकारी प्रदान करें।')}",
                        language="hi-IN"
                    )
                    response.append(gather)
                    response.say("मुझे कोई प्रतिक्रिया नहीं मिली। अलविदा।", language="hi-IN")
                else:
                    response.say("कोई प्रश्न उपलब्ध नहीं हैं। आपके समय के लिए धन्यवाद। अलविदा।", language="hi-IN")
                    followup.status = "COMPLETE"
                    db.commit()
            else:
                # Invalid choice - ask again
                gather = Gather(
                    num_digits=1,
                    timeout=5,
                    action=f'/api/twilio/voice/{case_id}',
                    method='POST'
                )
                gather.say(
                    "Invalid selection. Please press 1 for English or 2 for Hindi.",
                    language="en-US"
                )
                response.append(gather)
                response.say("No input received. Goodbye.", language="en-US")
        else:
            # First call - present IVR menu
            gather = Gather(
                num_digits=1,
                timeout=5,
                action=f'/api/twilio/voice/{case_id}',
                method='POST'
            )
            gather.say(
                "Hello, this is SmartFU Safety Team calling about an urgent medication safety report. "
                "Press 1 for English. Press 2 for Hindi.",
                language="en-US"
            )
            response.append(gather)
            response.say("No selection made. Goodbye.", language="en-US")
            logger.info(f"📞 Voice call initiated for case {case_id}")
    else:
        # Language already set - should not reach here, redirect to response handler
        response.redirect(f'/api/twilio/voice/{case_id}/response')
    
    return Response(content=str(response), media_type="application/xml")


@router.post("/twilio/voice/{case_id}/response")
async def handle_voice_response(
    case_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Handle spoken response with confirmation flow:
    1. Capture speech
    2. Confirm answer ("You said X, correct?")
    3. If confirmed, process and update case
    4. Thank and end call OR continue to next question
    """
    from twilio.twiml.voice_response import VoiceResponse, Gather
    from app.services.response_processor import ResponseProcessor
    
    form_data = await request.form()
    speech_result = form_data.get("SpeechResult", "")
    digits = form_data.get("Digits", "")
    
    response = VoiceResponse()
    
    followup = db.query(FollowUpAttempt).filter(
        FollowUpAttempt.case_id == case_id,
        FollowUpAttempt.channel == "PHONE"
    ).order_by(FollowUpAttempt.sent_at.desc()).first()
    
    if not followup:
        response.say("No active follow-up found. Goodbye.", language="en-US")
        return Response(content=str(response), media_type="application/xml")
    
    lang = followup.metadata.get("language", "en")
    lang_code = "en-US" if lang == "en" else "hi-IN"
    current_idx = followup.metadata.get("current_question_index", 0)
    
    if not speech_result:
        if lang == "hi":
            response.say("कोई प्रतिक्रिया नहीं मिली। कृपया पुनः प्रयास करें या बाद में संपर्क करें। अलविदा।", language=lang_code)
        else:
            response.say("No response captured. Please call back or contact us. Goodbye.", language=lang_code)
        followup.status = "NO_RESPONSE"
        db.commit()
        return Response(content=str(response), media_type="application/xml")
    
    logger.info(f"📞 Voice response captured: {speech_result}")
    
    # Process answer
    if followup.questions_sent and current_idx < len(followup.questions_sent):
        current_question = followup.questions_sent[current_idx]
        field_name = current_question.get("field")
        
        # Process response and update case
        result = await ResponseProcessor.process_response(
            db=db,
            case_id=str(case_id),
            attempt_id=str(followup.attempt_id),
            response_data={
                "answer": speech_result,
                "field_name": field_name,
                "channel": "PHONE",
                "question_index": current_idx
            },
            channel="PHONE"
        )
        
        if result.get("processed"):
            logger.info(
                f"✅ Voice response processed: "
                f"Completeness {result.get('completeness_before', 0):.0%} → {result.get('completeness_after', 0):.0%}"
            )
            
            # Store answer
            if "answers" not in followup.metadata:
                followup.metadata["answers"] = []
            followup.metadata["answers"].append({
                "field": field_name,
                "answer": speech_result,
                "index": current_idx
            })
            
            # Move to next question or end
            next_idx = current_idx + 1
            followup.metadata["current_question_index"] = next_idx
            followup.questions_answered = len(followup.metadata["answers"])
            followup.response_received = True
            
            # Check if more questions
            if next_idx < len(followup.questions_sent):
                # Has more questions - but CRITICAL calls should ask ONE question only
                # End call and thank user
                if lang == "hi":
                    response.say(
                        f"आपका उत्तर '{speech_result}' प्राप्त हुआ। रोगी सुरक्षा सुनिश्चित करने में आपकी सहायता के लिए धन्यवाद। "
                        "हम ईमेल या व्हाट्सएप के माध्यम से शेष प्रश्नों के साथ संपर्क करेंगे। अलविदा।",
                        language=lang_code
                    )
                else:
                    response.say(
                        f"Thank you. Your answer '{speech_result}' has been recorded. "
                        "We will follow up with remaining questions via email or WhatsApp. "
                        "Your cooperation helps ensure patient safety. Goodbye.",
                        language=lang_code
                    )
                followup.status = "PARTIAL_RESPONSE"
                logger.info(f"📞 CRITICAL call completed - {followup.questions_answered}/{len(followup.questions_sent)} answered")
            else:
                # All questions answered (should be just 1 for CRITICAL)
                followup.status = "COMPLETE"
                
                if lang == "hi":
                    response.say(
                        f"धन्यवाद! आपका उत्तर '{speech_result}' प्राप्त हुआ। "
                        "रोगी सुरक्षा सुनिश्चित करने में आपकी सहायता के लिए धन्यवाद। अलविदा।",
                        language=lang_code
                    )
                else:
                    response.say(
                        f"Thank you! Your answer '{speech_result}' has been recorded. "
                        "Your cooperation helps ensure patient safety. Goodbye.",
                        language=lang_code
                    )
                logger.info(f"🎉 Voice follow-up complete for case {case_id}")
            
            db.commit()
        else:
            # Processing failed
            logger.error(f"Failed to process voice response: {result.get('error')}")
            if lang == "hi":
                response.say("आपके उत्तर को संसाधित करने में त्रुटि हुई। कृपया बाद में संपर्क करें। अलविदा।", language=lang_code)
            else:
                response.say("Error processing your answer. Please contact us. Goodbye.", language=lang_code)
    else:
        if lang == "hi":
            response.say("कोई और प्रश्न नहीं हैं। धन्यवाद। अलविदा।", language=lang_code)
        else:
            response.say("No further questions. Thank you. Goodbye.", language=lang_code)
        followup.status = "COMPLETE"
        db.commit()
    
    return Response(content=str(response), media_type="application/xml")


@router.post("/twilio/recording/{case_id}")
async def handle_recording(
    case_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Handle call recording callback (for compliance)
    """
    form_data = await request.form()
    recording_url = form_data.get("RecordingUrl", "")
    recording_sid = form_data.get("RecordingSid", "")
    
    logger.info(f"📼 Recording saved for case {case_id}: {recording_sid}")
    
    # Could store recording_url in followup_attempt for audit trail
    followup = db.query(FollowUpAttempt).filter(
        FollowUpAttempt.case_id == case_id
    ).order_by(FollowUpAttempt.sent_at.desc()).first()
    
    if followup and followup.response_data:
        followup.response_data["recording_url"] = recording_url
        followup.response_data["recording_sid"] = recording_sid
        db.commit()
    
    return {"status": "ok"}


@router.post("/twilio/whatsapp/{case_id}")
async def handle_whatsapp_response(
    case_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    PRODUCTION WhatsApp Flow:
    1. First message: Ask language preference
    2. Store language in metadata
    3. Ask ONE question at a time
    4. Capture response, update case
    5. Continue or stop based on confidence
    """
    from fastapi.responses import Response
    from twilio.twiml.messaging_response import MessagingResponse
    from app.services.response_processor import ResponseProcessor
    
    form_data = await request.form()
    message_body = form_data.get("Body", "").strip()
    from_number = form_data.get("From", "")
    
    logger.info(f"💬 WhatsApp message from {from_number} for case {case_id}: {message_body}")
    
    resp = MessagingResponse()
    
    # Get active follow-up attempt
    followup = db.query(FollowUpAttempt).filter(
        FollowUpAttempt.case_id == case_id,
        FollowUpAttempt.channel == "WHATSAPP"
    ).order_by(FollowUpAttempt.sent_at.desc()).first()
    
    if not followup:
        logger.warning(f"No WhatsApp follow-up found for case {case_id}")
        resp.message("❌ No active follow-up found for this case.")
        return Response(content=str(resp), media_type="application/xml")
    
    # Initialize metadata if not exists
    if not followup.metadata:
        followup.metadata = {}
    
    # STEP 1: Language Selection
    if not followup.metadata.get("language"):
        # User is selecting language
        if message_body.lower() in ["1", "english", "en"]:
            followup.metadata["language"] = "en"
            followup.metadata["current_question_index"] = 0
            db.commit()
            logger.info(f"🌍 Language set to English for case {case_id}")
            
            # Send first question in English
            if followup.questions_sent and len(followup.questions_sent) > 0:
                q = followup.questions_sent[0]
                msg = f"""🏥 *SmartFU Safety System*
📋 Case: {case_id[:8]}

{q.get('question', '')}

{'⚠️ *CRITICAL*' if q.get('criticality') == 'CRITICAL' else ''}

Please reply with your answer."""
                resp.message(msg)
                followup.status = "AWAITING_RESPONSE"
                db.commit()
            else:
                resp.message("✅ Thank you! No further questions at this time.")
                followup.status = "COMPLETE"
                db.commit()
                
        elif message_body.lower() in ["2", "hindi", "hi", "हिंदी"]:
            followup.metadata["language"] = "hi"
            followup.metadata["current_question_index"] = 0
            db.commit()
            logger.info(f"🌍 Language set to Hindi for case {case_id}")
            
            # Send first question in Hindi
            if followup.questions_sent and len(followup.questions_sent) > 0:
                q = followup.questions_sent[0]
                msg = f"""🏥 *SmartFU सुरक्षा प्रणाली*
📋 केस: {case_id[:8]}

{q.get('question', '')}

{'⚠️ *महत्वपूर्ण*' if q.get('criticality') == 'CRITICAL' else ''}

कृपया अपना उत्तर दें।"""
                resp.message(msg)
                followup.status = "AWAITING_RESPONSE"
                db.commit()
            else:
                resp.message("✅ धन्यवाद! इस समय कोई और प्रश्न नहीं हैं।")
                followup.status = "COMPLETE"
                db.commit()
        else:
            # Invalid language selection
            resp.message("Please reply:\n1️⃣ English\n2️⃣ हिंदी")
        
        return Response(content=str(resp), media_type="application/xml")
    
    # STEP 2: Process Answer to Current Question
    lang = followup.metadata.get("language", "en")
    current_idx = followup.metadata.get("current_question_index", 0)
    
    if followup.questions_sent and current_idx < len(followup.questions_sent):
        current_question = followup.questions_sent[current_idx]
        field_name = current_question.get("field")
        
        logger.info(f"📝 Processing answer for field: {field_name}")
        
        # Process response and update case
        result = await ResponseProcessor.process_response(
            db=db,
            case_id=str(case_id),
            attempt_id=str(followup.attempt_id),
            response_data={
                "answer": message_body,
                "field_name": field_name,
                "channel": "WHATSAPP",
                "question_index": current_idx
            },
            channel="WHATSAPP"
        )
        
        if result.get("processed"):
            logger.info(
                f"✅ WhatsApp response processed: "
                f"Completeness {result.get('completeness_before', 0):.0%} → {result.get('completeness_after', 0):.0%}"
            )
            
            # Store answer in metadata
            if "answers" not in followup.metadata:
                followup.metadata["answers"] = []
            followup.metadata["answers"].append({
                "field": field_name,
                "answer": message_body,
                "index": current_idx
            })
            
            # Move to next question
            next_idx = current_idx + 1
            followup.metadata["current_question_index"] = next_idx
            followup.questions_answered = len(followup.metadata["answers"])
            
            # Check if more questions or stop
            if next_idx < len(followup.questions_sent):
                # Send next question
                next_q = followup.questions_sent[next_idx]
                
                if lang == "hi":
                    msg = f"""✅ उत्तर प्राप्त हुआ। धन्यवाद!

📋 अगला प्रश्न:

{next_q.get('question', '')}

{'⚠️ *महत्वपूर्ण*' if next_q.get('criticality') == 'CRITICAL' else ''}

कृपया उत्तर दें।"""
                else:
                    msg = f"""✅ Answer received. Thank you!

📋 Next question:

{next_q.get('question', '')}

{'⚠️ *CRITICAL*' if next_q.get('criticality') == 'CRITICAL' else ''}

Please reply with your answer."""
                
                resp.message(msg)
                logger.info(f"📤 Sent question {next_idx + 1}/{len(followup.questions_sent)}")
            else:
                # All questions answered
                followup.status = "COMPLETE"
                followup.response_received = True
                
                if lang == "hi":
                    msg = """✅ सभी प्रश्नों के उत्तर मिल गए। धन्यवाद!

रोगी सुरक्षा सुनिश्चित करने में आपकी सहायता के लिए धन्यवाद।

_SmartFU सुरक्षा प्रणाली_"""
                else:
                    msg = """✅ All questions answered. Thank you!

Your cooperation helps ensure patient safety.

_SmartFU Safety System_"""
                
                resp.message(msg)
                logger.info(f"🎉 WhatsApp follow-up complete for case {case_id}")
            
            db.commit()
        else:
            # Processing failed
            logger.error(f"Failed to process response: {result.get('error')}")
            resp.message("⚠️ Error processing your answer. Please try again or contact support.")
    else:
        # No more questions
        if lang == "hi":
            resp.message("✅ धन्यवाद! इस समय कोई और प्रश्न नहीं हैं।")
        else:
            resp.message("✅ Thank you! No further questions at this time.")
        followup.status = "COMPLETE"
        db.commit()
    
    return Response(content=str(resp), media_type="application/xml")
