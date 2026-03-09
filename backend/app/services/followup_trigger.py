"""
Automated Follow-Up Trigger Service
Integrates with existing analysis pipeline to trigger REAL follow-ups.
Follows STRICT rules from user requirements.
"""

import logging
import uuid
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.case import AECase
from app.models.followup import FollowUpAttempt, FollowUpDecision
from app.services.followup_orchestration import FollowUpOrchestrator
from app.services.communication_service import get_communication_service
from app.services.audit_service import AuditService
from app.services.contact_resolver import ContactResolver
from app.core.config import settings

logger = logging.getLogger(__name__)


class FollowUpTrigger:
    """
    STEP 2: WHEN FOLLOW-UP SHOULD TRIGGER
    
    Follow-up must trigger ONLY AFTER: POST /cases/{case_id}/analyze
    
    Use existing analysis output fields:
    - decision
    - risk_score
    - response_probability
    - missing_fields
    - completeness_score
    
    DO NOT send follow-up if:
    - decision == "NO_FOLLOWUP"
    - completeness_score >= confidence_threshold
    """
    
    @staticmethod
    async def trigger_automated_followup(
        db: Session,
        case: AECase,
        analysis_result: Dict,
        questions: List[Dict],
        user_id: Optional[str] = None
    ) -> Dict:
        """
        Trigger automated follow-up after case analysis completes.
        
        MULTI-CHANNEL STRATEGY: Send follow-up via ALL available channels
        simultaneously (EMAIL + PHONE + WHATSAPP). First response from any
        channel wins. Each channel gets its own FollowUpAttempt row,
        linked by shared decision_id.
        
        Args:
            db: Database session
            case: AECase instance
            analysis_result: Output from smartfu_agent
            questions: Selected questions from Feature 3
            user_id: Optional user ID for audit
        
        Returns:
            Dict with follow-up status and communication results per channel
        """
        try:
            logger.info(f"\n{'='*80}")
            logger.info(f"🚀 FOLLOW-UP TRIGGER STARTED")
            logger.info(f"   Case ID: {case.case_id}")
            logger.info(f"   Primary ID: {case.primaryid}")
            logger.info(f"{'='*80}\n")
            
            # Extract analysis fields
            decision = analysis_result.get("decision", "MONITOR")
            risk_score = analysis_result.get("risk_score", 0.5)
            completeness_score = analysis_result.get("completeness_score", 0.0)
            stop_followup = analysis_result.get("stop_followup", False)
            response_probability = analysis_result.get("response_probability", 0.5)
            followup_required = analysis_result.get("followup_required", False)
            
            logger.info(f"📊 Analysis Results:")
            logger.info(f"   Decision: {decision}")
            logger.info(f"   Risk Score: {risk_score}")
            logger.info(f"   Completeness: {completeness_score}")
            logger.info(f"   Follow-up Required: {followup_required}")
            logger.info(f"   Stop Follow-up: {stop_followup}")
            
            # CRITICAL REQUIREMENT: Use AI-decided channel from analysis
            # DO NOT compute channel ourselves - respect AI decision
            ai_channel = analysis_result.get("followup_channel", None)
            logger.info(f"📡 AI Selected Channel: {ai_channel}")
            
            # If AI didn't require follow-up, skip
            if not followup_required:
                logger.info(f"⏭️ AI decided no follow-up needed for case {case.case_id}")
                return {
                    "followup_created": False,
                    "reason": "AI analysis determined follow-up not required",
                    "channel": None
                }
            
            # If no questions, skip
            if not questions or len(questions) == 0:
                logger.warning(f"⏭️ SKIPPING: No questions for case {case.case_id}")
                logger.info(f"   Reason: Question list is empty")
                logger.info("="*80)
                return {
                    "followup_created": False,
                    "reason": "No questions to ask",
                    "channel": None
                }
            
            logger.info(f"📝 Questions to ask: {len(questions)}")

            # DUPLICATE CHECK: Prevent duplicate calls if active attempts exist
            # Check for any PENDING or AWAITING_RESPONSE PHONE attempts for this case
            active_phone_attempts = db.query(FollowUpAttempt).filter(
                FollowUpAttempt.case_id == case.case_id,
                FollowUpAttempt.channel == "PHONE",
                FollowUpAttempt.status.in_(["PENDING", "SENT", "AWAITING_RESPONSE"])
            ).count()

            if active_phone_attempts > 0:
                logger.warning(f"⚠️ DUPLICATE CHECK: {active_phone_attempts} active PHONE attempt(s) already exist for case {case.case_id}")
                logger.info(f"   Expiring old attempts before creating new ones...")
                # Expire stale active attempts so fresh ones can be created
                stale_attempts = db.query(FollowUpAttempt).filter(
                    FollowUpAttempt.case_id == case.case_id,
                    FollowUpAttempt.status.in_(["PENDING", "SENT", "AWAITING_RESPONSE"])
                ).all()
                for stale in stale_attempts:
                    stale.status = "EXPIRED"
                    stale.stop_reason = "Superseded by new follow-up trigger"
                db.flush()
                logger.info(f"   ♻️ Expired {len(stale_attempts)} stale attempts")

            # ============================================================
            # MULTI-CHANNEL: Send via ALL available channels simultaneously
            # ============================================================
            ALL_CHANNELS = ["EMAIL", "PHONE", "WHATSAPP"]
            
            # Determine which channels are available based on config
            available_channels = []
            
            # EMAIL is always available if email settings exist
            if settings.EMAIL_FROM and settings.ENABLE_EMAIL_FOLLOWUPS:
                available_channels.append("EMAIL")
            
            # PHONE requires Twilio + ngrok (public URL for TwiML webhooks)
            if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_FROM_NUMBER:
                if not settings.ENABLE_SMS_FOLLOWUPS:
                    logger.info("📞 PHONE skipped: ENABLE_SMS_FOLLOWUPS=False")
                elif "localhost" in settings.BACKEND_URL or "127.0.0.1" in settings.BACKEND_URL:
                    logger.info("📞 PHONE skipped: BACKEND_URL is localhost (ngrok required for Twilio Voice webhooks)")
                else:
                    available_channels.append("PHONE")
            else:
                logger.info("📞 PHONE skipped: Twilio credentials not configured")
            
            # WHATSAPP requires Twilio + WhatsApp number + public URL for webhooks
            if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_WHATSAPP_NUMBER:
                if not settings.ENABLE_SMS_FOLLOWUPS:
                    logger.info("💬 WHATSAPP skipped: ENABLE_SMS_FOLLOWUPS=False")
                elif "localhost" in settings.BACKEND_URL or "127.0.0.1" in settings.BACKEND_URL:
                    logger.info("💬 WHATSAPP skipped: BACKEND_URL is localhost (ngrok required for WhatsApp webhooks)")
                else:
                    available_channels.append("WHATSAPP")
            else:
                logger.info("💬 WHATSAPP skipped: Twilio WhatsApp not configured")
            
            if not available_channels:
                logger.error(f"❌ No communication channels available!")
                return {
                    "followup_created": False,
                    "reason": "No communication channels configured",
                    "channel": None
                }
            
            logger.info(f"\n📡 MULTI-CHANNEL FOLLOW-UP:")
            logger.info(f"   Available channels: {available_channels}")
            logger.info(f"   Total channels: {len(available_channels)}")

            # Build decision reason
            decision_reason = f"{decision} - Risk: {risk_score:.2f}, Completeness: {completeness_score:.2f}"
            reason = f"Automated follow-up for {decision} decision"
            
            # STEP 4: Create ONE shared FollowUpDecision record
            followup_decision = FollowUpDecision(
                decision_id=uuid.uuid4(),
                case_id=case.case_id,
                decision_type="AUTO_TRIGGER",
                decision_reason=decision_reason,
                predicted_response_probability=response_probability,
                recommended_channel="MULTI",  # All channels
                case_risk_level=analysis_result.get("risk_level", "MEDIUM"),
                escalation_required=(decision == "ESCALATE"),
                created_at=datetime.utcnow()
            )
            db.add(followup_decision)
            db.commit()
            
            # Dynamic iteration_number: count existing ROUNDS (unique decision_ids)
            from sqlalchemy import func
            existing_rounds = db.query(func.count(func.distinct(FollowUpAttempt.decision_id))).filter(
                FollowUpAttempt.case_id == case.case_id,
                FollowUpAttempt.status.notin_(["EXPIRED", "FAILED"])
            ).scalar() or 0
            iteration_num = existing_rounds + 1
            is_re_followup = analysis_result.get("is_re_followup", False)
            
            logger.info(f"📊 Attempt tracking: round #{iteration_num} (re-followup={is_re_followup})")
            
            # STEP 5: Create ONE FollowUpAttempt PER CHANNEL (shared decision_id)
            channel_results = {}
            channel_attempts = {}
            
            for channel in available_channels:
                secure_token = str(uuid.uuid4())
                
                # Store questions + metadata in response_data
                response_data_payload = {"questions": questions}
                # Include PDF attachments if present (from combined_followup builder)
                if analysis_result.get("followup_attachments"):
                    response_data_payload["attachments"] = analysis_result["followup_attachments"]
                if is_re_followup:
                    response_data_payload["is_re_followup"] = True
                    response_data_payload["parent_attempt_id"] = analysis_result.get("parent_attempt_id")
                    response_data_payload["attempt_number"] = iteration_num
                
                followup_attempt = FollowUpAttempt(
                    attempt_id=uuid.uuid4(),
                    case_id=case.case_id,
                    decision_id=followup_decision.decision_id,  # SHARED across channels
                    iteration_number=iteration_num,
                    attempt_number=iteration_num,
                    channel=channel,
                    questions_sent=questions,
                    questions_count=len(questions),
                    response_data=response_data_payload,
                    decision="PROCEED",
                    reasoning=f"Multi-channel {'re-follow-up' if is_re_followup else 'follow-up'} round #{iteration_num} via {channel}",
                    secure_token=secure_token,
                    sent_at=datetime.utcnow(),
                    status="PENDING"
                )
                db.add(followup_attempt)
                channel_attempts[channel] = (followup_attempt, secure_token)
            
            db.commit()  # Commit all attempts at once
            
            # STEP 6: Send communication on ALL channels
            from app.services.contact_resolver import ContactResolver
            contact_info = ContactResolver.resolve_contact(case.primaryid)
            
            # FIX: Set sent_to on each attempt so webhook can find them by phone/email
            reporter_phone = contact_info.get('phone') if contact_info else None
            reporter_email = contact_info.get('email') if contact_info else None
            
            for channel in available_channels:
                followup_attempt, secure_token = channel_attempts[channel]
                
                # FIX: Set sent_to based on channel so webhook can match incoming messages
                if channel in ("PHONE", "WHATSAPP") and reporter_phone:
                    followup_attempt.sent_to = reporter_phone
                    followup_attempt.recipient_email = reporter_email  # Also store email for reference
                elif channel == "EMAIL" and reporter_email:
                    followup_attempt.sent_to = reporter_email
                    followup_attempt.recipient_email = reporter_email
                
                logger.info(f"\n{'📧' if channel == 'EMAIL' else '📞' if channel == 'PHONE' else '💬'} Sending {channel} follow-up...")
                
                try:
                    communication_result = await FollowUpTrigger._send_communication(
                        channel=channel,
                        case=case,
                        questions=questions,
                        secure_token=secure_token,
                        followup_attempt=followup_attempt,
                        language=analysis_result.get("followup_language", "en")
                    )
                    
                    channel_results[channel] = communication_result
                    
                    # Update attempt status based on result
                    if communication_result.get("success"):
                        followup_attempt.response_status = "SENT"
                        followup_attempt.status = "SENT"  # FIX: Use "SENT" to match webhook filter
                        followup_attempt.sent_method = channel
                        logger.info(f"   ✅ {channel} sent successfully (sent_to={followup_attempt.sent_to})")
                    else:
                        followup_attempt.response_status = "FAILED"
                        followup_attempt.status = "FAILED"
                        followup_attempt.stop_reason = communication_result.get("error", "Unknown error")
                        logger.warning(f"   ❌ {channel} failed: {communication_result.get('error')}")
                    
                except Exception as ch_error:
                    logger.error(f"   ❌ {channel} exception: {ch_error}")
                    followup_attempt.response_status = "FAILED"
                    followup_attempt.status = "FAILED"
                    followup_attempt.stop_reason = str(ch_error)
                    channel_results[channel] = {"success": False, "error": str(ch_error), "channel": channel}
            
            try:
                db.commit()
                
                # STEP 9: AUDIT & COMPLIANCE - Log follow-up action
                AuditService.log_followup_sent(
                    db=db,
                    case_id=case.case_id,
                    channel="MULTI:" + ",".join(available_channels),
                    question_count=len(questions),
                    user_id=user_id
                )
            except Exception as db_error:
                logger.error(f"⚠️ Database update failed (but communications were sent): {db_error}")
                db.rollback()
            
            # Build summary
            successful_channels = [ch for ch, r in channel_results.items() if r.get("success")]
            failed_channels = [ch for ch, r in channel_results.items() if not r.get("success")]
            
            logger.info(f"\n{'='*80}")
            logger.info(f"📊 MULTI-CHANNEL FOLLOW-UP SUMMARY")
            logger.info(f"   ✅ Sent: {successful_channels}")
            logger.info(f"   ❌ Failed: {failed_channels}")
            logger.info(f"   Decision ID: {followup_decision.decision_id}")
            logger.info(f"{'='*80}\n")
            
            return {
                "success": len(successful_channels) > 0,
                "followup_created": True,
                "channels": available_channels,
                "successful_channels": successful_channels,
                "failed_channels": failed_channels,
                "channel": "MULTI",  # Backward compat
                "decision_id": str(followup_decision.decision_id),
                "channel_results": channel_results,
                "questions_count": len(questions),
                "contact_info": contact_info,
                "message": f"Follow-up sent via {', '.join(successful_channels)}" if successful_channels else "All channels failed"
            }
            
        except Exception as e:
            logger.error(f"Follow-up trigger failed: {e}", exc_info=True)
            return {
                "followup_created": False,
                "error": str(e),
                "channel": None
            }
    
    @staticmethod
    def _select_channel_deterministic(
        decision: str,
        risk_score: float,
        response_probability: float,
        reporter_type: Optional[str]
    ) -> str:
        """
        STEP 3: CHANNEL SELECTION (DETERMINISTIC, NOT RANDOM)
        
        Implement ChannelSelector with STRICT rules:
        
        IF decision == "ESCALATE" OR risk_score >= 0.8
            → CHANNEL = PHONE_CALL (Twilio Voice)
        
        ELSE IF response_probability >= 0.6
            → CHANNEL = EMAIL
        
        ELSE
            → CHANNEL = WHATSAPP (Twilio WhatsApp)
        
        NO hardcoding. NO random choice. NO UI-based logic.
        """
        # Rule 1: Escalated cases or high risk → PHONE
        if decision == "ESCALATE" or risk_score >= 0.8:
            return "PHONE"
        
        # Rule 2: High response probability → EMAIL
        if response_probability >= 0.6:
            return "EMAIL"
        
        # Rule 3: Default → WHATSAPP
        return "WHATSAPP"
    
    @staticmethod
    async def _send_communication(
        channel: str,
        case: AECase,
        questions: List[Dict],
        secure_token: str,
        followup_attempt: FollowUpAttempt,
        language: str = "en"
    ) -> Dict:
        """
        Send actual communication via selected channel.
        
        Returns communication result with success status.
        """
        comm_service = get_communication_service()
        
        logger.info(f"\n🔍 RESOLVING CONTACT INFO:")
        logger.info(f"   Primary ID: {case.primaryid}")
        
        # Get reporter contact info from ContactResolver (simulates CRM integration)
        contact_info = ContactResolver.resolve_contact(case.primaryid)
        
        if not contact_info:
            logger.error(f"❌ FOLLOW-UP FAILED: No contact info for primaryid={case.primaryid}")
            logger.error(f"   Case ID: {case.case_id}")
            logger.error(f"   Channel was: {channel}")
            return {
                "success": False,
                "error": "No contact information available for this case",
                "channel": channel
            }
        
        reporter_email = contact_info.get('email')
        reporter_phone = contact_info.get('phone')
        
        logger.info(f"\n📬 CONTACT INFO RESOLVED:")
        logger.info(f"   Email: {reporter_email}")
        logger.info(f"   Phone: {reporter_phone}")
        logger.info(f"   Channel: {channel}")
        
        if channel == "PHONE":
            logger.info(f"\n📞 PHONE CALL FLOW:")
            logger.info(f"   To: {reporter_phone}")
            
            # PHONE CALL for HIGH/CRITICAL risk
            if not reporter_phone:
                logger.error(f"❌ PHONE FAILED: No phone number available")
                return {
                    "success": False,
                    "error": "No phone number available",
                    "channel": "PHONE"
                }
            
            logger.info(f"   Questions to ask: {len(questions)}")
            logger.info(f"   🚀 Calling Twilio send_phone_call...")
            
            result = comm_service.send_phone_call(
                to_number=reporter_phone,
                attempt_id=str(followup_attempt.attempt_id),
                questions=questions
            )
            
            logger.info(f"{'✅' if result.get('success') else '❌'} PHONE CALL {'INITIATED' if result.get('success') else 'FAILED'}")
            if result.get("success"):
                logger.info(f"   Call SID: {result.get('call_sid')}")
            else:
                logger.error(f"   Error: {result.get('error')}")
            
            return result
        
        elif channel == "WHATSAPP":
            logger.info(f"\n📱 WHATSAPP FLOW:")
            logger.info(f"   To: {reporter_phone}")
            
            # WHATSAPP for MEDIUM risk or phone fallback
            if not reporter_phone:
                logger.error(f"❌ WHATSAPP FAILED: No phone number available")
                return {
                    "success": False,
                    "error": "No phone number available",
                    "channel": "WHATSAPP"
                }
            
            logger.info(f"   Questions: {len(questions)}")
            logger.info(f"   🚀 Calling Twilio send_whatsapp_followup...")
            
            # Send first question via WhatsApp
            result = comm_service.send_whatsapp_followup(
                to_number=reporter_phone,
                attempt_id=str(followup_attempt.attempt_id),
                questions=questions
            )
            
            logger.info(f"{'✅' if result.get('success') else '❌'} WHATSAPP {'SENT' if result.get('success') else 'FAILED'}")
            if not result.get("success"):
                logger.error(f"   Error: {result.get('error')}")
            
            return result
        
        elif channel == "EMAIL":
            logger.info(f"\n📧 EMAIL FLOW:")
            logger.info(f"   To: {reporter_email}")
            logger.info(f"   Questions: {len(questions)}")
            logger.info(f"   Case ID: {case.case_id}")
            
            # STEP 6: EMAIL FLOW
            if not reporter_email:
                logger.error(f"❌ EMAIL FAILED: No email address available")
                return {
                    "success": False,
                    "error": "No email address available",
                    "channel": "EMAIL"
                }
            
            logger.info(f"   🚀 Calling SMTP send_email...")
            logger.info(f"   FROM: {settings.EMAIL_FROM}")
            logger.info(f"   TO: {reporter_email}")
            
            # Gather PDF attachments from the analysis result
            email_attachments = []
            if followup_attempt.response_data and isinstance(followup_attempt.response_data, dict):
                email_attachments = followup_attempt.response_data.get("attachments", [])
            
            result = comm_service.send_email(
                to_email=reporter_email,
                case_id=str(case.case_id),
                questions=questions,
                secure_token=secure_token,
                attachments=email_attachments,
                language=language
            )
            
            if result.get('success'):
                logger.info(f"✅ EMAIL SENT successfully")
                logger.info(f"   To: {result.get('to_email')}")
                logger.info(f"   Questions: {result.get('question_count')}")
            else:
                logger.error(f"❌ EMAIL FAILED: {result.get('error')}")
            logger.info("="*80)

            return result

        else:
            return {
                "success": False,
                "error": f"Unknown channel: {channel}",
                "channel": channel
            }
    
    @staticmethod
    def _get_highest_priority_question(questions: List[Dict]) -> Dict:
        """
        Get highest priority question for single-question channels (PHONE/WHATSAPP).
        
        Priority order: CRITICAL > HIGH > MEDIUM > LOW
        """
        priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        
        if not questions:
            return {}
        
        # Sort by criticality
        sorted_questions = sorted(
            questions,
            key=lambda q: priority_order.get(q.get('criticality', 'MEDIUM'), 2)
        )
        
        return sorted_questions[0] if sorted_questions else questions[0]
