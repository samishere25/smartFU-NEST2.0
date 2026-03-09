# Feature 4: Multi-Channel Communication

---

## Overview
SmartFU delivers follow-up questions to reporters through **4 channels**: Email, Phone (IVR), WhatsApp, and a web-based Reporter Portal. The system intelligently selects channels based on case risk, reporter type, and engagement prediction from the AI pipeline.

---

## 4.1 Architecture

```
┌──────────────────────────────────────────────────────────┐
│                  CommunicationService                     │
│         backend/app/services/communication_service.py     │
│                       (645 lines)                         │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  ┌────────┐  ┌────────┐  ┌──────────┐  ┌──────────────┐ │
│  │ EMAIL  │  │ PHONE  │  │ WHATSAPP │  │   REPORTER   │ │
│  │ SMTP   │  │ Twilio │  │  Twilio  │  │    PORTAL    │ │
│  │ TLS    │  │ Voice  │  │ Sandbox  │  │  React SPA   │ │
│  └────────┘  └────────┘  └──────────┘  └──────────────┘ │
│       │           │            │               │          │
│       ▼           ▼            ▼               ▼          │
│   smtplib    TwiML/REST    REST API      JWT Token URL   │
└──────────────────────────────────────────────────────────┘
```

---

## 4.2 Channel Selection Logic

From Agent 7 (Follow-Up Orchestration) and lifecycle policies:

| Risk Level | Follow-Up Priority | Recommended Channel | Reason |
|---|---|---|---|
| HIGH | CRITICAL | **PHONE** | Immediate voice contact required for serious AEs |
| HIGH | HIGH | **PHONE** or **EMAIL** | Depends on reporter preference |
| MEDIUM | HIGH | **EMAIL** | Standard professional follow-up |
| MEDIUM | MEDIUM | **EMAIL** or **WHATSAPP** | Reporter's preferred channel |
| LOW | LOW | **EMAIL** | Routine follow-up |
| Any | Any | **REPORTER PORTAL** | Always available as supplement |

---

## 4.3 Channel 1: Email (SMTP)

### Configuration
```python
# From backend/app/config/config.py
SMTP_HOST: str = "smtp.gmail.com"
SMTP_PORT: int = 587
SMTP_USER: str       # From environment variable
SMTP_PASSWORD: str   # From environment variable (App Password)
FROM_EMAIL: str      # Sender address
```

### Email Pipeline
```
1. Compose HTML email
   ├── Company branding + header
   ├── Case reference (Primary ID)
   ├── Numbered questions (from 4-source merge)
   ├── Secure portal link (JWT-encoded URL)
   ├── Regulatory disclaimer
   └── Reply instructions

2. Attach PDF
   ├── CIOMS form copy (if applicable)
   └── Follow-up questionnaire

3. Send via SMTP
   ├── TLS encryption (port 587)
   ├── MIME multipart/alternative
   └── Retry on failure

4. Log in audit trail
   ├── FOLLOWUP_SENT action
   ├── Channel: EMAIL
   └── Timestamp + recipient
```

### Key Code
```python
async def send_email_followup(
    self, 
    case: AECase, 
    questions: List[Dict],
    recipient_email: str,
    language: str = "en"
) -> Dict:
    """Send HTML email with questions + portal link"""
```

---

## 4.4 Channel 2: Phone IVR (Twilio Voice)

### Configuration
```python
TWILIO_ACCOUNT_SID: str    # Twilio account
TWILIO_AUTH_TOKEN: str      # Twilio auth
TWILIO_PHONE_NUMBER: str   # Twilio phone number (caller ID)
TWILIO_TWIML_URL: str      # Webhook URL for TwiML responses
```

### Phone Call Pipeline
```
1. Initiate outbound call
   ├── Twilio REST API → create call
   ├── Sets callback URL → TwiML webhook endpoint
   └── Caller ID: TWILIO_PHONE_NUMBER

2. TwiML Webhook handles call flow:
   ├── POST /api/twilio/voice-twiml
   │
   ├── <Say> "Hello, this is SmartFU Safety calling regarding 
   │         case {primary_id}. We need to ask follow-up 
   │         questions about a reported adverse event."
   │
   ├── For each question:
   │   ├── <Say> "Question {n}: {question_text}"
   │   ├── <Gather input="speech dtmf" timeout="10">
   │   │   └── Records spoken or DTMF response
   │   └── Webhook captures response
   │
   ├── <Say> "Thank you for your responses."
   └── <Hangup/>

3. Response Processing
   ├── Twilio sends recording URL
   ├── Speech-to-text transcription
   ├── ResponseProcessor maps answers to fields
   └── Audit trail logged
```

### Twilio Webhooks

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/twilio/voice-twiml` | POST | Handle call flow with TwiML |
| `/api/twilio/voice-status` | POST | Call status callbacks |
| `/api/twilio/voice-response` | POST | Process DTMF/speech responses |
| `/api/twilio/voice-recording` | POST | Handle recording completion |

### TwiML Response Format
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">
        Hello, this is SmartFU Safety calling regarding 
        case ABC-2024-001.
    </Say>
    <Gather input="speech dtmf" timeout="10" 
            action="/api/twilio/voice-response">
        <Say>Question 1: What was the date of onset 
             of the adverse event?</Say>
    </Gather>
</Response>
```

---

## 4.5 Channel 3: WhatsApp (Twilio)

### Configuration
```python
TWILIO_WHATSAPP_NUMBER: str  # WhatsApp sandbox number
# Format: "whatsapp:+14155238886" (Twilio sandbox)
```

