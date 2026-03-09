# SmartFU — Complete Data Flows

---

## Overview
This document traces every major data flow in SmartFU from start to finish, showing exactly which services, models, and APIs are involved at each step.

---

## Flow 1: CIOMS Upload → Case Creation → Dashboard

```
User uploads CIOMS PDF
│
├── Frontend: Dashboard.jsx → handleUpload()
│   └── POST /api/cases/upload-cioms
│       └── FormData: { file: cioms.pdf }
│
├── Backend: cases.py → upload_cioms()
│   ├── 1. Store PDF as CaseDocument (type=CIOMS)
│   ├── 2. Extract text from PDF (PyMuPDF)
│   ├── 3. Call Mistral LLM to parse CIOMS fields
│   │   └── Prompt: "Extract these 26 fields from the CIOMS form..."
│   │   └── Model: mistral-large-latest
│   ├── 4. Create AECase record with extracted fields
│   │   └── 35+ columns populated (drug_name, event_type, etc.)
│   ├── 5. Run DataCompletenessService
│   │   └── Create MissingField records for empty fields
│   ├── 6. Log PVAuditTrail: CASE_CREATED + CIOMS_PARSED + FIELDS_EXTRACTED
│   └── 7. Return { case_id, fields_extracted, completeness_score }
│
├── Frontend receives case_id
│   └── Navigates to /cases/{case_id}
│
└── Dashboard auto-refreshes
    └── GET /api/cases → updated case list with new case
```

### Fields Extracted (26)

| Field | Source in CIOMS | DB Column |
|---|---|---|
| Patient initials | Section 1 | `patient_initials` |
| Age | Section 1 | `patient_age` |
| Sex | Section 1 | `patient_sex` |
| Weight | Section 1 | `patient_weight` |
| Height | Section 1 | `patient_height` |
| Drug name | Section 4 | `drug_name` |
| Drug dose | Section 4 | `drug_dose` |
| Drug route | Section 4 | `drug_route` |
| Drug indication | Section 4 | `drug_indication` |
| Drug start date | Section 4 | `drug_start_date` |
| Drug end date | Section 4 | `drug_end_date` |
| Event type | Section 5 | `event_type` |
| Event onset date | Section 5 | `event_onset_date` |
| Event outcome | Section 5 | `event_outcome` |
| Seriousness criteria | Section 6 | `seriousness_criteria` |
| Reporter name | Section 12 | `reporter_name` |
| Reporter email | Section 12 | `reporter_email` |
| Reporter phone | Section 12 | `reporter_phone` |
| Reporter type | Section 12 | `reporter_type` |
| Country | Section 12 | `country` |
| Medical history | Section 8 | `medical_history` |
| Concomitant drugs | Section 9 | `concomitant_drugs` |
| Dechallenge | Section 7 | `dechallenge` |
| Rechallenge | Section 7 | `rechallenge` |
| Lab results | Section 10 | `lab_results` |
| Narrative | Section 11 | `narrative` |

---

## Flow 2: CSV Bulk Upload

```
User uploads data.csv with multiple cases
│
├── Frontend: Dashboard.jsx → handleCSVUpload()
│   └── POST /api/cases/upload-csv
│       └── FormData: { file: data.csv }
│
├── Backend: cases.py → upload_csv()
│   ├── For each row in CSV:
│   │   ├── 1. Map CSV columns to AECase fields
│   │   ├── 2. Create AECase record
│   │   ├── 3. Run DataCompletenessService
│   │   ├── 4. Log PVAuditTrail: CASE_CREATED
│   │   └── 5. Run initial risk assessment (optional)
│   └── Return { cases_created: N, errors: [...] }
│
└── Dashboard refreshes with N new cases
```

---

## Flow 3: Reviewer Workflow → Analysis → Send

This is the **core workflow** that most judges should see in a demo:

