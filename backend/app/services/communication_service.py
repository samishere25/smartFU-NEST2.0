"""
Communication Service - REAL automated follow-up via PHONE/EMAIL/WHATSAPP
Triggered after case analysis based on FollowUpOrchestrator rules.
NO mock data. REAL Twilio integration.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.config import settings

logger = logging.getLogger(__name__)


class CommunicationService:
    """
    Real communication service for automated follow-ups.
    Supports: PHONE (Twilio Voice), EMAIL, WHATSAPP (Twilio WhatsApp)
    """
    
    def __init__(self):
        self.twilio_client = None
        if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
            try:
                self.twilio_client = Client(
                    settings.TWILIO_ACCOUNT_SID,
                    settings.TWILIO_AUTH_TOKEN
                )
                logger.info("✅ Twilio client initialized")
            except Exception as e:
                logger.error(f"❌ Twilio initialization failed: {e}")
    
    def send_phone_call(
        self,
        to_number: str,
        attempt_id: str,
        questions: List[Dict],
        callback_url: Optional[str] = None
    ) -> Dict:
        """
        Initiate Twilio Voice call for HIGH risk cases
        Questions are already in FollowUpAttempt.context
        
        Flow:
        1. Make call to reporter
        2. TwiML speaks questions one by one
        3. Captures speech responses
        4. Webhook saves responses to AECase
        """
        if not self.twilio_client:
            logger.error("Twilio client not initialized")
            return {
                "success": False,
                "error": "Twilio not configured",
                "channel": "PHONE"
            }
        
        if not settings.ENABLE_SMS_FOLLOWUPS:
            logger.warning("Phone follow-ups disabled in settings")
            return {
                "success": False,
                "error": "Phone follow-ups disabled",
                "channel": "PHONE"
            }
        
        try:
            logger.info("=" * 80)
            logger.info(f"📞 INITIATING PHONE CALL")
            logger.info(f"   To: {to_number}")
            logger.info(f"   Attempt ID: {attempt_id}")
            logger.info(f"   Questions: {len(questions)}")
            logger.info("=" * 80)
            
            # TwiML URL that Twilio will call when call is answered
            twiml_url = f"{settings.BACKEND_URL}/api/voice/initiate?attempt_id={attempt_id}"
            
            call = self.twilio_client.calls.create(
                to=to_number,
                from_=settings.TWILIO_FROM_NUMBER,
                url=twiml_url,
                status_callback=callback_url,
                status_callback_event=['initiated', 'ringing', 'answered', 'completed'],
                timeout=60,  # Ring for 60 seconds before giving up
                record=True,  # Record for compliance
                recording_status_callback=f"{settings.BACKEND_URL}/api/voice/recording/{attempt_id}"
            )
            
            logger.info(f"✅ Phone call initiated: {call.sid}")
            logger.info(f"   Status: {call.status}")
            logger.info(f"   To: {to_number}")
            
            return {
                "success": True,
                "channel": "PHONE",
                "call_sid": call.sid,
                "to_number": to_number,
                "status": call.status,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except TwilioRestException as e:
            error_msg = str(e.msg) if hasattr(e, 'msg') else str(e)
            # Detect trial account limitations
            if "trial" in error_msg.lower() or "21219" in str(getattr(e, 'code', '')):
                logger.warning(f"⚠️ Twilio TRIAL account limitation: {error_msg}")
                logger.info("   Phone calls require a paid Twilio account or verified caller ID")
                return {
                    "success": False,
                    "error": "Phone skipped: Twilio trial account cannot call unverified numbers. Upgrade to paid account for phone follow-ups.",
                    "channel": "PHONE",
                    "trial_limitation": True
                }
            logger.error(f"❌ Twilio error: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "channel": "PHONE"
            }
        except Exception as e:
            logger.error(f"❌ Phone call failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "channel": "PHONE"
            }
    
    def send_whatsapp_message(
        self,
        to_number: str,
        message: str
    ) -> Dict:
        """
        Send a single WhatsApp message via Twilio
        Used for sending questions one at a time
        """
        if not self.twilio_client:
            logger.error("Twilio client not initialized")
            return {
                "success": False,
                "error": "Twilio not configured",
                "channel": "WHATSAPP"
            }
        
        try:
            # Ensure number has whatsapp: prefix
            if not to_number.startswith("whatsapp:"):
                to_number = f"whatsapp:{to_number}"
            
            # Use WhatsApp sandbox number for WhatsApp messages
            whatsapp_from = settings.TWILIO_WHATSAPP_NUMBER or settings.TWILIO_FROM_NUMBER
            from_number = f"whatsapp:{whatsapp_from}"
            
            message_obj = self.twilio_client.messages.create(
                body=message,
                from_=from_number,
                to=to_number
            )
            
            logger.info(f"📱 WhatsApp message sent: {message_obj.sid}")
            
            return {
                "success": True,
                "channel": "WHATSAPP",
                "message_sid": message_obj.sid,
                "to_number": to_number,
                "status": message_obj.status
            }
            
        except TwilioRestException as e:
            error_msg = str(e.msg) if hasattr(e, 'msg') else str(e)
            if "trial" in error_msg.lower() or "sandbox" in error_msg.lower():
                logger.warning(f"⚠️ Twilio trial/sandbox limitation for WhatsApp: {error_msg}")
                return {
                    "success": False,
                    "error": "WhatsApp skipped: Twilio sandbox/trial limitation. Reporter must join sandbox first.",
                    "channel": "WHATSAPP",
                    "trial_limitation": True
                }
            logger.error(f"❌ WhatsApp error: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "channel": "WHATSAPP"
            }
        except Exception as e:
            logger.error(f"❌ WhatsApp failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "channel": "WHATSAPP"
            }
    
    def send_whatsapp_followup(
        self,
        to_number: str,
        attempt_id: str,
        questions: List[Dict]
    ) -> Dict:
        """
        Send first WhatsApp question for MEDIUM risk cases
        Subsequent questions sent after each response via webhook
        """
        if not questions:
            logger.error("No questions to send")
            return {
                "success": False,
                "error": "No questions",
                "channel": "WHATSAPP"
            }
        
        logger.info("=" * 80)
        logger.info(f"📱 WHATSAPP FOLLOW-UP INITIATED")
        logger.info(f"   To: {to_number}")
        logger.info(f"   Attempt ID: {attempt_id}")
        logger.info(f"   Total Questions: {len(questions)}")
        logger.info("=" * 80)
        
        # Send first question only
        first_question = questions[0]
        question_text = first_question.get("question_text", "") or first_question.get("question", "")
        
        intro_message = (
            "Dear Healthcare Professional,\n\n"
            "This is the Pharmacovigilance Safety Team regarding adverse event case follow-up. "
            "We require additional information to complete our safety assessment.\n\n"
            f"*Question:* {question_text}\n\n"
            "Please reply with your answer. Thank you for your cooperation."
        )
        
        result = self.send_whatsapp_message(to_number, intro_message)
        
        if result["success"]:
            logger.info(f"✅ First WhatsApp question sent: {first_question.get('field')}")
        
        return result
    
    def send_email(
        self,
        to_email: str,
        case_id: str,
        questions: List[Dict],
        secure_token: str = None,
        language: str = "en",
        attachments: List[Dict] = None
    ) -> Dict:
        """
        STEP 6: EMAIL FLOW
        
        Email must:
        - include case reference
        - explain purpose of follow-up
        - show number of pending questions
        - contain secure token-based link
        
        On form submit:
        - update case
        - trigger re-analysis
        - possibly trigger next follow-up step
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"📧 EMAIL SEND ATTEMPT")
        logger.info(f"   To: {to_email}")
        logger.info(f"   Questions: {len(questions)}")
        logger.info(f"   Case ID: {case_id}")
        logger.info(f"\n🔧 SMTP CONFIGURATION CHECK:")
        logger.info(f"   ENABLE_EMAIL_FOLLOWUPS: {settings.ENABLE_EMAIL_FOLLOWUPS}")
        logger.info(f"   SMTP Host: {settings.SMTP_HOST or 'NOT SET'}")
        logger.info(f"   SMTP Port: {settings.SMTP_PORT}")
        logger.info(f"   SMTP Username: {settings.SMTP_USERNAME or 'NOT SET'}")
        logger.info(f"   SMTP Password: {'SET' if settings.SMTP_PASSWORD else 'NOT SET'}")
        logger.info(f"   SMTP TLS: {settings.SMTP_USE_TLS}")
        logger.info(f"   Email From: {settings.EMAIL_FROM or 'NOT SET'}")
        logger.info(f"{'='*80}\n")
        
        # CRITICAL: Validate SMTP configuration before attempting send
        if not settings.ENABLE_EMAIL_FOLLOWUPS:
            logger.error("❌ EMAIL BLOCKED: ENABLE_EMAIL_FOLLOWUPS is False")
            logger.error("   Set ENABLE_EMAIL_FOLLOWUPS=True in .env file")
            return {
                "success": False,
                "error": "Email follow-ups disabled in settings",
                "channel": "EMAIL"
            }
        
        if not settings.SMTP_HOST:
            logger.error("❌ EMAIL BLOCKED: SMTP_HOST not configured")
            logger.error("   Set SMTP_HOST in .env file (e.g., smtp.gmail.com)")
            return {
                "success": False,
                "error": "SMTP_HOST not configured",
                "channel": "EMAIL"
            }
        
        if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
            logger.error("❌ EMAIL BLOCKED: SMTP credentials not configured")
            logger.error("   Set SMTP_USERNAME and SMTP_PASSWORD in .env file")
            return {
                "success": False,
                "error": "SMTP credentials not configured",
                "channel": "EMAIL"
            }
        
        if not to_email:
            logger.error("❌ EMAIL BLOCKED: No recipient email address")
            return {
                "success": False,
                "error": "No recipient email address",
                "channel": "EMAIL"
            }
        
        if not questions or len(questions) == 0:
            logger.error("❌ EMAIL BLOCKED: No questions to send")
            return {
                "success": False,
                "error": "No questions to send",
                "channel": "EMAIL"
            }
        
        logger.info("✅ SMTP configuration validated - proceeding with email send")
        
        try:
            # Create secure follow-up link (NEW: Conversational Agent)
            followup_url = f"{settings.FRONTEND_URL}/followup-agent?token={secure_token}"
            
            # Build email content
            question_count = len(questions)
            critical_count = sum(1 for q in questions if q.get('criticality') == 'CRITICAL')
            
            # Detect re-follow-up (questions have is_re_followup flag from ResponseProcessor)
            is_re_followup = any(q.get('is_re_followup') for q in questions)
            re_ask_attempt = max((q.get('re_ask_attempt', 1) for q in questions), default=1) if is_re_followup else 1
            
            # Language-specific email content
            LANG_SUBJECTS = {
                "en": f"Important: Safety Follow-Up Required - Case {case_id[:8]}",
                "hi": f"महत्वपूर्ण: सुरक्षा अनुवर्ती आवश्यक - केस {case_id[:8]}",
                "es": f"Importante: Seguimiento de seguridad requerido - Caso {case_id[:8]}",
                "fr": f"Important: Suivi de sécurité requis - Dossier {case_id[:8]}",
                "de": f"Wichtig: Sicherheits-Nachverfolgung erforderlich - Fall {case_id[:8]}",
                "ja": f"重要: 安全性フォローアップが必要です - ケース {case_id[:8]}",
                "zh": f"重要: 需要安全随访 - 案例 {case_id[:8]}",
                "pt": f"Importante: Acompanhamento de segurança necessário - Caso {case_id[:8]}",
                "ar": f"مهم: متابعة السلامة مطلوبة - الحالة {case_id[:8]}",
            }
            
            if is_re_followup:
                subject = f"Reminder (Attempt #{re_ask_attempt}): {question_count} Remaining Question{'s' if question_count > 1 else ''} - Case {case_id[:8]}"
            else:
                subject = LANG_SUBJECTS.get(language, LANG_SUBJECTS["en"])
            
            # Re-follow-up gets a different intro paragraph
            if is_re_followup:
                intro_html = f"""
                    <div style="background-color: #fff3cd; border-left: 4px solid #ff9800; padding: 16px; margin: 20px 0; border-radius: 4px;">
                        <p style="margin: 0;"><strong>🔄 Follow-Up Reminder (Attempt #{re_ask_attempt})</strong></p>
                        <p style="margin: 8px 0 0 0;">Thank you for your previous responses! We still need {question_count} more piece{'s' if question_count > 1 else ''} of information for this safety report. This should only take 1-2 minutes.</p>
                    </div>
                """
            else:
                intro_html = f"""
                    <div style="background-color: #e3f2fd; border-left: 4px solid #2196f3; padding: 16px; margin: 20px 0; border-radius: 4px;">
                        <p style="margin: 0;"><strong>✨ Interactive Follow-Up Experience</strong></p>
                        <p style="margin: 8px 0 0 0;">We've made it easy! Answer a few quick questions in a conversational format. Your language preference will be the first thing we ask.</p>
                    </div>
                """
            
            # Build questions list HTML outside f-string (Python 3.9 doesn't allow backslashes in f-string expressions)
            # Sort questions: CRITICAL first, then HIGH, then by source (reviewer/repo before AI)
            priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
            source_order = {"REVIEWER_NOTE_AI": 0, "reviewer_note": 0, "REPO_FORM_AI_FILTERED": 1, "checklist": 1}
            sorted_questions = sorted(
                questions,
                key=lambda q: (
                    priority_order.get(q.get("criticality", "MEDIUM"), 2),
                    source_order.get(q.get("source", ""), 5),
                ),
            )
            questions_items = []
            for q in sorted_questions:
                q_text = q.get("question_text", q.get("question", q.get("field", "Question")))
                source = q.get("source", "")
                # Source badges
                source_badge = ""
                if source in ("REVIEWER_NOTE_AI", "reviewer_note"):
                    source_badge = ' <span style="color: #1565c0; font-size: 10px;">[Reviewer]</span>'
                elif source in ("REPO_FORM_AI_FILTERED",):
                    source_badge = ' <span style="color: #6a1b9a; font-size: 10px;">[Form]</span>'
                elif source == "checklist":
                    source_badge = ' <span style="color: #e65100; font-size: 10px;">[Checklist]</span>'
                critical_badge = ' <span style="color: #d32f2f; font-size: 11px;">⚠ CRITICAL</span>' if q.get("criticality") == "CRITICAL" else ""
                questions_items.append(f'<li style="margin-bottom: 8px; font-size: 14px;">{q_text}{critical_badge}{source_badge}</li>')
            questions_list_html = "".join(questions_items)
            overflow_html = ""
            
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
                    <h2 style="color: #d32f2f;">🏥 SmartFU - Patient Safety Follow-Up</h2>
                    
                    <p><strong>Case Reference:</strong> {case_id}</p>
                    
                    {intro_html}
                    
                    <div style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 12px; margin: 20px 0;">
                        <p style="margin: 0;"><strong>Why this follow-up is required:</strong></p>
                        <p style="margin: 8px 0 0 0;">Additional safety information is needed to properly assess this adverse event report. This is solely for patient safety and regulatory compliance.</p>
                    </div>
                    
                    <div style="background-color: #f5f5f5; padding: 15px; border-radius: 4px; margin: 20px 0;">
                        <p style="margin: 0;"><strong>Questions Pending:</strong> {question_count}</p>
                        <p style="margin: 8px 0 0 0;"><strong>Estimated Time:</strong> 2-5 minutes</p>
                        {f'<p style="margin: 8px 0 0 0; color: #d32f2f;"><strong>Critical Questions:</strong> {critical_count}</p>' if critical_count > 0 else ''}
                    </div>
                    
                    <div style="background-color: #fafafa; border: 1px solid #e0e0e0; border-radius: 4px; padding: 16px; margin: 20px 0;">
                        <p style="margin: 0 0 12px 0; font-weight: bold; color: #333;">📋 Questions to Answer:</p>
                        <ol style="margin: 0; padding-left: 20px; color: #555;">
                            {questions_list_html}
                        </ol>
                        {overflow_html}
                    </div>
                    
                    <p style="margin: 24px 0; text-align: center;">
                        <a href="{followup_url}" 
                           style="display: inline-block; background: linear-gradient(to right, #1976d2, #2196f3); color: white; padding: 14px 32px; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                            Start Interactive Follow-Up 🚀
                        </a>
                    </p>
                    
                    <div style="background-color: #e8f5e9; padding: 12px; border-radius: 4px; margin: 20px 0;">
                        <p style="margin: 0; font-size: 14px;"><strong>🌐 Multi-Language Support</strong></p>
                        <p style="margin: 8px 0 0 0; font-size: 13px;">English | हिंदी (Hindi) - Choose your preference when you start</p>
                    </div>
                    
                    <div style="border-top: 1px solid #ddd; padding-top: 16px; margin-top: 24px; font-size: 12px; color: #666;">
                        <p>🔒 Secure link expires in 72 hours</p>
                        <p>💬 Conversational experience - one question at a time</p>
                        <p>📜 All responses are confidential and audit-logged for compliance</p>
                        <p>⏱ Minimal data requested - only essential safety information</p>
                    </div>
                    
                    <p style="font-size: 12px; color: #999; margin-top: 20px;">
                        This is an automated safety follow-up from SmartFU Pharmacovigilance System.
                        Do not reply to this email. Use the secure link above to respond.
                    </p>
                </div>
            </body>
            </html>
            """
            
            # Send email using SMTP
            msg = MIMEMultipart('mixed')
            msg['Subject'] = subject
            msg['From'] = settings.EMAIL_FROM
            msg['To'] = to_email
            
            msg.attach(MIMEText(html_content, 'html'))
            
            # Attach PDF files if provided
            if attachments:
                import os
                from email.mime.application import MIMEApplication
                for att in attachments:
                    file_path = att.get("file_path", "")
                    file_name = att.get("file_name", "attachment.pdf")
                    if file_path and os.path.isfile(file_path):
                        try:
                            with open(file_path, "rb") as f:
                                pdf_part = MIMEApplication(f.read(), _subtype="pdf")
                                pdf_part.add_header(
                                    "Content-Disposition", "attachment",
                                    filename=file_name
                                )
                                msg.attach(pdf_part)
                                logger.info(f"📎 PDF attached to email: {file_name}")
                        except Exception as att_err:
                            logger.warning(f"⚠️ Failed to attach PDF {file_name}: {att_err}")
                    else:
                        logger.warning(f"⚠️ PDF file not found: {file_path}")
            
            logger.info(f"🔌 Connecting to SMTP server...")
            logger.info(f"   Host: {settings.SMTP_HOST}:{settings.SMTP_PORT}")
            
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as server:
                logger.info(f"✅ SMTP connection established")
                
                if settings.SMTP_USE_TLS:
                    logger.info(f"🔐 Starting TLS...")
                    server.starttls()
                    logger.info(f"✅ TLS started")
                
                logger.info(f"🔑 Logging in to SMTP server...")
                logger.info(f"   Username: {settings.SMTP_USERNAME}")
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                logger.info(f"✅ SMTP login successful")
                
                logger.info(f"📤 Sending email message...")
                logger.info(f"   From: {settings.EMAIL_FROM}")
                logger.info(f"   To: {to_email}")
                logger.info(f"   Subject: {subject}")
                server.send_message(msg)
                logger.info(f"✅ Email message sent successfully to {to_email}")
            
            logger.info(f"\n{'='*80}")
            logger.info(f"✅ EMAIL SEND COMPLETE")
            logger.info(f"   Recipient: {to_email}")
            logger.info(f"   Questions: {question_count} ({critical_count} critical)")
            logger.info(f"   Token: {secure_token[:16]}...")
            logger.info(f"{'='*80}\n")
            
            return {
                "success": True,
                "channel": "EMAIL",
                "to_email": to_email,
                "question_count": question_count,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"\n{'='*80}")
            logger.error(f"❌ SMTP AUTHENTICATION FAILED")
            logger.error(f"   Error: {e}")
            logger.error(f"   Username: {settings.SMTP_USERNAME}")
            logger.error(f"   Host: {settings.SMTP_HOST}")
            logger.error(f"   Check your SMTP_USERNAME and SMTP_PASSWORD in .env")
            logger.error(f"{'='*80}\n")
            return {
                "success": False,
                "error": f"SMTP Authentication Failed: {str(e)}",
                "channel": "EMAIL"
            }
        except smtplib.SMTPException as e:
            logger.error(f"\n{'='*80}")
            logger.error(f"❌ SMTP ERROR")
            logger.error(f"   Error: {e}")
            logger.error(f"   Type: {type(e).__name__}")
            logger.error(f"{'='*80}\n")
            return {
                "success": False,
                "error": f"SMTP Error: {str(e)}",
                "channel": "EMAIL"
            }
        except Exception as e:
            logger.error(f"\n{'='*80}")
            logger.error(f"❌ EMAIL SEND FAILED")
            logger.error(f"   Error: {e}")
            logger.error(f"   Type: {type(e).__name__}")
            logger.error(f"   To: {to_email}")
            logger.error(f"   Questions: {len(questions) if questions else 0}")
            logger.error(f"{'='*80}\n")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e),
                "channel": "EMAIL"
            }
    
    def send_whatsapp(
        self,
        to_number: str,
        case_id: str,
        question: Dict,
        language: str = "en",
        secure_token: str = None
    ) -> Dict:
        """
        STEP 7: WHATSAPP FLOW
        
        Use Twilio WhatsApp API with link to FollowUpAgent
        Rules:
        - Send link to /followup-agent?token=<secure_token>
        - User answers questions in browser
        - No multi-message conversation needed
        """
        if not self.twilio_client:
            logger.error("Twilio client not initialized")
            return {
                "success": False,
                "error": "Twilio not configured",
                "channel": "WHATSAPP"
            }
        
        if not settings.ENABLE_SMS_FOLLOWUPS:
            logger.warning("WhatsApp follow-ups disabled in settings")
            return {
                "success": False,
                "error": "WhatsApp follow-ups disabled",
                "channel": "WHATSAPP"
            }
        
        try:
            # Use Twilio WhatsApp (sandbox or production)
            to_whatsapp = f"whatsapp:{to_number}"
            from_whatsapp = f"whatsapp:{settings.TWILIO_WHATSAPP_NUMBER}"
            
            # Create secure follow-up link
            followup_url = f"{settings.FRONTEND_URL}/followup-agent?token={secure_token}"
            
            # PRODUCTION: Message with link to follow-up agent
            message_body = f"""👋 Hello, this is *SmartFU Safety Team* regarding your medication safety report.