### WhatsApp Pipeline
```
1. Send initial message
   ├── Twilio WhatsApp API
   ├── Introduction + case reference
   └── "We'll ask {n} questions one at a time"

2. Conversational flow
   ├── Send Question 1
   ├── Wait for reply (webhook)
   ├── Process reply → send Question 2
   ├── ... repeat ...
   └── Send "Thank you" confirmation

3. Webhook Processing
   ├── POST /api/twilio/whatsapp-webhook
   ├── Match incoming message to active conversation
   ├── Store response via ResponseProcessor
   └── Send next question or close conversation
```

### WhatsApp Webhooks

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/twilio/whatsapp-webhook` | POST | Receive incoming WhatsApp messages |
| `/api/twilio/whatsapp-status` | POST | Message delivery status |

### Conversational State Tracking
```python
# Redis stores conversation state
conversation_key = f"whatsapp:{phone_number}:{case_id}"
state = {
    "current_question_index": 2,
    "total_questions": 5,
    "questions": [...],
    "responses": [...],
    "started_at": "2024-01-15T10:30:00Z"
}
# TTL: 24 hours (conversation expires after 24h)
```

---

## 4.6 Channel 4: Reporter Portal (Web)

### Architecture
```
Frontend: React SPA
├── Route: /followup/:token
├── Component: FollowUpAgent.jsx
├── NO LOGIN REQUIRED (secure token = authentication)
└── Multi-language support via TranslationService

Backend: FastAPI
├── POST /api/followup/generate-link → JWT token
├── GET /api/followup/validate/:token → case info
├── POST /api/followup/submit → process responses
└── JWT contains: case_id, reporter_email, expiry
```

### Portal Features

| Feature | Details |
|---|---|
| **Authentication** | JWT token in URL — no login needed |
| **Token Expiry** | Configurable (default: 72 hours) |
| **Multi-Language** | TranslationService adapts question language |
| **Conversational UI** | Questions shown one-by-one, with progress indicator |
| **File Upload** | Reporter can attach supporting documents |
| **Auto-Save** | Responses saved as entered (no data loss) |
| **Mobile-Friendly** | Responsive Tailwind design |
| **Confirmation** | Thank you page with reference number |

### JWT Token Structure
```json
{
    "case_id": 42,
    "reporter_email": "dr.smith@hospital.com",
    "exp": 1705363200,
    "iat": 1705104000,
    "type": "followup_portal"
}
```

### Portal User Flow
```
1. Reporter receives email/WhatsApp with portal link
   └── https://smartfu.com/followup/eyJhbGciOiJIUzI1...

2. Token validated → case info loaded
   └── Shows: drug name, event type, reporter name

3. Conversational question flow
   ├── Question 1 displayed with input field
   ├── Reporter types answer → "Next" button
   ├── Question 2 displayed...
   └── Progress bar updates

4. All answers submitted
   ├── ResponseProcessor processes answers
   ├── Fields updated in AECase
   ├── FieldUpdateHistory recorded
   └── Thank you page displayed
```

---

## 4.7 Response Processing (All Channels)

**File**: `backend/app/services/response_processor.py` (772 lines)

All channels feed into the same response processor:

```python
MAX_FOLLOW_UP_ATTEMPTS = 3  # After 3 unanswered rounds, escalate

async def process_response(
    case_id: int,
    question_id: str,
    answer_text: str,
    channel: str,          # EMAIL/PHONE/WHATSAPP/PORTAL
    reporter_info: Dict
) -> ProcessedResponse:
    """
    1. Parse answer text
    2. Map answer to case field (NLP)
    3. Validate answer format
    4. Update AECase field
    5. Record FieldUpdateHistory
    6. Recalculate completeness score
    7. Check if more follow-up needed
    8. Log in audit trail
    """
```

### Answer-to-Field Mapping
Uses Mistral AI to intelligently map free-text answers to database fields:

| Reporter Answer | Mapped Field | Mapped Value |
|---|---|---|
| "It started on January 15th" | `event_onset_date` | `2024-01-15` |
| "Patient recovered fully" | `event_outcome` | `recovered` |
| "Yes, we stopped the drug" | `dechallenge` | `yes` |
| "The patient is 67 years old" | `patient_age` | `67` |

---

## 4.8 Multi-Language Support

**TranslationService** supports generating questions and portal content in multiple languages:

| Language | Code | Status |
|---|---|---|
| English | en | Primary |
| Spanish | es | Supported |
| French | fr | Supported |
| German | de | Supported |
| Japanese | ja | Supported |
| Hindi | hi | Supported |

Translation is handled at the question level — the Mistral LLM generates questions directly in the target language (not translated after generation).

---

## 4.9 Communication Audit Trail

Every communication is logged:

```python
PVAuditTrail(
    case_id=case_id,
    action="FOLLOWUP_SENT",
    actor_type="SYSTEM",
    details={
        "channel": "PHONE",
        "recipient": "+1234567890",
        "questions_count": 5,
        "attempt_number": 2,
        "language": "en"
    },
    timestamp=datetime.utcnow()
)
```

---

## 4.10 How to Explain to Judges

> "We don't just send emails. Based on case risk and AI prediction, SmartFU automatically selects the best channel. For a life-threatening event with 3 days to deadline, it makes a phone call. For routine follow-up, it sends an email with a secure portal link. The reporter portal needs no login — it uses a JWT token in the URL — and the conversational interface asks questions one at a time, with multi-language support. All responses, regardless of channel, flow into the same processing pipeline that updates the case and triggers re-analysis."

---

*See F5_LIFECYCLE_MANAGEMENT.md for how the system tracks follow-up attempts across channels.*
