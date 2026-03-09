"""
Follow-Up Response Processor
Handles responses from Email/Phone/WhatsApp and updates case data.

WORKFLOW:
When response received → map answers to CIOMS fields → update case → recalculate completeness
→ If partial response (some questions unanswered) and attempt < MAX_ATTEMPTS,
  schedule a re-follow-up for ONLY the remaining unanswered questions.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from dateutil import parser as date_parser

from app.models.case import AECase
from app.models.followup import FollowUpAttempt, FollowUpResponse, FieldUpdateHistory
from app.services.data_completeness import DataCompletenessService

logger = logging.getLogger(__name__)


class ResponseProcessor:
    """
    Process follow-up responses and update case data.
    
    WORKFLOW:
    1. Extract answer from response
    2. Map to corresponding CIOMS field
    3. Update case record
    4. Recalculate completeness
    5. Update FollowUpAttempt status to RESPONDED
    6. If partial response → detect unanswered → trigger re-follow-up (max 3 attempts)
    """
    
    MAX_FOLLOW_UP_ATTEMPTS = 3  # Industry standard for pharmacovigilance
    
    @staticmethod
    async def process_response(
        db: Session,
        case_id: str,
        attempt_id: str = None,  # Made optional
        response_data: Dict = None,
        channel: str = "EMAIL"
    ) -> Dict:
        """
        Process a follow-up response and update case data.
        
        Args:
            db: Database session
            case_id: Case UUID
            attempt_id: FollowUpAttempt UUID (optional - may fail due to database type error)
            response_data: Response payload (answer, question_id, etc.)
            channel: Communication channel (EMAIL/PHONE/WHATSAPP)
        
        Returns:
            Processing result with updated completeness
        """
        try:
            # STEP 1: LOG INCOMING DATA
            logger.info("="*80)
            logger.info("🔍 RESPONSE PROCESSOR - INCOMING DATA")
            logger.info(f"   Case ID: {case_id}")
            logger.info(f"   Attempt ID: {attempt_id}")
            logger.info(f"   Response Data: {response_data}")
            logger.info(f"   Channel: {channel}")
            logger.info("="*80)
            
            # Get case
            case = db.query(AECase).filter(AECase.case_id == case_id).first()
            if not case:
                raise ValueError(f"Case {case_id} not found")
            
            # Try to get followup attempt (skip if database error or not provided)
            followup = None
            if attempt_id:
                try:
                    followup = db.query(FollowUpAttempt).filter(
                        FollowUpAttempt.attempt_id == attempt_id
                    ).first()
                except Exception as db_error:
                    logger.warning(f"⚠️ FollowUpAttempt query failed (known type 25 error): {str(db_error)}")
                    logger.info("💡 Continuing without followup attempt update...")
            
            # Extract answer
            answer_text = response_data.get("answer", "")
            question_field = response_data.get("field_name", None)
            
            if not answer_text:
                logger.warning(f"Empty response received for case {case_id}")
                return {
                    "processed": False,
                    "reason": "Empty answer"
                }
            
            # Capture the PREVIOUS value of the target field before update
            previous_values = {}
            if question_field:
                mapped = ResponseProcessor.FIELD_MAP.get(question_field, question_field)
                if hasattr(case, mapped):
                    prev = getattr(case, mapped)
                    previous_values[mapped] = str(prev) if prev is not None else None

            # Resolve question text from the attempt's sent questions
            question_text_resolved = response_data.get("question_text")
            question_id_resolved = response_data.get("question_id")
            if not question_text_resolved and followup and followup.response_data:
                sent_qs = followup.response_data.get("questions", []) if isinstance(followup.response_data, dict) else []
                for q in sent_qs:
                    qf = q.get("field") or q.get("field_name")
                    if qf == question_field:
                        question_text_resolved = q.get("question_text") or q.get("question")
                        question_id_resolved = question_id_resolved or q.get("id") or q.get("question_id")
                        break

            # Map answer to CIOMS field and update case
            updated_fields = ResponseProcessor._map_and_update_case(
                case=case,
                question_field=question_field,
                answer=answer_text,
                followup=followup  # May be None
            )
            
            # ── PERSIST FollowUpResponse + FieldUpdateHistory ──────────
            response_record = None
            attempt_num = None
            if followup:
                attempt_num = followup.iteration_number or followup.attempt_number or 1

            for field in updated_fields:
                new_val = str(getattr(case, field)) if getattr(case, field) is not None else None
                prev_val = previous_values.get(field)

                response_record = FollowUpResponse(
                    attempt_id=followup.attempt_id if followup else None,
                    case_id=case.case_id,
                    question_id=question_id_resolved,
                    question_text=question_text_resolved,
                    field_name=field,
                    response_text=answer_text,
                    field_value=new_val,
                    previous_value=prev_val,
                    value_type=type(getattr(case, field)).__name__ if getattr(case, field) is not None else "str",
                    channel=response_data.get("channel", channel),
                    attempt_number=attempt_num,
                    is_complete=True,
                    is_validated=False,
                    processed=True,
                    ai_extracted_value=response_data.get("ai_extracted_value"),
                    extraction_confidence=float(response_data.get("confidence", 0)) if response_data.get("confidence") else None,
                    responded_at=datetime.utcnow(),
                )
                db.add(response_record)

                # Field update history (old → new provenance)
                history = FieldUpdateHistory(
                    case_id=case.case_id,
                    field_name=field,
                    old_value=prev_val,
                    new_value=new_val,
                    source=response_data.get("channel", channel),
                    changed_by="reporter",
                    changed_at=datetime.utcnow(),
                )
                db.add(history)

            # If the answer didn't update any fields (FIRST-WRITE-WINS skip),
            # still record the response for audit trail
            if not updated_fields and question_field:
                mapped_field = ResponseProcessor.FIELD_MAP.get(question_field, question_field)
                existing_val = str(getattr(case, mapped_field)) if hasattr(case, mapped_field) and getattr(case, mapped_field) is not None else None
                response_record = FollowUpResponse(
                    attempt_id=followup.attempt_id if followup else None,
                    case_id=case.case_id,
                    question_id=question_id_resolved,
                    question_text=question_text_resolved,
                    field_name=mapped_field,
                    response_text=answer_text,
                    field_value=existing_val,
                    previous_value=existing_val,
                    value_type="str",
                    channel=response_data.get("channel", channel),
                    attempt_number=attempt_num,
                    is_complete=False,
                    is_validated=False,
                    processed=False,  # Not applied — FIRST-WRITE-WINS
                    responded_at=datetime.utcnow(),
                )
                db.add(response_record)
            
            # STEP 3: COMMIT THE FIELD UPDATE FIRST
            logger.info("="*80)
            logger.info("💾 DATABASE COMMIT (FIELD UPDATE)")
            for field in updated_fields:
                logger.info(f"   BEFORE COMMIT: {field} = {getattr(case, field)}")
            
            db.commit()
            logger.info("   ✅ Transaction committed")
            
            # Refetch to verify persistence
            db.refresh(case)
            logger.info("   Verification after commit:")
            for field in updated_fields:
                logger.info(f"   AFTER COMMIT: {field} = {getattr(case, field)}")
            logger.info("="*80)

            # ── AUDIT TRAIL: log response received ──────────
            try:
                from app.services.audit_service import AuditService
                AuditService.log_followup_response_received(
                    db=db,
                    case_id=case.case_id,
                    channel=response_data.get("channel", channel),
                    fields_updated=updated_fields,
                    response_id=str(response_record.response_id) if response_record else None,
                    attempt_id=str(followup.attempt_id) if followup else None,
                )
            except Exception as audit_err:
                logger.warning(f"⚠️ Audit log failed (non-blocking): {audit_err}")
            
            # STEP 4: RECALCULATE COMPLETENESS AFTER SAVING
            logger.info("🔄 RECALCULATING COMPLETENESS...")
            logger.info(f"   event_outcome = {case.event_outcome}")
            logger.info(f"   event_date = {case.event_date}")
            logger.info(f"   drug_dose = {case.drug_dose}")
            logger.info(f"   reporter_country = {case.reporter_country}")
            
            completeness_result = ResponseProcessor._recalculate_completeness(case)
            
            # Update case completeness score
            old_score = case.data_completeness_score or 0.0
            new_score = completeness_result.get("completeness_score", 0.0)
            case.data_completeness_score = new_score
            case.updated_at = datetime.utcnow()
            
            logger.info(f"📊 COMPLETENESS RECALCULATED:")
            logger.info(f"   OLD: {old_score:.0%}")
            logger.info(f"   NEW: {new_score:.0%}")
            logger.info("="*80)
            
            # STEP 5: UPDATE FOLLOWUP STATUS BASED ON NEW COMPLETENESS
            if followup:
                try:
                    followup.response_received = True
                    followup.responded_at = datetime.utcnow()
                    followup.questions_answered = (followup.questions_answered or 0) + len(updated_fields)
                    
                    logger.info("="*80)
                    logger.info("📊 FOLLOW-UP STATUS UPDATE")
                    logger.info(f"   Fields updated: {len(updated_fields)}")
                    logger.info(f"   Completeness: {new_score:.0%}")
                    
                    # CRITICAL: Only mark COMPLETE if completeness = 100%
                    if new_score >= 1.0:
                        followup.response_status = "COMPLETE"
                        followup.status = "COMPLETE"
                        logger.info(f"   ✅ STATUS: COMPLETE (100% complete)")
                    elif len(updated_fields) > 0:
                        followup.response_status = "RESPONDED"
                        followup.status = "RESPONDED"
                        logger.info(f"   ✅ STATUS: RESPONDED ({new_score:.0%} complete, more questions needed)")
                    else:
                        followup.response_status = "PENDING"
                        followup.status = "PENDING"
                        logger.info(f"   ⚠️ STATUS: PENDING (no fields updated)")
                    logger.info("="*80)
                    
                    # FIX: Store ALL answers as array - don't overwrite previous answers
                    if followup.response_data and isinstance(followup.response_data, dict):
                        # Append to answers array (preserve questions list)
                        if "answers" not in followup.response_data:
                            followup.response_data["answers"] = []
                        followup.response_data["answers"].append({
                            "field_name": response_data.get("field_name"),
                            "answer": response_data.get("answer"),
                            "answered_at": datetime.utcnow().isoformat(),
                            "channel": response_data.get("channel", channel)
                        })
                    else:
                        followup.response_data = {
                            "answers": [{
                                "field_name": response_data.get("field_name"),
                                "answer": response_data.get("answer"),
                                "answered_at": datetime.utcnow().isoformat(),
                                "channel": response_data.get("channel", channel)
                            }]
                        }

                    # CRITICAL: Tell SQLAlchemy the JSON column was mutated in-place
                    flag_modified(followup, "response_data")

                    # Calculate response time
                    if followup.sent_at:
                        time_diff = datetime.utcnow() - followup.sent_at
                        followup.response_time_hours = time_diff.total_seconds() / 3600
                except Exception as update_error:
                    logger.warning(f"⚠️ Failed to update followup attempt: {str(update_error)}")
            
            # Final commit
            db.commit()
            
            logger.info(
                f"✅ Response processed for case {case_id}: "
                f"{len(updated_fields)} fields updated, "
                f"completeness: {new_score:.0%}"
            )
            
            return {
                "processed": True,
                "case_id": str(case_id),
                "attempt_id": str(attempt_id) if attempt_id else None,
                "channel": channel,
                "fields_updated": updated_fields,
                "completeness_before": completeness_result.get("completeness_before", 0.0),
                "completeness_after": completeness_result.get("completeness_score", 0.0),
                "information_gain": completeness_result.get("information_gain", 0.0)
            }
            
        except Exception as e:
            logger.error(f"Response processing failed: {e}", exc_info=True)
            return {
                "processed": False,
                "error": str(e)
            }
    
    # STEP 2: STRICT FIELD MAPPING
    # Maps follow-up question field names to actual AECase model attributes
    FIELD_MAP = {
        "event_outcome": "event_outcome",
        "event_date": "event_date",
        "drug_dose": "drug_dose",
        "drug_route": "drug_route",
        "reporter_country": "reporter_country",
        "reporter_type": "reporter_type",
        "patient_age": "patient_age",
        "patient_sex": "patient_sex",
        # CIOMS / extended fields
        "reaction_description": "adverse_event",
        "reaction_onset": "event_date",
        "laboratory_tests": "medical_history",  # closest CIOMS field
        "concomitant_drugs": "concomitant_drugs",
        "medical_history": "medical_history",
        "indication": "indication",
        "patient_initials": "patient_initials",
        "dechallenge": "dechallenge",
        "rechallenge": "rechallenge",
        "therapy_start": "therapy_start",
        "therapy_end": "therapy_end",
        "manufacturer_name": "manufacturer_name",
        "reporter_email": "reporter_email",
        "reporter_phone": "reporter_phone",
    }
    
    @staticmethod
    def _map_and_update_case(
        case: AECase,
        question_field: Optional[str],
        answer: str,
        followup: FollowUpAttempt
    ) -> List[str]:
        """
        Map answer to CIOMS field and update case record.
        
        FIRST-WRITE-WINS DEDUP: If a field already has a non-null value
        (from another channel's earlier response), DO NOT overwrite it.
        This ensures the first channel to respond takes priority in
        multi-channel simultaneous follow-ups.
        
        Args:
            case: AECase instance
            question_field: Field name from question (if available)
            answer: Answer text
            followup: FollowUpAttempt with questions in response_data
        
        Returns:
            List of updated field names
        """
        updated_fields = []
        
        # STEP 2: Apply field mapping
        logger.info("="*80)
        logger.info("🔧 FIELD MAPPING & UPDATE")
        logger.info(f"   Question field: {question_field}")
        logger.info(f"   Answer value: {answer}")
        
        # If question_field specified, map and update that specific field
        if question_field:
            # Map to actual field name
            mapped_field = ResponseProcessor.FIELD_MAP.get(question_field, question_field)
            logger.info(f"   Mapped field: {mapped_field}")
            
            # ── FIX: Handle reviewer/repo fields that don't exist on AECase ──
            # Reviewer questions have field_name like "reviewer_note_1", "reviewer_q_1"
            # These don't exist on AECase — store in review_notes instead of crashing
            if not hasattr(case, mapped_field):
                if "reviewer" in question_field.lower() or "repo" in question_field.lower() or "checklist" in question_field.lower():
                    logger.info(f"   📝 Reviewer/repo field '{question_field}' — storing answer in review_notes")
                    existing_notes = case.review_notes or ""
                    separator = "\n" if existing_notes else ""
                    case.review_notes = f"{existing_notes}{separator}[{question_field}]: {answer}"
                    updated_fields.append("review_notes")
                    logger.info(f"   ✅ SAVED reviewer answer to review_notes: {question_field} = {answer[:80]}")
                    return updated_fields
                else:
                    error_msg = f"❌ FIX #2 CRITICAL ERROR: AECase has no attribute '{mapped_field}'!"
                    logger.error(error_msg)
                    logger.error(f"   Question field '{question_field}' cannot be saved.")
                    logger.error(f"   Add mapping: FIELD_MAP['{question_field}'] = '<correct_field_name>'")
                    raise ValueError(error_msg)
            
            # FIRST-WRITE-WINS: Skip if field already has data (another channel responded first)
            existing_value = getattr(case, mapped_field)
            if existing_value is not None and str(existing_value).strip():
                logger.info(f"   ⏭️ FIRST-WRITE-WINS: {mapped_field} already has value '{existing_value}' — skipping (another channel responded first)")
                return updated_fields
            
            # STEP 3: Log BEFORE update
            logger.info(f"   BEFORE: {mapped_field} = {existing_value}")
            
            # STEP 4 FIX: Normalize and type-convert speech answers before saving
            # Speech recognition returns natural language - must convert to DB types
            import re

            if mapped_field == 'event_outcome' and answer:
                answer = answer.upper().strip()
                logger.info(f"   🔧 NORMALIZED event_outcome: {answer}")

            # Parse date fields (DateTime columns)
            if 'date' in mapped_field.lower() and isinstance(answer, str):
                try:
                    parsed_date = date_parser.parse(answer, fuzzy=True)
                    setattr(case, mapped_field, parsed_date)
                    logger.info(f"   ✅ SAVED: {mapped_field} = {parsed_date} (parsed from: {answer})")
                except Exception as e:
                    logger.warning(f"   ⚠️ Could not parse date '{answer}': {e}. Storing as NULL.")
                    setattr(case, mapped_field, None)

            # Parse integer fields (patient_age) - extract number from speech like "45 years old"
            elif mapped_field == 'patient_age' and isinstance(answer, str):
                # Word-to-number mapping for common speech patterns
                word_numbers = {
                    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
                    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
                    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
                    "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
                    "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
                }
                age_val = None
                # Try extracting digits first (e.g. "45 years old" → 45)
                nums = re.findall(r'\d+', answer)
                if nums:
                    age_val = int(nums[0])
                else:
                    # Try word numbers (e.g. "forty five" → 45)
                    lower_ans = answer.lower().strip()
                    for word, num in word_numbers.items():
                        if word in lower_ans:
                            age_val = num
                            break
                if age_val is not None and 0 < age_val < 150:
                    setattr(case, mapped_field, age_val)
                    logger.info(f"   ✅ SAVED: {mapped_field} = {age_val} (parsed from speech: '{answer}')")
                else:
                    logger.warning(f"   ⚠️ Could not parse age from '{answer}'. Skipping.")

            # Parse country fields - truncate/normalize for String(5) column
            elif mapped_field == 'reporter_country' and isinstance(answer, str):
                # Map common spoken country names to ISO codes
                country_map = {
                    "india": "IN", "united states": "US", "america": "US", "usa": "US",
                    "uk": "GB", "united kingdom": "GB", "england": "GB", "britain": "GB",
                    "canada": "CA", "germany": "DE", "france": "FR", "japan": "JP",
                    "china": "CN", "australia": "AU", "brazil": "BR", "italy": "IT",
                    "spain": "ES", "mexico": "MX", "russia": "RU", "south korea": "KR",
                }
                lower_ans = answer.lower().strip()
                country_code = country_map.get(lower_ans, answer.strip()[:5].upper())
                setattr(case, mapped_field, country_code)
                logger.info(f"   ✅ SAVED: {mapped_field} = {country_code} (parsed from speech: '{answer}')")

            # Parse sex field - normalize to M/F
            elif mapped_field == 'patient_sex' and isinstance(answer, str):
                lower_ans = answer.lower().strip()
                if any(w in lower_ans for w in ["male", "man", "boy", "पुरुष", "लड़का"]):
                    sex_val = "M"
                elif any(w in lower_ans for w in ["female", "woman", "girl", "महिला", "लड़की"]):
                    sex_val = "F"
                else:
                    sex_val = answer.strip()[:10]
                setattr(case, mapped_field, sex_val)
                logger.info(f"   ✅ SAVED: {mapped_field} = {sex_val} (parsed from speech: '{answer}')")

            else:
                setattr(case, mapped_field, answer)
                logger.info(f"   ✅ SAVED: {mapped_field} = {answer}")
            
            # STEP 7 debug log
            logger.info(f"✅ SAVED FIELD: {mapped_field} = {answer}")
            
            updated_fields.append(mapped_field)
            logger.info(f"   Updated fields: {updated_fields}")
            logger.info("="*80)
            return updated_fields
        
        # A. Read questions from response_data ONLY - NO FALLBACK
        questions_list = None
        if followup:
            if followup.response_data and isinstance(followup.response_data, dict):
                questions_list = followup.response_data.get("questions", [])
                if questions_list:
                    logger.info(f"   ✅ Found {len(questions_list)} questions in response_data")
            
            if not questions_list:
                logger.warning("   ⚠️ No questions found in response_data")
        
        # Map answer to field from questions
        if questions_list:
            for question in questions_list:
                # AI stores as "field", legacy uses "field_name"
                field_name = question.get("field") or question.get("field_name")
                if field_name and hasattr(case, field_name):
                    # FIRST-WRITE-WINS: Skip if field already has data
                    existing_val = getattr(case, field_name)
                    if existing_val is not None and str(existing_val).strip():
                        logger.info(f"⏭️ FIRST-WRITE-WINS: {field_name} already has value '{existing_val}' — skipping")
                        continue
                    
                    # Parse date fields
                    if 'date' in field_name.lower() and isinstance(answer, str):
                        try:
                            parsed_date = date_parser.parse(answer, fuzzy=True)
                            setattr(case, field_name, parsed_date)
                            logger.info(f"✅ Updated case field: {field_name} = {parsed_date} (parsed from: {answer})")
                        except Exception as e:
                            logger.warning(f"Could not parse date '{answer}': {e}. Storing as NULL.")
                            setattr(case, field_name, None)
                    else:
                        setattr(case, field_name, answer)
                        logger.info(f"✅ Updated case field: {field_name} = {answer}")
                    
                    updated_fields.append(field_name)
                    break  # Only update first question (one question per follow-up)
        
        # If still no field, log warning
        if not updated_fields:
            logger.warning(f"Could not map answer to case field for case {case.case_id}")
        
        return updated_fields
    
    @staticmethod
    def _recalculate_completeness(case: AECase) -> Dict:
        """
        Recalculate data completeness for case.
        
        Uses existing DataCompletenessAgent logic.
        
        Args:
            case: AECase instance
        
        Returns:
            Completeness analysis result
        """
        # Prepare case data
        case_data = {
            "primaryid": case.primaryid,
            "suspect_drug": case.suspect_drug,
            "adverse_event": case.adverse_event,
            "reporter_type": case.reporter_type,
            "patient_age": case.patient_age,
            "patient_sex": case.patient_sex,
            "drug_route": case.drug_route,
            "drug_dose": case.drug_dose,
            "event_date": case.event_date,
            "event_outcome": case.event_outcome,
            "reporter_country": case.reporter_country,
            "is_serious": case.is_serious,
            "patient_initials": getattr(case, "patient_initials", None),
            "receipt_date": getattr(case, "receipt_date", None),
        }
        
        # Run completeness analysis
        completeness_result = DataCompletenessService.analyze_case(case_data)
        
        return completeness_result

    @staticmethod
    def _detect_unanswered_fields(followup: FollowUpAttempt) -> List[Dict]:
        """
        Compare questions sent vs answers received to find unanswered questions.
        
        Returns list of unanswered question dicts (same format as original questions).
        """
        if not followup or not followup.response_data or not isinstance(followup.response_data, dict):
            return []
        
        questions = followup.response_data.get("questions", [])
        answers = followup.response_data.get("answers", [])
        
        if not questions:
            return []
        
        # Build set of answered field names
        answered_fields = set()
        for ans in answers:
            field = ans.get("field_name") or ans.get("field")
            if field:
                answered_fields.add(field)
        
        # Find questions whose fields were NOT answered
        unanswered = []
        for q in questions:
            field = q.get("field") or q.get("field_name")
            if field and field not in answered_fields:
                unanswered.append(q)
        
        return unanswered

    @staticmethod
    async def finalize_attempt(
        db: Session,
        followup: FollowUpAttempt,
        case: AECase
    ) -> Optional[Dict]:
        """
        Called when a follow-up session ends (all questions presented to reporter).
        Detects unanswered questions and triggers a re-follow-up if needed.
        
        MULTI-CHANNEL AWARE:
        - Cancels sister attempts on other channels (same decision_id)
        - Counts ROUNDS (unique decision_ids) for MAX_ATTEMPTS, not individual attempts
        - Only re-triggers if CRITICAL/HIGH questions remain unanswered
        
        Returns:
            Re-follow-up result dict if triggered, None otherwise
        """
        try:
            unanswered = ResponseProcessor._detect_unanswered_fields(followup)
            
            if not unanswered:
                logger.info(f"✅ All questions answered for attempt {followup.attempt_id} — no re-follow-up needed")
                # Cancel sister attempts on other channels (they're no longer needed)
                ResponseProcessor._cancel_sister_attempts(db, followup)
                return None
            
            logger.info(f"🔄 PARTIAL RESPONSE DETECTED for case {case.case_id}")
            logger.info(f"   Questions sent: {followup.questions_count or 0}")
            logger.info(f"   Questions answered: {followup.questions_answered or 0}")
            logger.info(f"   Unanswered: {len(unanswered)}")
            for q in unanswered:
                f = q.get("field") or q.get("field_name")
                c = q.get("criticality", "MEDIUM")
                logger.info(f"      ❓ {f} ({c})")
            
            # Store unanswered fields in response_data for downstream tracking
            if followup.response_data and isinstance(followup.response_data, dict):
                followup.response_data["unanswered"] = [
                    {"field": q.get("field") or q.get("field_name"), "criticality": q.get("criticality", "MEDIUM")}
                    for q in unanswered
                ]
                flag_modified(followup, "response_data")
            
            # Mark as PARTIAL_RESPONSE
            followup.status = "PARTIAL_RESPONSE"
            followup.response_status = "PARTIAL_RESPONSE"
            
            # Cancel sister attempts on other channels
            ResponseProcessor._cancel_sister_attempts(db, followup)
            
            db.commit()
            
            # Count total ROUNDS (unique decision_ids) for this case — not individual attempts
            from sqlalchemy import func
            total_rounds = db.query(func.count(func.distinct(FollowUpAttempt.decision_id))).filter(
                FollowUpAttempt.case_id == case.case_id,
                FollowUpAttempt.status.notin_(["EXPIRED", "FAILED"])
            ).scalar() or 0
            
            if total_rounds >= ResponseProcessor.MAX_FOLLOW_UP_ATTEMPTS:
                logger.info(f"⛔ MAX ROUNDS ({ResponseProcessor.MAX_FOLLOW_UP_ATTEMPTS}) reached for case {case.case_id} — no more re-follow-ups")
                return {"re_followup": False, "reason": "max_attempts_reached", "total_rounds": total_rounds}
            
            # Filter to only CRITICAL/HIGH unanswered questions (don't chase LOW/MEDIUM on re-ask)
            critical_unanswered = [
                q for q in unanswered
                if q.get("criticality", "MEDIUM").upper() in ("CRITICAL", "HIGH")
            ]
            
            if not critical_unanswered:
                logger.info(f"⏭️ Only MEDIUM/LOW questions unanswered — skipping re-follow-up")
                return {"re_followup": False, "reason": "only_low_priority_unanswered", "unanswered_count": len(unanswered)}
            
            # Boost priority for re-asked questions
            for q in critical_unanswered:
                q["is_re_followup"] = True
                q["re_ask_attempt"] = total_rounds + 1
                # If it was HIGH, escalate to CRITICAL on re-ask
                if q.get("criticality", "").upper() == "HIGH":
                    q["criticality"] = "CRITICAL"
                    q["escalated_reason"] = "Unanswered in previous follow-up"
            
            logger.info(f"🚀 TRIGGERING RE-FOLLOW-UP for case {case.case_id}")
            logger.info(f"   Round #{total_rounds + 1} with {len(critical_unanswered)} questions")
            
            # Build analysis_result for the trigger (reuse case data)
            analysis_result = {
                "decision": "PROCEED",
                "risk_score": case.seriousness_score or 0.5,
                "completeness_score": case.data_completeness_score or 0.0,
                "followup_required": True,
                "stop_followup": False,
                "response_probability": 0.5,
                "risk_level": "HIGH",  # Re-follow-ups are inherently important
                "is_re_followup": True,
                "parent_attempt_id": str(followup.attempt_id),
                "attempt_number": total_rounds + 1,
            }
            
            from app.services.followup_trigger import FollowUpTrigger
            re_followup_result = await FollowUpTrigger.trigger_automated_followup(
                db=db,
                case=case,
                analysis_result=analysis_result,
                questions=critical_unanswered,
                user_id=None
            )
            
            logger.info(f"{'✅' if re_followup_result.get('success') else '❌'} Re-follow-up result: {re_followup_result.get('message', '')}")
            
            return {
                "re_followup": True,
                "round_number": total_rounds + 1,
                "questions_count": len(critical_unanswered),
                "channels": re_followup_result.get("successful_channels", []),
                "result": re_followup_result
            }
            
        except Exception as e:
            logger.error(f"❌ Re-follow-up trigger failed: {e}", exc_info=True)
            return {"re_followup": False, "error": str(e)}
    
    @staticmethod
    def _cancel_sister_attempts(db: Session, responded_attempt: FollowUpAttempt):
        """
        Cancel other channel attempts for the same decision_id (same round).
        When one channel gets a response, other channels for the same round
        should be marked as SUPERSEDED to prevent duplicate processing.
        """
        if not responded_attempt.decision_id:
            return
        
        try:
            sister_attempts = db.query(FollowUpAttempt).filter(
                FollowUpAttempt.decision_id == responded_attempt.decision_id,
                FollowUpAttempt.attempt_id != responded_attempt.attempt_id,
                FollowUpAttempt.status.in_(["PENDING", "AWAITING_RESPONSE"])
            ).all()
            
            for sister in sister_attempts:
                sister.status = "SUPERSEDED"
                sister.response_status = "SUPERSEDED"
                sister.stop_reason = f"Response received via {responded_attempt.channel}"
                logger.info(f"   🔇 Cancelled {sister.channel} attempt {sister.attempt_id} (superseded by {responded_attempt.channel})")
            
            if sister_attempts:
                db.commit()
                logger.info(f"✅ Cancelled {len(sister_attempts)} sister attempts for decision {responded_attempt.decision_id}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to cancel sister attempts: {e}")