```
Step 1: Reviewer Opens Case
│
├── Frontend: CaseAnalysis.jsx
│   └── GET /api/cases/by-primaryid/{primary_id}
│       └── Returns: case data, missing fields, documents, analysis history
│
Step 2: Reviewer Adds Questions + Notes
│
├── Frontend: Right panel → reviewer notes textarea
│   └── User types: "[REVIEWER_QUESTION] Was a liver function test performed?"
│   └── POST /api/cases/{case_id}/reviewer-notes
│       └── Body: { notes: "..." }
│       └── Audit: REVIEWER_NOTE_ADDED
│
Step 3: Reviewer Attaches Repo Documents
│
├── Frontend: Repository Documents section
│   └── GET /api/repo-documents → list available TAFU/pregnancy forms
│   └── User selects relevant forms
│   └── POST /api/cases/{case_id}/attach-repo-docs
│       └── Body: { repo_doc_ids: [1, 3, 7] }
│
Step 4: Reviewer Clicks "Analyze & Send"
│
├── Frontend: Triggers analyze-and-send
│   └── POST /api/cases/by-primaryid/{primary_id}/analyze-and-send
│       └── Body: { repo_doc_ids: [1,3,7], reviewer_notes: "...", language: "en" }
│
├── Backend Pipeline (cases.py → analyze_and_send()):
│   │
│   ├── 4a. Parse reviewer questions from notes
│   │   └── Extract text after [REVIEWER_QUESTION] tags
│   │   └── Each becomes source: "REVIEWER_QUESTION" (priority 0)
│   │
│   ├── 4b. Run TFU Decision Agent (tfu_rules.py)
│   │   ├── _decide_tfu_required() → True
│   │   ├── _collect_candidates() → regulatory questions
│   │   └── Each becomes source: "TFU_MANDATORY" (priority 1)
│   │
│   ├── 4c. Load repo document questions
│   │   ├── Query repo_documents table for attached IDs
│   │   ├── Extract questions (doc.extracted_questions)
│   │   ├── Filter via repo_question_filter.py (Mistral AI)
│   │   └── Each becomes source: "REPO_FORM" (priority 2)
│   │
│   ├── 4d. Run 7-Agent LangGraph Pipeline
│   │   ├── Agent 1: Data Completeness → missing_fields
│   │   ├── Agent 2: Medical Reasoning → seriousness_hint
│   │   ├── Agent 3: Risk Assessment → risk_score, risk_category
│   │   ├── Agent 4: Response Strategy → response_probability
│   │   ├── Agent 5: Escalation → decision
│   │   ├── Agent 6: Question Generation → AI questions
│   │   ├── Agent 7: Follow-Up Orchestration → channel
│   │   ├── Finalizer: Confidence aggregation
│   │   └── Each question becomes source: "AI_GENERATED" (priority 3)
│   │
│   ├── 4e. MERGE all 4 sources through apply_tfu_gate()
│   │   ├── Combine all questions
│   │   ├── Semantic deduplication (cosine > 0.8)
│   │   ├── Sort by source priority, then score
│   │   └── Enforce ABSOLUTE_MAX_QUESTIONS = 5
│   │
│   ├── 4f. Build ExplainabilityBuilder output
│   │   └── Decision explanation + regulatory checkpoints
│   │
│   ├── 4g. Store results
│   │   ├── Create FollowUpDecision record
│   │   ├── Update AECase (risk_score, analysis_status)
│   │   ├── Log PVAuditTrail: AI_RISK_DECISION + AI_FOLLOWUP_DECISION
│   │   └── Store CaseConfidenceHistory
│   │
│   └── 4h. Send via selected channel
│       ├── CommunicationService.send()
│       ├── Channel based on Agent 7 output
│       └── Log PVAuditTrail: FOLLOWUP_SENT
│
Step 5: Frontend updates
│
├── CaseAnalysis.jsx receives analysis result
│   ├── Overview tab: risk score, seriousness, confidence
│   ├── Decision tab: AI decision explanation
│   ├── Questions tab: 4-panel display (blue/amber/indigo/purple)
│   ├── Oversight tab: governance level + override option
│   └── Right panel: completeness ring, risk ring, lifecycle stepper
│
└── Dashboard: Case status updated to "Analyzed"
```

---

## Flow 4: Phone IVR Follow-Up

