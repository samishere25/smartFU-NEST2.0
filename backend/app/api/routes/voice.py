"""
Twilio Voice (Phone Call) Routes
Handles phone follow-up calls with speech recognition
"""

from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional
import logging
from twilio.twiml.voice_response import VoiceResponse, Gather

from app.db.session import get_db
from app.models.followup import FollowUpAttempt
from app.models.case import AECase
from app.services.response_processor import ResponseProcessor

router = APIRouter()
logger = logging.getLogger(__name__)


def translate_question(question_text: str, language: str) -> str:
    """
    Translate question text based on language
    Maps common question patterns to Hindi
    """
    if language != "hi":
        return question_text
    
    # Question translations (English -> Hindi)
    translations = {
        # Event outcome questions
        "What was the outcome of the adverse event?": "प्रतिकूल घटना का परिणाम क्या था?",
        "What happened to the patient after the adverse event?": "प्रतिकूल घटना के बाद रोगी को क्या हुआ?",
        "Did the patient recover?": "क्या रोगी ठीक हो गया?",
        "Is the patient still experiencing symptoms?": "क्या रोगी अभी भी लक्षणों का अनुभव कर रहा है?",
        
        # Event date questions
        "When did the adverse event occur?": "प्रतिकूल घटना कब हुई?",
        "What was the date of the adverse event?": "प्रतिकूल घटना की तारीख क्या थी?",
        "When did the event happen?": "घटना कब हुई?",
        "On what date did the event occur?": "घटना किस तारीख को हुई?",
        
        # Reporter country questions
        "In which country did the event occur?": "घटना किस देश में हुई?",
        "Which country was the reporter from?": "रिपोर्टर किस देश से था?",
        "Where did this event happen?": "यह घटना कहाँ हुई?",
        "What is the reporter's country?": "रिपोर्टर का देश क्या है?",
        
        # Product name questions
        "What was the name of the product involved?": "शामिल उत्पाद का नाम क्या था?",
        "Which product caused the adverse event?": "किस उत्पाद ने प्रतिकूल घटना का कारण बना?",
        "What product was involved?": "कौन सा उत्पाद शामिल था?",
        
        # Generic fallback for unknown questions
        "Please provide more information.": "कृपया अधिक जानकारी प्रदान करें।",
    }
    
    # Try exact match first
    if question_text in translations:
        return translations[question_text]
    
    # Try partial match for common keywords
    lower_question = question_text.lower()
    if "outcome" in lower_question:
        return "प्रतिकूल घटना का परिणाम क्या था?"
    elif "date" in lower_question or "when" in lower_question:
        return "प्रतिकूल घटना कब हुई?"
    elif "country" in lower_question or "where" in lower_question:
        return "घटना किस देश में हुई?"
    elif "product" in lower_question or "medicine" in lower_question:
        return "शामिल उत्पाद का नाम क्या था?"
    
    # Default: return original if no match
    return question_text