📋 Case Reference: {case_id[:8]}

We need to ask you some important questions to ensure patient safety.

🔗 *Click here to start:*
{followup_url}

✨ Interactive experience - one question at a time
🌐 Multi-language support
⏱ Only 2-5 minutes

_Automated follow-up from SmartFU Pharmacovigilance Platform_"""
            
            message = self.twilio_client.messages.create(
                body=message_body,
                from_=from_whatsapp,
                to=to_whatsapp,
                status_callback=f"{settings.BACKEND_URL}/api/twilio/whatsapp/{case_id}"
            )
            
            logger.info(f"💬 WhatsApp sent via Sandbox: {message.sid} to {to_number}")
            
            return {
                "success": True,
                "channel": "WHATSAPP",
                "message_sid": message.sid,
                "to_number": to_number,
                "status": message.status,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except TwilioRestException as e:
            logger.error(f"Twilio WhatsApp error: {e.msg}")
            return {
                "success": False,
                "error": str(e.msg),
                "channel": "WHATSAPP"
            }
        except Exception as e:
            logger.error(f"WhatsApp send failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "channel": "WHATSAPP"
            }


# Singleton instance
_communication_service = None

def get_communication_service() -> CommunicationService:
    """Get or create communication service instance"""
    global _communication_service
    if _communication_service is None:
        _communication_service = CommunicationService()
    return _communication_service