```
System decides to call reporter (Agent 7: channel = PHONE)
│
├── Backend: CommunicationService.send_phone_followup()
│   └── Twilio REST API → Create outbound call
│       └── to: reporter_phone, from: TWILIO_PHONE_NUMBER
│       └── url: /api/twilio/voice-twiml?case_id={id}
│
├── Twilio connects call, hits webhook:
│   └── POST /api/twilio/voice-twiml
│       └── Returns TwiML XML with questions
│
├── Call flow:
│   ├── <Say> Introduction + case reference
│   ├── For each question (1-5):
│   │   ├── <Say> "Question N: {text}"
│   │   ├── <Gather input="speech dtmf" timeout="10">
│   │   └── Reporter speaks answer or presses keys
│   ├── <Say> "Thank you for your responses"
│   └── <Hangup/>
│
├── Each response triggers webhook:
│   └── POST /api/twilio/voice-response
│       ├── Capture speech transcription / DTMF digits
│       └── Process via ResponseProcessor
│
├── ResponseProcessor.process_response()
│   ├── Parse answer text (Mistral AI NLP)
│   ├── Map to target field (e.g., "January 15" → event_onset_date)
│   ├── Update AECase field
│   ├── Create FieldUpdateHistory record
│   ├── Log PVAuditTrail: RESPONSE_RECEIVED
│   └── Recalculate completeness score
│
└── If completeness ≥ 0.85 → lifecycle → COMPLETED
    Else → schedule next follow-up round
```

---

## Flow 5: Reporter Portal Response

```
Reporter clicks portal link in email
│
├── URL: https://smartfu.com/followup/{jwt_token}
│   └── Frontend: FollowUpAgent.jsx
│       └── GET /api/followup/validate/{token}
│           └── Validates JWT, returns case info + questions
│
├── Reporter answers questions one-by-one
│   ├── Conversational UI (one question at a time)
│   ├── Text input + optional file upload
│   ├── Auto-saves each answer
│   └── Progress bar updates
│
├── Reporter submits all answers
│   └── POST /api/followup/submit
│       └── Body: { token, responses: [{question_id, answer}...] }
│
├── Backend: process_portal_responses()
│   ├── For each answer:
│   │   ├── ResponseProcessor.process_response()
│   │   ├── Map answer → case field
│   │   ├── Update AECase
│   │   ├── Create FieldUpdateHistory
│   │   └── Log audit trail
│   ├── Update lifecycle attempt: status = RESPONDED
│   └── Recalculate completeness
│
└── Frontend: "Thank you" confirmation page
```

---

## Flow 6: WhatsApp Conversational Follow-Up

```
System sends WhatsApp message
│
├── Backend: CommunicationService.send_whatsapp_followup()
│   └── Twilio WhatsApp API → send message
│       └── to: whatsapp:+{phone}, from: whatsapp:+{twilio_number}
│       └── body: "Hello, this is SmartFU Safety. We need to follow up
│                  on case {primary_id}. I'll ask {n} questions."
│
├── Store conversation state in Redis
│   └── Key: whatsapp:{phone}:{case_id}
│   └── Value: { current_question_index: 0, questions: [...] }
│   └── TTL: 24 hours
│
├── Send first question
│   └── "Question 1: {text}"
│
├── Reporter replies via WhatsApp
│   └── Twilio webhook: POST /api/twilio/whatsapp-webhook
│       ├── Match to active conversation (Redis lookup)
│       ├── Process response via ResponseProcessor
│       ├── Increment current_question_index
│       └── Send next question (or thank you if done)
│
├── Repeat until all questions answered or conversation expires
│
└── Final: Update lifecycle, log audit trail
```

---

## Flow 7: Signal Detection

```
Background job / manual trigger
│
├── POST /api/signals/detect
│
├── SignalService.detect_signals()
│   ├── 1. Query all cases grouped by (drug_name, event_type)
│   │   └── SELECT drug_name, event_type, COUNT(*) FROM ae_cases
│   │       GROUP BY drug_name, event_type HAVING COUNT(*) >= 2
│   │
│   ├── 2. For each drug-event pair:
│   │   ├── Calculate 2×2 contingency table (a, b, c, d)
│   │   ├── Compute PRR = (a/(a+b)) / (c/(c+d))
│   │   ├── Classify: STRONG/MODERATE/WEAK/NONE
│   │   ├── Calculate trend (7-day window comparison)
│   │   └── Determine risk priority
│   │
│   ├── 3. Create/update SafetySignal records
│   │   └── Upsert into safety_signals table
│   │
│   ├── 4. Log PVAuditTrail: SIGNAL_DETECTED (for new signals)
│   │
│   └── 5. Return { new_signals: N, updated_signals: M }
│
├── Dashboard Signals panel updates
│   └── GET /api/signals → list of active signals
│
└── Safety Officer reviews on Signals.jsx page
```

---

## Flow 8: Lifecycle State Machine