@router.post("/initiate")
async def initiate_phone_call(
    attempt_id: str,
    language: str = "",  # Empty string means no language selected yet
    db: Session = Depends(get_db)
):
    """
    Generate TwiML to initiate phone call
    Called by Twilio when call is answered
    Shows language selection menu first if no language selected
    """
    logger.info(f"📞 PHONE CALL INITIATED for attempt {attempt_id}")
    logger.info(f"   Language: '{language}'")
    
    try:
        # Get follow-up attempt
        attempt = db.query(FollowUpAttempt).filter(FollowUpAttempt.attempt_id == attempt_id).first()
        if not attempt:
            logger.error(f"❌ No follow-up attempt found for {attempt_id}")
            response = VoiceResponse()
            response.say("Sorry, we could not find your follow-up session. Please try again later. Goodbye.", language="en-IN")
            response.hangup()
            return Response(content=str(response), media_type="application/xml")
        
        # Get questions from response_data (primary) or questions_sent (fallback)
        questions = []
        if attempt.response_data and isinstance(attempt.response_data, dict):
            questions = attempt.response_data.get("questions", [])
            logger.info(f"   📦 response_data keys: {list(attempt.response_data.keys())}, questions count: {len(questions)}")
        else:
            logger.warning(f"   ⚠️ response_data is empty/None for attempt {attempt_id}")

        # Fallback: use questions_sent column if response_data had no questions
        if not questions and attempt.questions_sent:
            if isinstance(attempt.questions_sent, list):
                questions = attempt.questions_sent
                logger.info(f"   🔄 Fallback to questions_sent: {len(questions)} questions")
            elif isinstance(attempt.questions_sent, dict):
                questions = attempt.questions_sent.get("questions", [])
                logger.info(f"   🔄 Fallback to questions_sent dict: {len(questions)} questions")

        if not questions:
            logger.error(f"❌ No questions found in attempt {attempt_id} (response_data={attempt.response_data is not None}, questions_sent={attempt.questions_sent is not None})")
            response = VoiceResponse()
            response.say("Sorry, no follow-up questions are available at this time. Goodbye.", language="en-IN")
            response.hangup()
            return Response(content=str(response), media_type="application/xml")
        
        # Get case to check which fields are already filled
        case = db.query(AECase).filter(AECase.case_id == attempt.case_id).first()
        if not case:
            logger.error(f"❌ Case not found for attempt {attempt_id}")
            response = VoiceResponse()
            response.say("Sorry, we could not find the associated case. Goodbye.", language="en-IN")
            response.hangup()
            return Response(content=str(response), media_type="application/xml")
        
        # Filter out already answered questions
        unanswered_questions = []
        for q in questions:
            field_name = q.get("field")
            field_value = getattr(case, field_name, None) if field_name else None
            
            # Skip if field already has value
            if field_value is None or field_value == "":
                unanswered_questions.append(q)
            else:
                logger.info(f"   ⏭️ Skipping {field_name}: already answered")
        
        if not unanswered_questions:
            logger.warning(f"⏭️ All questions already answered for attempt {attempt_id}")
            # Mark as complete
            attempt.status = "COMPLETE"
            db.commit()
            
            response = VoiceResponse()
            response.say("All required information has been collected. Thank you.", language="en-IN")
            response.hangup()
            return Response(content=str(response), media_type="application/xml")
        
        # Generate TwiML
        response = VoiceResponse()
        
        # If no language selected yet, show language menu
        if not language or language == "":
            # Language selection menu
            gather = Gather(
                num_digits=1,
                action=f"/api/voice/language-select?attempt_id={attempt_id}",
                method="POST",
                timeout=5
            )
            gather.say(
                "नमस्ते। हिंदी के लिए 1 दबाएं। "
                "For English, press 2.",
                language="hi-IN"
            )
            response.append(gather)
            
            # Default to Hindi if no selection
            response.say("कोई चयन नहीं मिला। हिंदी में जारी रखते हैं।", language="hi-IN")
            response.redirect(f"/api/voice/initiate?attempt_id={attempt_id}&language=hi")
            
            return Response(content=str(response), media_type="application/xml")
        
        # Continue with questions in selected language
        lang_code = "hi-IN" if language == "hi" else "en-IN"
        
        # Greeting based on language
        if language == "hi":
            greeting = "नमस्ते। यह SmartFU सुरक्षा फॉलो-अप सिस्टम है। " \
                       "कृपया प्रतिकूल घटना रिपोर्ट के बारे में कुछ महत्वपूर्ण प्रश्नों के उत्तर दें।"
        else:
            greeting = "Hello. This is SmartFU safety follow-up system. " \
                       "Please answer a few important questions about the adverse event report."
        
        response.say(greeting, language=lang_code)
        
        # First unanswered question - find its actual index in the full questions list
        first_question = unanswered_questions[0]
        question_text_en = first_question.get("question_text", "") or first_question.get("question", "")
        # Find the actual index of this question in the original questions list
        question_index = 0
        for idx, q in enumerate(questions):
            if q.get("field") == first_question.get("field"):
                question_index = idx
                break
        
        # Translate question to selected language
        question_text = translate_question(question_text_en, language)
        
        logger.info(f"📝 Asking Question {question_index + 1}: {first_question.get('field')}")
        
        gather = Gather(
            input="speech",
            action=f"/api/voice/response?attempt_id={attempt_id}&question_index={question_index}&language={language}",
            method="POST",
            language=lang_code,
            timeout=5,
            speech_timeout="auto"
        )
        gather.say(question_text, language=lang_code)
        response.append(gather)
        
        # If no response, SKIP to next question (don't loop back to initiate — that causes infinite Q1 loop)
        no_response = "कोई जवाब नहीं मिला। अगले प्रश्न पर जा रहे हैं।" if language == "hi" else "No response received. Moving to the next question."
        response.say(no_response, language=lang_code)
        response.redirect(f"/api/voice/response?attempt_id={attempt_id}&question_index={question_index}&language={language}&skip=true")
        
        return Response(content=str(response), media_type="application/xml")

    except Exception as e:
        logger.error(f"❌ Voice initiate error for attempt {attempt_id}: {e}", exc_info=True)
        error_response = VoiceResponse()
        error_response.say("Sorry, an error occurred while processing your call. Please try again later. Goodbye.", language="en-IN")
        error_response.hangup()
        return Response(content=str(error_response), media_type="application/xml")


