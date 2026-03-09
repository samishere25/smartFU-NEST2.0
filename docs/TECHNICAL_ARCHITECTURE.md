# SmartFU — Technical Architecture Deep Dive

---

## 1. SYSTEM ARCHITECTURE DIAGRAM

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React 18.2)                          │
│   Port 3000 · Vite 5.0 Dev Server · Tailwind CSS 3.4                  │
│                                                                         │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│   │Dashboard │ │Case List │ │CIOMS     │ │Case      │ │Reviewer  │   │
│   │(metrics) │ │(all AEs) │ │Upload    │ │Analysis  │ │Dashboard │   │
│   └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│   │Follow-Up │ │Follow-Up │ │Signals   │ │Lifecycle │ │Audit     │   │
│   │Attempts  │ │Agent     │ │Detection │ │Tracking  │ │Trail     │   │
│   └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐                              │
│   │Explain-  │ │Login     │ │PDF Test  │                              │
│   │ability   │ │(auth)    │ │          │                              │
│   └──────────┘ └──────────┘ └──────────┘                              │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                    REST API (JSON) + JWT Bearer Token
                    Vite Proxy: /api/* → localhost:8000
                                │
┌───────────────────────────────▼─────────────────────────────────────────┐
│                     FASTAPI BACKEND (Port 8000)                        │
│   Python 3.11 · Uvicorn 0.27 · SQLAlchemy 2.0 · Pydantic 2.5         │
│                                                                         │
│   ┌─── API LAYER (22 Route Groups, 80+ Endpoints) ──────────────────┐ │
│   │ /api/auth      → Register, Login, Profile                        │ │
│   │ /api/cases     → CRUD, Upload CSV/PDF, Analyze, Analyze-and-Send │ │
│   │ /api/followups → Questions, Submit, Decline, Override            │ │
│   │ /api/review    → Reviewer Dashboard endpoints                    │ │
│   │ /api/signals   → Evaluate, Active, Escalate, Review             │ │
│   │ /api/lifecycle  → Init, Send, Respond, Remind, Escalate, Dead   │ │
│   │ /api/audit     → PV Audit Trail, Stats, By Case/Signal          │ │
│   │ /api/governance → Oversight, Audit Log, Summary                  │ │
│   │ /api/analytics  → Dashboard Metrics                              │ │
│   │ /api/repo-documents → Upload, List, Questions, Delete            │ │
│   │ /api/voice     → Twilio Voice TwiML, Response, Recording        │ │
│   │ /api/whatsapp  → Webhook, Status                                │ │
│   │ /api/email     → Response Page, Process, Inbound Webhook        │ │
│   │ /api/regulatory → Start Workflow                                 │ │
│   │ /api/admin     → System Health                                   │ │
│   └──────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│   ┌─── AI LAYER ─────────────────────────────────────────────────────┐ │
│   │                                                                   │ │
│   │  ┌─────── 7-Agent Pipeline (graph.py, 1500 lines) ──────────┐  │ │
│   │  │                                                            │  │ │
│   │  │  SmartFUState (TypedDict) — shared graph state             │  │ │
│   │  │  40+ fields: case_data, risk_score, medical_reasoning,     │  │ │
│   │  │  engagement_risk, questions, decision, confidences...      │  │ │
│   │  │                                                            │  │ │
│   │  │  Agent 1: data_completeness_agent                          │  │ │
│   │  │    └─ DataCompletenessService                              │  │ │
│   │  │  Agent 2: medical_reasoning_agent                          │  │ │
│   │  │    └─ MedicalReasoningAgent (RAG: BioBERT + FAISS)        │  │ │
│   │  │  Agent 3: risk_assessment_agent                            │  │ │
│   │  │    └─ SemanticRiskEngine (SentenceTransformer)             │  │ │
│   │  │  Agent 4: response_strategy_agent                          │  │ │
│   │  │    └─ predict_response() + adapt_engagement_risk()        │  │ │
│   │  │  Agent 5: escalation_agent                                 │  │ │
│   │  │    └─ Mistral LLM reasoning + threshold logic             │  │ │
│   │  │  Agent 6: question_generation_agent                        │  │ │
│   │  │    └─ QuestionValueScorer (RL-enhanced)                   │  │ │
│   │  │  Agent 7: followup_orchestration_agent                     │  │ │
│   │  │    └─ FollowUpOrchestrator (channel + priority)           │  │ │
│   │  │  Agent 8: finalize_orchestration_output                    │  │ │
│   │  │    └─ Weighted confidence aggregation                     │  │ │
│   │  └────────────────────────────────────────────────────────────┘  │ │
│   │                                                                   │ │
│   │  ┌─── TFU Decision Agent (tfu_rules.py, 620 lines) ──────────┐ │ │
│   │  │  tfu_decision_agent() → _decide_tfu_required()             │ │ │
│   │  │  → _collect_candidates() → apply_tfu_gate()                │ │ │
│   │  │  ICH E2A seriousness · RMP risks · Special situations      │ │ │
│   │  │  ABSOLUTE_MAX_QUESTIONS = 5                                 │ │ │
│   │  └────────────────────────────────────────────────────────────┘ │ │
│   │                                                                   │ │
│   │  ┌─── UnifiedOrchestrator (Connected Flow) ──────────────────┐  │ │
│   │  │  Feature 1 (Risk+Medical) → Feature 2 (Strategy)          │  │ │
│   │  │  → Feature 3 (Adaptive Questioning)                        │  │ │
│   │  │  Safety guarantees: Cannot stop follow-up for HIGH risk    │  │ │
│   │  └────────────────────────────────────────────────────────────┘  │ │
│   └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│   ┌─── SERVICES LAYER (25+ Services) ───────────────────────────────┐ │
│   │ CommunicationService (645 lines) — Email/Phone/WhatsApp         │ │
│   │ ResponseProcessor (772 lines) — Answer→Field mapping + history  │ │
│   │ QuestionValueScorer (1022 lines) — RL scoring + Mistral text    │ │
│   │ CiomsExtractor — PDF extraction (regex + Mistral LLM)          │ │
│   │ RepoQuestionFilter (234 lines) — Mistral AI filtering          │ │
│   │ LifecycleTracker (904 lines) — State machine + policies        │ │
│   │ SignalService (251 lines) — PRR calculation + classification    │ │
│   │ ExplainabilityBuilder (400 lines) — Decision explanations      │ │
│   │ PVAuditService (441 lines) — Immutable audit trail             │ │
│   │ TranslationService — Multi-language via LLM                    │ │
│   │ ResponsePredictionService — ML response probability            │ │
│   │ EngagementRiskAdaptation — Channel/timing optimization         │ │
│   │ ContactResolver — Reporter contact resolution                  │ │
│   │ CaseService — CRUD operations                                  │ │
│   │ CombinedFollowUpBuilder — 4-source question merge              │ │
│   │ FollowUpTrigger — Decision engine                              │ │
│   │ FollowUpOrchestrator — Pipeline runner                         │ │
│   └──────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│   ┌─── DATA MODELS (11 model files, 19 tables) ─────────────────────┐ │
│   │ case.py → AECase (ae_cases) — 35+ columns                       │ │
│   │ case.py → MissingField (missing_fields)                          │ │
│   │ followup.py → FollowUpDecision, FollowUpAttempt,                 │ │
│   │               FollowUpResponse, FieldUpdateHistory,              │ │
│   │               CaseConfidenceHistory, AdaptiveLoopSession         │ │
│   │ signal.py → SafetySignal (safety_signals)                        │ │
│   │ audit.py → AuditLog (audit_logs)                                 │ │
│   │ pv_audit_trail.py → PVAuditTrail (pv_audit_trail)               │ │
│   │ lifecycle_tracker.py → FollowUpLifecycle, LifecycleAttempt,      │ │
│   │                        LifecycleAuditLog, ReporterPolicy         │ │
│   │ case_document.py → CaseDocument (case_documents)                 │ │
│   │ repo_document.py → RepoDocument (repo_documents)                 │ │
│   │ regulatory.py → RegulatoryWorkflow (regulatory_workflows)        │ │
│   │ user.py → User (users)                                           │ │
│   └──────────────────────────────────────────────────────────────────┘ │
└────────┬──────────────────┬────────────────────┬────────────────────────┘
         │                  │                    │
    ┌────▼────────┐   ┌─────▼─────────┐   ┌─────▼──────┐
    │ PostgreSQL  │   │   Twilio      │   │ Mistral AI │
    │ 15          │   │   Voice API   │   │ LLM        │
    │ + pgvector  │   │   WhatsApp    │   │ (Primary)  │
    │ + Redis 7   │   │   Webhooks    │   │ Claude     │
    │             │   │               │   │ (Backup)   │
    └─────────────┘   └───────────────┘   └────────────┘
```

---

## 2. DATABASE SCHEMA (Complete)

### 2.1 Core Case Tables

#### `ae_cases` — The primary adverse event case record
```
case_id              UUID PK (auto uuid4)
primaryid            Integer UNIQUE INDEXED
receipt_date         DateTime
patient_age          Integer (nullable)
patient_sex          String(10)
patient_age_group    String(20)
patient_initials     String(20)     ← CIOMS field
suspect_drug         String(500) NOT NULL
drug_route           String(100)
drug_dose            String(500)
adverse_event        String(1000) NOT NULL
event_date           DateTime
event_outcome        String(100)
reporter_type        String(10)     ← MD/HP/CN/etc
reporter_country     String(5)
reporter_email       String(200)
reporter_phone       String(50)
indication           String(500)    ← CIOMS field
therapy_start        DateTime       ← CIOMS field
therapy_end          DateTime       ← CIOMS field
therapy_duration     Integer (days)
dechallenge          String(50)
rechallenge          String(50)
concomitant_drugs    Text
medical_history      Text
manufacturer_name    String(500)
report_type          String(50)
seriousness_score    Float (default 0.0)
data_completeness_score Float (default 0.0)
case_priority        String(20)
case_status          String(50) default 'INITIAL_RECEIVED'
is_serious           Boolean (default False)
requires_followup    Boolean (default True)
human_reviewed       Boolean (default False)
reviewed_by          String(100)
reviewed_at          DateTime
review_notes         Text           ← contains [REVIEWER_QUESTION] and [REPO_DOC_ATTACHED] tags
risk_level           String(20)
priority_score       String(20)
intake_source        String(20) default 'CSV'  ← CSV/PDF/MANUAL
source_filename      String(500)
created_at           DateTime
updated_at           DateTime

Relationships: missing_fields, followup_attempts, confidence_history, adaptive_sessions, documents
```

#### `missing_fields` — Per-field analysis from Data Completeness Agent
```
id                    UUID PK
case_id               UUID FK → ae_cases
field_name            String
field_category        String
is_missing            Boolean
is_unclear            Boolean
is_inconsistent       Boolean
safety_criticality    String  ← CRITICAL/HIGH/MEDIUM/LOW
regulatory_requirement Boolean
should_follow_up      Boolean
followup_priority     Integer
question_value_score  Float
missing_reason        String
impact_explanation    String
created_at            DateTime
```

### 2.2 Follow-Up Tables

#### `followup_decisions` — AI decision records
```
decision_id                   UUID PK
case_id                       UUID FK
decision_type                 String
decision_reason               String
agent_name                    String
confidence_score              Float
predicted_response_probability Float
optimal_timing_hours          Float
recommended_channel           String
case_risk_level              String
escalation_required          Boolean
human_override               Boolean
override_reason              String
created_at                   DateTime
```

#### `followup_attempts` — Each sent follow-up
```
attempt_id          UUID PK
case_id             UUID FK
decision_id         UUID FK
iteration_number    Integer
attempt_number      Integer
safety_confidence   Float
data_completeness   Float
risk_score          Float
response_probability Float
questions_sent      JSON        ← array of question objects
questions_count     Integer
fields_requested    JSON
channel             String      ← EMAIL/PHONE/WHATSAPP
sent_method         String
sent_to             String
recipient_email     String
secure_token        String      ← for reporter portal access
decision            String
reasoning           String
sent_at             DateTime
response_received   Boolean
response_status     String      ← SENT/RESPONDED/NO_RESPONSE
response_received_at DateTime
responded_at        DateTime
response_data       JSON
response_time_hours Float
questions_answered  Integer
data_quality_score  Float
status              String      ← PENDING/RESPONDED/NO_RESPONSE/EXPIRED
information_gained  Float
stop_followup       Boolean
stop_reason         String
created_at / updated_at DateTime
```

#### `followup_responses` — Individual reporter answers
```
response_id          UUID PK
attempt_id           UUID FK
case_id              UUID FK
question_id          String
question_text        String
field_name           String
response_text        String
field_value          String
previous_value       String     ← old value before update
value_type           String
channel              String
attempt_number       Integer
is_complete          Boolean
is_validated         Boolean
needs_clarification  Boolean
processed            Boolean
ai_extracted_value   String     ← AI interpretation
extraction_confidence Float
response_file_url    String
responded_at         DateTime
created_at           DateTime
```

#### `field_update_history` — Field version tracking
```
id           UUID PK
case_id      UUID FK
response_id  UUID FK
field_name   String
old_value    String
new_value    String
source       String     ← EMAIL/PHONE/WHATSAPP/WEB
changed_by   String     ← reporter email, system, reviewer
changed_at   DateTime
```

### 2.3 Signal & Regulatory Tables

#### `safety_signals` — Detected safety signals
```
signal_id                    UUID PK
drug_name                    String
adverse_event                String
signal_type                  String  ← EMERGING/CONFIRMED/DISMISSED
case_count                   Integer
reporting_rate               Float
proportional_reporting_ratio Float
temporal_pattern             String
demographic_pattern          String
signal_strength              String  ← STRONG/MODERATE/WEAK
clinical_significance        String
trend                        String  ← UP/DOWN/STABLE
is_active                    Boolean
signal_status                String  ← NEW/UNDER_REVIEW/ESCALATED/RESOLVED/FALSE_POSITIVE
detected_at / reviewed_at / updated_at DateTime
reviewed_by                  String
seriousness_ratio            Float
risk_priority                String  ← CRITICAL/HIGH/MEDIUM/LOW
review_note                  String
frozen_snapshot              JSON    ← immutable regulatory evidence
```

#### `regulatory_workflows` — Triggered when signal escalated
```
id               UUID PK
signal_id        UUID UNIQUE INDEXED FK
status           String default 'IN_PROGRESS'
report_type      String default 'CIOMS_DRAFT'
due_date         DateTime
cioms_placeholder String
created_at       DateTime
```

### 2.4 Lifecycle Tables

#### `followup_lifecycle` — One record per case
```
lifecycle_id              UUID PK
case_id                   UUID FK UNIQUE
reporter_type             Enum (HCP/NON_HCP)
reporter_subtype          String
attempt_count             Integer default 0
max_attempts              Integer
last_attempt_at           DateTime
next_reminder_due         DateTime
reminder_interval_hours   Integer default 24
response_status           Enum (PENDING/PARTIAL/COMPLETE/NO_RESPONSE)
questions_total_sent      Integer default 0
questions_total_answered  Integer default 0
questions_this_round      Integer
max_questions_per_round   Integer
escalation_status         Enum (NONE/FLAGGED/URGENT/ESCALATED_TO_REVIEWER/ESCALATED_TO_MEDICAL)
escalation_reason         String
escalated_at              DateTime
escalated_to              String
seriousness_level         Enum (LOW/MEDIUM/HIGH/CRITICAL)
regulatory_deadline       DateTime
days_remaining            Integer
deadline_type             String
regulatory_submitted      Boolean default False
completeness_score        Float default 0.0
safety_confidence_score   Float default 0.0
target_completeness       Float default 0.85
dead_case_flag            Boolean default False
dead_case_reason          String
dead_case_at              DateTime
closed_at                 DateTime
closed_by                 String
closure_reason            String
lifecycle_status          Enum (ACTIVE/AWAITING_RESPONSE/ESCALATED/COMPLETED/DEAD_CASE/CLOSED)
created_at / updated_at   DateTime

Relationships: case, audit_logs, attempts
```

#### `lifecycle_attempts`, `lifecycle_audit_log`, `reporter_policies` — Supporting lifecycle tables
(See DATABASE_SCHEMA section in main report for details)

### 2.5 Audit & Document Tables

#### `pv_audit_trail` — Immutable, append-only (FDA 21 CFR Part 11)
```
audit_id          UUID PK
case_id           UUID (nullable, indexed)
signal_id         UUID (nullable, indexed)
timestamp         DateTime (indexed)
actor_type        String  ← AI/HUMAN/SYSTEM/REPORTER
actor_id          String
action_type       String (indexed)  ← 20+ types
description       String
previous_value    JSON
new_value         JSON
decision_metadata JSON
model_version     String
confidence_score  Float
channel           String  ← EMAIL/PHONE/WHATSAPP/SMS
regulatory_impact String

Composite Indexes:
  ix_pv_audit_case_action  (case_id, action_type)
  ix_pv_audit_case_time    (case_id, timestamp)
  ix_pv_audit_actor_time   (actor_type, timestamp)
  ix_pv_audit_signal_action (signal_id, action_type)
```

#### `users` — Authentication & authorization
```
user_id               UUID PK
email                 String UNIQUE INDEXED
username              String UNIQUE
password_hash         String  ← Argon2
full_name             String
role                  String  ← PV_SPECIALIST/SAFETY_OFFICER/ADMIN
department            String
organization          String
permissions           JSON
can_approve_high_risk Boolean
mfa_enabled           Boolean
failed_login_attempts Integer
is_active             Boolean
last_login            DateTime
created_at            DateTime
```

---

## 3. AUTHENTICATION & SECURITY

### 3.1 Auth Flow
```
1. User submits email + password → POST /api/auth/login (form-encoded)
2. Backend verifies against Argon2 hash
3. Returns JWT access_token (60 min) + refresh_token (7 days)
4. Frontend stores in localStorage
5. All subsequent requests include Authorization: Bearer <token>
6. 401 response → auto-redirect to /login
```

### 3.2 Role-Based Access Control
| Role | Can View | Can Analyze | Can Override | Can Approve High-Risk |
|---|---|---|---|---|
| PV_SPECIALIST | All cases | Yes | No | No |
| SAFETY_OFFICER | All cases | Yes | Yes | Yes |
| ADMIN | Everything | Yes | Yes | Yes |

### 3.3 Reporter Portal Security
- No auth required (public page)
- Access via unique `secure_token` (UUID per follow-up attempt)
- Token validated server-side before showing questions
- Token expired/used → access denied

---

## 4. FRONTEND ROUTING (Complete)

| Route | Component | Auth Required | Purpose |
|---|---|---|---|
| `/` | → `/dashboard` | Yes | Redirect |
| `/dashboard` | Dashboard | Yes | Overview metrics, KPIs, PDF upload |
| `/case-analysis` | CaseList | Yes | All cases with filters |
| `/cioms-upload` | CiomsUploadPage | Yes | CIOMS PDF upload + repo selection |
| `/cases` | CaseList | Yes | Alias for case-analysis |
| `/cases/:caseId` | CaseAnalysis | Yes | Deep case view + 4 question panels |
| `/followup-attempts` | FollowUpAttempts | Yes | Follow-up history tracker |
| `/follow-up/:caseId` | FollowUp | Yes | Single case follow-up |
| `/signals` | Signals | Yes | Safety signal dashboard |
| `/explainability/:caseId` | Explainability | Yes | AI decision explanations |
| `/lifecycle` | LifecycleTracking | Yes | All case lifecycles |
| `/lifecycle/:caseId` | LifecycleTracking | Yes | Single case lifecycle |
| `/audit-trail` | AuditTrail | Yes | PV audit trail viewer |
| `/reviewer` | ReviewerDashboard | Yes | Novartis Review panel |
| `/followup-agent` | FollowUpAgent | **No** | Reporter response portal |
| `/login` | Login | No | Authentication |

---

## 5. CONFIGURATION (config.py)

```python
class Settings(BaseSettings):
    # Application
    APP_NAME = "SmartFU"
    ENVIRONMENT = "development"
    
    # Database
    DATABASE_URL: str          # PostgreSQL connection string
    DB_PASSWORD: str
    REDIS_URL = "redis://localhost:6379/0"
    
    # Security
    SECRET_KEY: str            # JWT signing key
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 60
    REFRESH_TOKEN_EXPIRE_DAYS = 7
    CORS_ORIGINS = ["http://localhost:3000", "http://localhost:5173",
                    "http://localhost:3001", "http://localhost:3002"]
    
    # AI/ML
    ANTHROPIC_API_KEY: str
    OPENAI_API_KEY = ""
    GEMINI_API_KEY = ""
    MISTRAL_API_KEY = ""
    MODELS_PATH = "./models"
    
    # Email
    SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD: optional
    EMAIL_FROM = "noreply@smartfu.com"
    
    # Twilio
    TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN: optional
    TWILIO_FROM_NUMBER, TWILIO_WHATSAPP_NUMBER: optional
    
    # URLs
    BACKEND_URL = "http://localhost:8000"
    FRONTEND_URL = "http://localhost:3000"
    
    # Feature Flags
    ENABLE_AI_AGENTS = True
    ENABLE_EMAIL_FOLLOWUPS = False
    ENABLE_SMS_FOLLOWUPS = False
    ENABLE_SIGNAL_DETECTION = True
    MAX_UPLOAD_SIZE_MB = 50
```

---

## 6. DOCKER INFRASTRUCTURE

### docker-compose.yml
```yaml
services:
  postgres:
    image: postgres:15
    user: smartfu_user
    database: smartfu
    port: 5432
    init-script: init-pgvector.sh  # enables pgvector extension
    volume: postgres_data
    
  redis:
    image: redis:7-alpine
    port: 6379
    volume: redis_data

network: smartfu-network (bridge)
```

### Backend Dockerfile
```dockerfile
FROM python:3.11-slim
RUN apt-get install build-essential libpq-dev curl
COPY requirements.txt → pip install
HEALTHCHECK: curl -f http://localhost:8000/health
EXPOSE 8000
CMD: uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 7. DEPENDENCY LIST (Complete)

| Category | Package | Version | Purpose |
|---|---|---|---|
| Web Framework | fastapi | 0.109.0 | Async REST API |
| ASGI Server | uvicorn[standard] | 0.27.0 | Production server |
| ORM | sqlalchemy | 2.0.25 | Database abstraction |
| Migrations | alembic | 1.13.1 | Schema migrations |
| PostgreSQL | psycopg2-binary | 2.9.9 | DB driver |
| Vector DB | pgvector | 0.2.4 | Vector similarity extension |
| Validation | pydantic | 2.5.3 | Data validation |
| Settings | pydantic-settings | 2.1.0 | Config management |
| JWT | python-jose[cryptography] | 3.3.0 | Token generation |
| Auth | passlib[bcrypt] | 1.7.4 | Password hashing |
| Data | pandas | 2.2.0 | CSV processing |
| Data | numpy | 1.26.3 | Numerical operations |
| PDF | pdfplumber | 0.10.3 | PDF text extraction |
| ML | scikit-learn | 1.4.0 | Risk classification |
| ML | xgboost | 2.0.3 | Gradient boosting |
| ML | imbalanced-learn | 0.12.0 | SMOTE oversampling |
| LLM | mistralai | ≥0.4.0 | Primary LLM |
| LLM | langchain | 0.1.4 | LLM orchestration |
| LLM | langchain-anthropic | 0.1.0 | Claude integration |
| LLM | langgraph | 0.0.19 | Multi-agent graphs |
| LLM | anthropic | 0.18.1 | Backup LLM |
| Vector | faiss-cpu | 1.7.4 | FAISS index |
| Embeddings | sentence-transformers | 2.2.2 | Semantic scoring |
| Cache | redis | 5.0.1 | Caching layer |
| Communication | twilio | ≥8.0.0 | Voice + WhatsApp |
| HTTP | httpx | 0.26.0 | Async HTTP client |
| HTTP | aiohttp | 3.9.1 | Async HTTP |
| XML | lxml | 5.1.0 | XML parsing |

---

*This document covers the complete technical architecture. See feature-specific docs for deep dives into each component.*