```
Case completeness check triggers state evaluation
│
├── LifecycleTracker._determine_next_action()
│
├── State: INITIATED
│   └── First follow-up sent → ACTIVE
│
├── State: ACTIVE
│   ├── Response received + completeness ≥ 0.85 → COMPLETED
│   ├── Response received + completeness < 0.85 → stay ACTIVE (send next round)
│   ├── No response + attempts < escalate_after → stay ACTIVE (retry)
│   ├── No response + attempts ≥ escalate_after → STALLED
│   └── Deadline passed + no response → STALLED
│
├── State: STALLED
│   ├── Escalation triggered → ESCALATED
│   └── Log: LIFECYCLE_STAGE_CHANGE (ACTIVE → STALLED)
│
├── State: ESCALATED
│   ├── Response received → ACTIVE (re-enter loop)
│   ├── Max attempts + Non-HCP + auto_dead_letter → DEAD_LETTER
│   └── Max attempts + HCP → stays ESCALATED (manual review required)
│
├── State: COMPLETED
│   └── Terminal state — case has sufficient data
│
└── State: DEAD_LETTER
    └── Terminal state — all attempts exhausted
```

---

## Flow 9: Authentication & Authorization

```
Login Flow:
│
├── Frontend: Login.jsx → handleSubmit()
│   └── POST /api/auth/login
│       └── Body: { email, password }
│
├── Backend: auth.py → login()
│   ├── Lookup user by email
│   ├── Verify password (Argon2 hash)
│   ├── Generate JWT tokens:
│   │   ├── Access token (HS256, 60min expiry)
│   │   └── Refresh token (HS256, 7day expiry)
│   └── Return { access_token, refresh_token, user_info }
│
├── Frontend: Store tokens in localStorage
│   └── api.setAuthToken(access_token)
│
├── Subsequent API calls:
│   └── Authorization: Bearer {access_token}
│
├── Token refresh:
│   └── POST /api/auth/refresh
│       └── Body: { refresh_token }
│       └── Returns: { access_token (new) }
│
└── Role-based access:
    ├── PV_SPECIALIST: Can view/analyze cases
    ├── SAFETY_OFFICER: Can review signals, override decisions
    └── ADMIN: Full access including user management
```

---

## Flow 10: Human Override

```
AI Decision: SKIP (don't follow up)
Review Level: MANDATORY (risk ≥ 0.8)
│
├── Frontend: Oversight tab shows MANDATORY review
│   └── User clicks "Override → PROCEED"
│   └── Enters reason: "Reporter is specialist, can provide critical data"
│
├── POST /api/cases/{case_id}/override
│   └── Body: {
│       original_decision: "SKIP",
│       new_decision: "PROCEED",
│       reason: "Reporter is specialist..."
│   }
│
├── Backend: cases.py → override_decision()
│   ├── 1. Validate user role (SAFETY_OFFICER or ADMIN)
│   ├── 2. Update case decision to PROCEED
│   ├── 3. Log PVAuditTrail: HUMAN_OVERRIDE
│   │   └── previous_value: {decision: "SKIP"}
│   │   └── new_value: {decision: "PROCEED"}
│   │   └── actor_type: HUMAN, actor_id: user.id
│   └── 4. Re-trigger follow-up pipeline
│
└── Case proceeds with human-authorized decision
```

---

## Summary: Complete System Data Flow

```
CIOMS PDF / CSV → Case Creation → Dashboard
         │
         ▼
    Reviewer Review
    ├── Add questions
    ├── Add notes  
    ├── Attach repo docs
    └── Click "Analyze & Send"
         │
         ▼
    4-Source Question Merge
    ├── Reviewer (priority 0)
    ├── TFU Regulatory (priority 1)
    ├── Repo Forms (priority 2)
    └── AI Pipeline (priority 3)
         │
         ▼
    TFU Gate: Max 5 questions
         │
         ▼
    Send via Channel (Email / Phone / WhatsApp / Portal)
         │
         ▼
    Reporter Responds
         │
         ▼
    Response Processor → Update Case Fields
         │
         ▼
    Lifecycle Check
    ├── Completeness ≥ 0.85? → COMPLETED
    ├── More rounds needed? → Follow up again
    ├── No response? → Escalate
    └── Max attempts? → Dead Letter (Non-HCP) / Manual (HCP)
         │
         ▼
    Signal Detection → PRR Calculation → Dashboard Alerts
         │
         ▼
    Audit Trail: Every step permanently logged
```

---

*See JUDGE_PRESENTATION_GUIDE.md for how to present this in a live demo.*