@router.post("/language-select")
async def handle_language_selection(
    request: Request,
    attempt_id: str,
    Digits: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Handle language selection from IVR menu
    """
    logger.info(f"🌐 LANGUAGE SELECTED: {Digits} for attempt {attempt_id}")
    
    # Map digits to language
    language = "hi" if Digits == "1" else "en"
    
    logger.info(f"   Selected language: {'Hindi' if language == 'hi' else 'English'}")
    
    # Redirect to questions with selected language
    response = VoiceResponse()
    response.redirect(f"/api/voice/initiate?attempt_id={attempt_id}&language={language}")
    
    return Response(content=str(response), media_type="application/xml")


@router.post("/response")
async def handle_phone_response(
    request: Request,
    attempt_id: str,
    question_index: int,
    language: str = "hi",
    skip: Optional[str] = None,
    finish: Optional[str] = None,
    SpeechResult: Optional[str] = Form(None),
    Confidence: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Handle spoken response from Twilio
    Save answer and continue to next question.
    skip=true means this question was skipped (no speech detected).
    finish=true means call is ending after no speech on last question.
    """
    logger.info("=" * 80)
    logger.info(f"📞 PHONE RESPONSE RECEIVED")
    logger.info(f"   Attempt ID: {attempt_id}")
    logger.info(f"   Question Index: {question_index}")
    logger.info(f"   Speech Result: {SpeechResult}")
    logger.info(f"   Confidence: {Confidence}")
    logger.info(f"   Skip: {skip}, Finish: {finish}")
    logger.info("=" * 80)

    try:
        # Get follow-up attempt
        attempt = db.query(FollowUpAttempt).filter(FollowUpAttempt.attempt_id == attempt_id).first()
        if not attempt:
            logger.error(f"❌ No follow-up attempt found for {attempt_id}")
            err = VoiceResponse()
            err.say("Sorry, session not found. Goodbye.", language="en-IN")
            err.hangup()
            return Response(content=str(err), media_type="application/xml")

        # Get questions
        questions = attempt.response_data.get("questions", []) if attempt.response_data else []

        if question_index >= len(questions):
            logger.error(f"❌ Invalid question index {question_index}")
            err = VoiceResponse()
            err.say("Sorry, an error occurred. Goodbye.", language="en-IN")
            err.hangup()
            return Response(content=str(err), media_type="application/xml")

        current_question = questions[question_index]
        field_name = current_question.get("field")

        # Process the response (only if there's actual speech, not a skip)
        if SpeechResult and not skip:
            response_data = {
                "answer": SpeechResult,
                "field_name": field_name,
                "channel": "PHONE",
                "confidence": Confidence
            }

            logger.info(f"💾 Processing response for field: {field_name}")

            # Use ResponseProcessor to save answer
            result = await ResponseProcessor.process_response(
                db=db,
                case_id=str(attempt.case_id),
                attempt_id=str(attempt.attempt_id),
                response_data=response_data
            )

            logger.info(f"✅ Response processed: {result}")
        elif skip:
            logger.info(f"⏭️ Question {question_index} ({field_name}) SKIPPED - no speech detected")

        # Get updated case to check remaining questions
        case = db.query(AECase).filter(AECase.case_id == attempt.case_id).first()
        
        # Find next unanswered question
        next_question_index = None
        for idx in range(question_index + 1, len(questions)):
            q = questions[idx]
            f = q.get("field")
            field_value = getattr(case, f, None) if f else None
            
            if field_value is None or field_value == "":
                next_question_index = idx
                break
        
        # Generate TwiML response
        twiml_response = VoiceResponse()
        lang_code = "hi-IN" if language == "hi" else "en-IN"
        
        if next_question_index is not None:
            # Ask next question
            next_question = questions[next_question_index]
            next_question_text_en = next_question.get("question_text", "") or next_question.get("question", "")

            # Translate question to selected language
            next_question_text = translate_question(next_question_text_en, language)

            logger.info(f"📝 Next Question {next_question_index + 1}: {next_question.get('field')}")

            gather = Gather(
                input="speech",
                action=f"/api/voice/response?attempt_id={attempt_id}&question_index={next_question_index}&language={language}",
                method="POST",
                language=lang_code,
                timeout=5,
                speech_timeout="auto"
            )
            gather.say(next_question_text, language=lang_code)
            twiml_response.append(gather)

            # If no speech detected, SKIP to next question instead of hanging up
            # Find the question after this one to continue the flow
            skip_to_index = None
            for skip_idx in range(next_question_index + 1, len(questions)):
                sq = questions[skip_idx]
                sf = sq.get("field")
                sf_value = getattr(case, sf, None) if sf else None
                if sf_value is None or sf_value == "":
                    skip_to_index = skip_idx
                    break

            if skip_to_index is not None:
                # There are more questions - skip this one and continue
                no_response = "कोई जवाब नहीं मिला। अगले प्रश्न पर जा रहे हैं।" if language == "hi" else "No response received. Moving to the next question."
                twiml_response.say(no_response, language=lang_code)
                twiml_response.redirect(f"/api/voice/response?attempt_id={attempt_id}&question_index={skip_to_index}&language={language}&skip=true")
            else:
                # This was the last question - end the call gracefully
                no_response = "कोई जवाब नहीं मिला। कॉल समाप्त हो रही है।" if language == "hi" else "No response received. Ending the call."
                twiml_response.say(no_response, language=lang_code)
                twiml_response.redirect(f"/api/voice/response?attempt_id={attempt_id}&question_index={next_question_index}&language={language}&finish=true")
        else:
            # All questions answered (or call finishing after skip)
            logger.info(f"✅ All questions done for attempt {attempt_id}")

            # Check completeness
            if case.data_completeness_score and case.data_completeness_score >= 1.0:
                attempt.status = "COMPLETE"
                logger.info(f"🎉 Case {case.case_id} is now 100% complete!")
            else:
                attempt.status = "RESPONDED"
                logger.info(f"📊 Case {case.case_id} completeness: {(case.data_completeness_score or 0) * 100}%")

            db.commit()

            # Finalize: cancel sister attempts + trigger re-follow-up for unanswered questions
            try:
                re_followup_result = await ResponseProcessor.finalize_attempt(
                    db=db,
                    followup=attempt,
                    case=case
                )
                if re_followup_result and re_followup_result.get("re_followup"):
                    logger.info(f"🔄 Re-follow-up triggered for unanswered questions: {re_followup_result}")
                else:
                    logger.info(f"✅ No re-follow-up needed: {re_followup_result}")
            except Exception as fin_err:
                logger.error(f"⚠️ finalize_attempt failed: {fin_err}")

            # Thank you message
            if language == "hi":
                thank_you = "जानकारी प्रदान करने के लिए धन्यवाद। फॉलो-अप पूरा हो गया है। नमस्ते।"
            else:
                thank_you = "Thank you for providing the information. This completes the follow-up. Goodbye."

            twiml_response.say(thank_you, language=lang_code)
            twiml_response.hangup()

        return Response(content=str(twiml_response), media_type="application/xml")

    except Exception as e:
        logger.error(f"❌ Voice response error for attempt {attempt_id}: {e}", exc_info=True)
        error_response = VoiceResponse()
        error_response.say("Sorry, an error occurred. Goodbye.", language="en-IN")
        error_response.hangup()
        return Response(content=str(error_response), media_type="application/xml")


@router.post("/recording/{attempt_id}")
async def handle_recording_callback(
    attempt_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Handle Twilio recording status callback.
    Called when a call recording is available.
    """
    form_data = await request.form()
    recording_url = form_data.get("RecordingUrl", "")
    recording_sid = form_data.get("RecordingSid", "")
    recording_status = form_data.get("RecordingStatus", "")

    logger.info(f"🎙️ Recording callback for attempt {attempt_id}")
    logger.info(f"   Recording URL: {recording_url}")
    logger.info(f"   Recording SID: {recording_sid}")
    logger.info(f"   Recording Status: {recording_status}")

    attempt = db.query(FollowUpAttempt).filter(
        FollowUpAttempt.attempt_id == attempt_id
    ).first()

    if attempt:
        if not attempt.response_data:
            attempt.response_data = {}
        # Store recording info alongside existing questions
        attempt.response_data["recording_url"] = recording_url
        attempt.response_data["recording_sid"] = recording_sid
        attempt.response_data["recording_status"] = recording_status
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(attempt, "response_data")
        db.commit()
        logger.info(f"   ✅ Recording info saved for attempt {attempt_id}")
    else:
        logger.warning(f"   ⚠️ Attempt {attempt_id} not found for recording callback")

    return {"status": "ok"}
