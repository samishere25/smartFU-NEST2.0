# SmartFU — Complete Technical Documentation

> **Smart Follow-Up System for Pharmacovigilance**
> AI-powered adverse event case management with intelligent follow-up automation

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture & Tech Stack](#2-architecture--tech-stack)
3. [Project Structure](#3-project-structure)
4. [Backend Deep Dive](#4-backend-deep-dive)
   - 4.1 [FastAPI Application (main.py)](#41-fastapi-application-mainpy)
   - 4.2 [Database Layer](#42-database-layer)
   - 4.3 [Data Models (17 ORM Models)](#43-data-models-17-orm-models)
   - 4.4 [Authentication & Security](#44-authentication--security)
   - 4.5 [API Routes (21 Routers)](#45-api-routes-21-routers)
   - 4.6 [Pydantic Schemas](#46-pydantic-schemas)
5. [AI Agent Pipeline](#5-ai-agent-pipeline)
   - 5.1 [Pipeline Architecture](#51-pipeline-architecture)
   - 5.2 [Agent 1 — Data Completeness](#52-agent-1--data-completeness)
   - 5.3 [Agent 2 — Medical Reasoning (RAG)](#53-agent-2--medical-reasoning-rag)
   - 5.4 [Agent 3 — Risk Assessment (ML)](#54-agent-3--risk-assessment-ml)
   - 5.5 [Agent 4 — Response Strategy](#55-agent-4--response-strategy)
   - 5.6 [Agent 5 — Escalation Logic](#56-agent-5--escalation-logic)
   - 5.7 [Agent 6 — Question Generation (RL)](#57-agent-6--question-generation-rl)
   - 5.8 [Agent 7 — Follow-Up Orchestration](#58-agent-7--followup-orchestration)
   - 5.9 [Final Confidence Aggregation](#59-final-confidence-aggregation)
   - 5.10 [Connected Flow Orchestrator](#510-connected-flow-orchestrator)
   - 5.11 [Adaptive Loop Engine](#511-adaptive-loop-engine)
6. [Core Services](#6-core-services)
   - 6.1 [CIOMS PDF Extraction](#61-cioms-pdf-extraction)
   - 6.2 [Combined Follow-Up Builder](#62-combined-follow-up-builder)
   - 6.3 [Follow-Up Trigger (Multi-Channel)](#63-follow-up-trigger-multi-channel)
   - 6.4 [Communication Service](#64-communication-service)
   - 6.5 [Signal Detection Service](#65-signal-detection-service)
   - 6.6 [Explainability Builder](#66-explainability-builder)
   - 6.7 [Lifecycle Tracker](#67-lifecycle-tracker)
   - 6.8 [Audit Service](#68-audit-service)
   - 6.9 [Case Service](#69-case-service)
7. [Frontend Deep Dive](#7-frontend-deep-dive)
   - 7.1 [Application Shell (App.jsx)](#71-application-shell-appjsx)
   - 7.2 [Pages & Components](#72-pages--components)
   - 7.3 [API Client (api.js)](#73-api-client-apijs)
   - 7.4 [State Management](#74-state-management)
8. [Data Flow — End to End](#8-data-flow--end-to-end)
9. [Security Architecture](#9-security-architecture)
10. [Configuration Reference](#10-configuration-reference)
11. [Dependencies](#11-dependencies)
12. [Glossary](#12-glossary)

---

## 1. System Overview

SmartFU is a **pharmacovigilance (PV) automation platform** that manages adverse event (AE) case intake, analysis, and follow-up. It replaces manual safety officer workflows with an AI-driven pipeline that:

1. **Ingests** CIOMS Form-I PDFs → extracts 24 structured fields via LLM + regex
2. **Analyzes** each case through a 7-agent AI pipeline → produces risk score, seriousness assessment, follow-up decision
3. **Generates** prioritized follow-up questions using Reinforcement Learning scoring
4. **Sends** follow-up requests via Email, WhatsApp, and Phone simultaneously
5. **Tracks** lifecycle state (intake → follow-up → escalation → closure) per regulatory deadlines
6. **Detects** safety signals via Proportional Reporting Ratio (PRR) across all cases
7. **Explains** every AI decision with deterministic, audit-ready explainability

### Key Capabilities

| Capability | What It Does |
|---|---|
| **CIOMS Upload** | PDF → structured data via Mistral LLM with regex fallback |
| **7-Agent Pipeline** | Data Completeness → Medical Reasoning → Risk Assessment → Response Strategy → Escalation → Question Generation → Follow-Up Orchestration |
| **TFU Decision Agent** | Automated follow-up trigger with multi-channel dispatch |
| **Multi-Channel Comms** | Email (SMTP), WhatsApp (Twilio), Phone (Twilio Voice) — simultaneous |
| **Reviewer Mode** | Human reviewer can add questions before AI sends follow-up |
| **Lifecycle Tracking** | HCP/Non-HCP policies, 24h reminders, 7/15-day deadlines, dead-case detection |
| **Severity Monitor** | PRR-based signal detection with regulatory escalation workflows |
| **Audit Trail** | FDA 21 CFR Part 11 compliant, immutable, append-only logging |
| **Explainability** | LLM-free, deterministic explanations with agent trace & regulatory checkpoints |
| **Adaptive Loop** | Iterative convergence engine — re-runs pipeline until safety confidence meets threshold |

---

## 2. Architecture & Tech Stack

```
┌──────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                         │
│  React 18.2 · Vite 5.0 · Tailwind CSS 3.4 · React Router 7.13  │
│  Recharts · PDF Upload · Token-based Auth · LocalStorage State  │
└───────────────────────────┬──────────────────────────────────────┘
                            │ HTTP/REST (Bearer JWT)
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                       BACKEND (FastAPI)                          │
│  FastAPI 0.109 · Python 3.11 · Uvicorn · 21 API Routers         │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              SECURITY LAYER                                │  │
│  │  Argon2 Hashing · JWT HS256 · RBAC · Rate Limiting         │  │
│  │  Security Headers · Account Lockout · CORS                 │  │
│  └────────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              AI AGENT PIPELINE                             │  │
│  │  7 Sequential Agents · LangGraph State · 3-Feature Flow    │  │
│  │  Mistral LLM · BioBERT RAG · FAISS · Sentence Transformers│  │
│  │  Logistic Regression ML · Reinforcement Learning Scoring   │  │
│  └────────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              SERVICES LAYER                                │  │
│  │  CIOMS Extractor · Communication (Twilio/SMTP)             │  │
│  │  Signal Detection · Lifecycle · Audit · Explainability     │  │
│  └────────────────────────────────────────────────────────────┘  │
└───────────────────────────┬──────────────────────────────────────┘
                            │ SQLAlchemy ORM
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                     DATABASE (PostgreSQL)                         │
│  17 Tables · UUID PKs · pgvector Extension · Connection Pool     │
│  Pool: 10 persistent + 20 overflow = 30 max connections          │
└──────────────────────────────────────────────────────────────────┘
```

### Tech Stack Summary

| Layer | Technology | Version |
|---|---|---|
| **Frontend** | React | 18.2 |
| **Build Tool** | Vite | 5.0 |
| **CSS** | Tailwind CSS | 3.4 |
| **Routing** | React Router | 7.13 |
| **Charts** | Recharts | — |
| **Backend** | FastAPI | 0.109 |
| **Language** | Python | 3.11 |
| **Server** | Uvicorn | 0.27 |
| **Database** | PostgreSQL | 15+ |
| **ORM** | SQLAlchemy | 2.0.25 |
| **Migrations** | Alembic | 1.13.1 |
| **Vector DB** | pgvector / FAISS | 0.2.4 / 1.7.4 |
| **LLM** | Mistral Large | via mistralai SDK |
| **Embeddings** | Sentence-Transformers | 2.2.2 (MiniLM-L6-v2) |
| **Medical NLP** | BioBERT | pritamdeka/BioBERT-mnli |
| **ML** | scikit-learn / XGBoost | 1.4.0 / 2.0.3 |
| **PDF Parsing** | pdfplumber | 0.10.3 |
| **Auth** | JWT (python-jose) + Argon2 | HS256 |
| **Rate Limiting** | slowapi | 0.1.9 (optional) |
| **SMS/Voice/WhatsApp** | Twilio | 8.0+ |
| **Email** | smtplib (Python stdlib) | — |

---

## 3. Project Structure

```
smartfu/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app entry, middleware, routers
│   │   ├── agents/                    # AI Agent Pipeline
│   │   │   ├── graph.py               # Master orchestration (7 agents + connected flow)
│   │   │   ├── gemini_client.py       # LLM client (Mistral API wrapper)
│   │   │   ├── risk_assessment_agent.py   # ML-based risk classifier
│   │   │   ├── medical_reasoning_agent.py # RAG medical analysis (FAISS + BioBERT)
│   │   │   ├── adaptive_loop.py       # Iterative convergence engine
│   │   │   └── knowledge_base/        # FAISS index + metadata for RAG
│   │   │       ├── faiss_index.bin
│   │   │       └── metadata.pkl
│   │   ├── api/
│   │   │   └── routes/                # 21 API routers
│   │   │       ├── auth.py            # Login, register, /me
│   │   │       ├── cases.py           # Case CRUD, analysis, reviewer questions
│   │   │       ├── followups.py       # Follow-up attempts & responses
│   │   │       ├── signals.py         # Safety signal endpoints
│   │   │       ├── lifecycle.py       # Lifecycle state machine
│   │   │       ├── governance.py      # Trust, privacy, oversight
│   │   │       ├── pv_audit.py        # PV audit trail (21 CFR Part 11)
│   │   │       ├── cioms_combined.py  # Combined CIOMS send
│   │   │       ├── repo_documents.py  # Global document repository
│   │   │       ├── pdf_upload.py      # CIOMS PDF upload
│   │   │       ├── case_documents.py  # Per-case document management
│   │   │       ├── analytics.py       # Dashboard metrics
│   │   │       ├── admin.py           # Admin operations
│   │   │       ├── regulatory.py      # Regulatory workflow
│   │   │       ├── reviewer.py        # Reviewer dashboard
│   │   │       ├── reporter_portal.py # Reporter response portal
│   │   │       ├── twilio_webhooks.py # Twilio SMS/WhatsApp webhooks
│   │   │       ├── voice.py           # Twilio Voice webhooks
│   │   │       ├── whatsapp.py        # WhatsApp message handling
│   │   │       ├── email_webhooks.py  # Email response processing
│   │   │       └── followup_agent.py  # Conversational follow-up (public)
│   │   ├── core/
│   │   │   ├── config.py             # Pydantic Settings (.env loader)
│   │   │   ├── security.py           # JWT, Argon2, RBAC
│   │   │   └── dependencies.py       # FastAPI dependencies
│   │   ├── db/
│   │   │   ├── session.py            # Engine + SessionLocal + get_db()
│   │   │   ├── base.py               # SQLAlchemy declarative base
│   │   │   └── base_class.py         # Base model mixin
│   │   ├── models/                    # 10 files → 17 SQLAlchemy models
│   │   │   ├── case.py               # AECase + MissingField
│   │   │   ├── followup.py           # FollowUpDecision, Attempt, Response, etc.
│   │   │   ├── user.py               # User
│   │   │   ├── audit.py              # AuditLog
│   │   │   ├── signal.py             # SafetySignal
│   │   │   ├── lifecycle_tracker.py   # FollowUpLifecycle, Attempt, AuditLog, Policy
│   │   │   ├── repo_document.py      # RepoDocument
│   │   │   ├── case_document.py      # CaseDocument
│   │   │   ├── pv_audit_trail.py     # PVAuditTrail
│   │   │   └── regulatory.py         # RegulatoryWorkflow
│   │   ├── schemas/                   # Pydantic request/response models
│   │   │   ├── user.py               # UserBase, UserCreate, UserInDB, Token
│   │   │   ├── case.py               # CaseCreate, CaseList, CaseResponse
│   │   │   ├── followup.py           # FollowUpSchemas
│   │   │   ├── response.py           # ResponseSchemas
│   │   │   └── ...
│   │   ├── services/                  # 28 service modules
│   │   │   ├── cioms_extractor.py     # PDF → 24 CIOMS fields
│   │   │   ├── case_service.py        # Case CRUD + CSV upload
│   │   │   ├── combined_followup.py   # Merges AI + reviewer + checklist questions
│   │   │   ├── followup_trigger.py    # Multi-channel dispatch
│   │   │   ├── communication_service.py # Email/WhatsApp/Phone sending
│   │   │   ├── signal_service.py      # PRR signal detection
│   │   │   ├── explainability.py      # Deterministic explanations
│   │   │   ├── lifecycle_tracker.py   # Lifecycle state machine
│   │   │   ├── audit_service.py       # Audit logging
│   │   │   ├── question_scoring.py    # RL-enhanced question ranking
│   │   │   ├── data_completeness.py   # Weighted completeness scoring
│   │   │   ├── response_prediction.py # Response probability estimation
│   │   │   ├── contact_resolver.py    # Reporter contact lookup
│   │   │   ├── cioms_question_generator.py # LLM question text generation
│   │   │   ├── checklist_extractor.py # PDF checklist → structured questions
│   │   │   └── ...
│   │   ├── ml/                        # ML model utilities
│   │   └── utils/                     # Utility modules
│   │       ├── signal_detection.py
│   │       ├── confidence_attribution.py
│   │       ├── case_memory_engine.py
│   │       ├── question_value_scorer.py
│   │       ├── safety_confidence.py
│   │       ├── timing_optimization.py
│   │       └── ...
│   ├── models/                        # Trained ML model files
│   │   └── question_rl_state.json     # RL reward state
│   ├── requirements.txt               # 45+ Python packages
│   ├── Dockerfile
│   └── alembic.ini
│
├── frontend/
│   ├── src/
│   │   ├── main.jsx                   # React entry point
│   │   ├── App.jsx                    # Root shell, routing, nav
│   │   ├── index.css                  # Tailwind imports
│   │   ├── pages/                     # 14 page components
│   │   │   ├── CiomsUploadPage.jsx    # PDF upload + reviewer toggle
│   │   │   ├── CaseAnalysis.jsx       # Single case deep-dive (6 tabs)
│   │   │   ├── CaseList.jsx           # Case repository table
│   │   │   ├── Dashboard.jsx          # KPI overview
│   │   │   ├── Signals.jsx            # Severity monitor
│   │   │   ├── LifecycleTracking.jsx  # Lifecycle state machine UI
│   │   │   ├── Explainability.jsx     # AI decision audit
│   │   │   ├── AuditTrail.jsx         # System-wide audit browser
│   │   │   ├── FollowUp.jsx           # Per-case follow-up detail
│   │   │   ├── FollowUpAttempts.jsx   # Follow-up attempt tracker
│   │   │   ├── FollowUpAgent.jsx      # Conversational follow-up (public)
│   │   │   ├── ReviewerDashboard.jsx  # Reviewer case review
│   │   │   ├── Login.jsx              # Authentication
│   │   │   └── PdfTest.jsx            # PDF testing
│   │   ├── components/                # 15+ reusable components
│   │   │   ├── CiomsUpload.jsx        # File upload widget
│   │   │   ├── CiomsDetailsSection.jsx
│   │   │   ├── HumanOversight.jsx
│   │   │   ├── AIConfidenceBadge.jsx
│   │   │   ├── MissingFieldsPanel.jsx
│   │   │   ├── QuestionIntelligence.jsx
│   │   │   ├── RepoDocumentsBlock.jsx
│   │   │   ├── ResponsePredictionCard.jsx
│   │   │   ├── FollowUpOptimizationCard.jsx
│   │   │   ├── Feature3Components.jsx
│   │   │   ├── ErrorState.jsx
│   │   │   ├── LoadingState.jsx
│   │   │   ├── tabs/                  # Tab sub-components
│   │   │   ├── lifecycle/             # Lifecycle sub-components
│   │   │   └── governance/            # Governance sub-components
│   │   ├── context/
│   │   │   └── CaseEventContext.jsx   # Cross-component event bus
│   │   └── utils/
│   │       ├── api.js                 # Centralized API client (45+ methods)
│   │       └── followUpOptimization.js # Follow-up utility functions
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── index.html
│
├── docker-compose.yml
├── docs/                              # 14 documentation files
└── models/                            # Shared ML model directory
```

---

## 4. Backend Deep Dive

### 4.1 FastAPI Application (`main.py`)

The backend entry point initializes the FastAPI app with comprehensive middleware, 21 API routers, and global error handling.

#### App Initialization

```python
app = FastAPI(
    title="SmartFU API",
    version="1.0.0",
    docs_url="/docs",      # Swagger UI
    redoc_url="/redoc",     # ReDoc
    lifespan=lifespan       # async context manager
)
```

#### Middleware Stack (applied in order)

| # | Middleware | Purpose |
|---|---|---|
| 1 | **CORS** | Allows `localhost:3000,5173,3001,3002`. Methods: GET, POST, PUT, PATCH, DELETE, OPTIONS. Headers: Authorization, Content-Type, Accept, Origin, X-Requested-With |
| 2 | **Security Headers** | Adds 6 HTTP security headers to every response |
| 3 | **Request Timing** | Adds `X-Process-Time` header (wall-clock seconds) |
| 4 | **Rate Limiting** | 60 req/min per IP via slowapi (optional — degrades gracefully if not installed) |

#### Security Headers (added to every response)

| Header | Value | Purpose |
|---|---|---|
| `X-Content-Type-Options` | `nosniff` | Prevents MIME-type sniffing |
| `X-Frame-Options` | `DENY` | Prevents clickjacking |
| `X-XSS-Protection` | `1; mode=block` | Legacy XSS filter |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Controls referrer leakage |
| `Content-Security-Policy` | `default-src 'self'; script-src 'self' 'unsafe-inline'; ...` | Restricts resource loading |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=(), payment=()` | Disables browser APIs |

#### Global Exception Handler

Catches all unhandled exceptions:
- Logs full traceback with `exc_info=True`
- Returns HTTP 500 with `{"detail": "Internal server error", "message": ...}`
- In debug mode: includes exception string; in production: generic message

#### Lifespan (Startup/Shutdown)

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting SmartFU API...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug Mode: {settings.DEBUG}")
    yield
    logger.info("👋 Shutting down SmartFU API...")
```

Tables are managed by **Alembic** (not auto-created at startup).

---

### 4.2 Database Layer

#### Connection Configuration (`db/session.py`)

```python
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,     # Detects stale connections before use
    pool_size=10,           # Persistent connections
    max_overflow=20         # Burst connections (total max = 30)
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

#### Session Dependency

```python
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

Used as `db: Session = Depends(get_db)` in all route handlers.

#### Database: PostgreSQL with pgvector

- **pgvector** extension enables vector similarity search (for future embedding-based queries)
- All primary keys are `UUID(as_uuid=True)` with `uuid.uuid4` defaults
- Migrations managed via Alembic (`alembic.ini` + `alembic/versions/`)

---

### 4.3 Data Models (17 ORM Models)

All models inherit from SQLAlchemy's `declarative_base()`. The central entity is **`AECase`** — all other models reference it.

#### Entity Relationship Diagram

```
                        ┌─────────────┐
                        │    User     │
                        │  (users)    │
                        └─────────────┘

┌──────────────┐    1:N ┌─────────────┐ 1:N ┌──────────────────┐
│ MissingField │◄───────│   AECase    │────►│  FollowUpAttempt │
│(missing_fields)│      │ (ae_cases)  │     │(followup_attempts)│
└──────────────┘        └──────┬──────┘     └────────┬─────────┘
                               │                     │ 1:N
                    1:1 ┌──────┴──────┐     ┌────────▼─────────┐
                    ┌───►FollowUpLife-│     │ FollowUpResponse  │
                    │   │   cycle     │     │(followup_responses)│
                    │   └─────────────┘     └──────────────────┘
                    │
               1:N  │   ┌─────────────┐
               ┌────┴───►CaseDocument │
               │        │(case_docs)  │
               │        └─────────────┘
               │
          1:N  │   ┌──────────────────┐
          ┌────┴───►CaseConfidence-   │
          │        │  History         │
          │        └──────────────────┘
          │
     1:N  │   ┌──────────────────┐
     ┌────┴───►AdaptiveLoop-     │
     │        │  Session         │
     │        └──────────────────┘

┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  AuditLog    │  │ SafetySignal │  │ PVAuditTrail │
│ (audit_logs) │  │(safety_sigs) │  │(pv_audit_trail)│
└──────────────┘  └──────────────┘  └──────────────┘

┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ RepoDocument │  │Regulatory-   │  │FieldUpdate-  │
│(repo_docs)   │  │  Workflow    │  │  History     │
└──────────────┘  └──────────────┘  └──────────────┘
```

#### Model Details

##### `AECase` (table: `ae_cases`) — Central Entity

The primary table storing every adverse event case in the system.

| Column | Type | Key Info |
|---|---|---|
| `case_id` | UUID | Primary key, auto-generated |
| `primaryid` | Integer | FAERS ID, **unique**, indexed |
| `receipt_date` | DateTime | When case was received |
| `patient_age` | Integer | Patient age |
| `patient_sex` | String(10) | M/F |
| `patient_age_group` | String(20) | Age group classification |
| `suspect_drug` | String(500) | **Required** — drug name |
| `drug_route` | String(100) | Administration route |
| `drug_dose` | String(500) | Dosage information |
| `adverse_event` | String(1000) | **Required** — event description |
| `event_date` | DateTime | When event occurred |
| `event_outcome` | String(100) | Outcome (recovered, fatal, etc.) |
| `reporter_type` | String(10) | Reporter occupation code |
| `reporter_country` | String(5) | Country code |
| `seriousness_score` | Float | AI-calculated seriousness (0.0–1.0) |
| `data_completeness_score` | Float | Weighted completeness (0.0–1.0) |
| `case_priority` | String(20) | Priority classification |
| `case_status` | String(50) | Default: `INITIAL_RECEIVED` |
| `is_serious` | Boolean | Seriousness flag |
| `requires_followup` | Boolean | Default: `True` |
| `human_reviewed` | Boolean | Whether a human has reviewed |
| `risk_level` | String(20) | HIGH / MEDIUM / LOW |
| `intake_source` | String(20) | Default: `CSV` |
| `reporter_email` | String(200) | For email follow-up |
| `reporter_phone` | String(50) | For phone/WhatsApp follow-up |
| `indication` | String(500) | Drug indication |
| `therapy_start` / `therapy_end` | DateTime | Treatment period |
| `dechallenge` / `rechallenge` | String(50) | Drug challenge results |
| `concomitant_drugs` | Text | Other medications |
| `medical_history` | Text | Patient history |
| `created_at` / `updated_at` | DateTime | Timestamps |

**Relationships:**
- `missing_fields` → MissingField (1:N, cascade delete)
- `followup_attempts` → FollowUpAttempt (1:N, cascade delete)
- `confidence_history` → CaseConfidenceHistory (1:N, cascade delete)
- `adaptive_sessions` → AdaptiveLoopSession (1:N, cascade delete)
- `documents` → CaseDocument (1:N, cascade delete)
- `lifecycle` → FollowUpLifecycle (1:1 via backref)

##### `MissingField` (table: `missing_fields`)

Tracks which fields are missing/unclear/inconsistent for a case.

| Column | Type | Purpose |
|---|---|---|
| `id` | UUID | PK |
| `case_id` | UUID | FK → ae_cases (CASCADE) |
| `field_name` | String(100) | Which field is missing |
| `field_category` | String(50) | PATIENT / EVENT / DRUG / REPORTER |
| `is_missing` / `is_unclear` / `is_inconsistent` | Boolean | Issue type flags |
| `safety_criticality` | String(20) | CRITICAL / HIGH / MEDIUM / LOW |
| `regulatory_requirement` | Boolean | Required by regulation? |
| `should_follow_up` | Boolean | Should we ask about this? |
| `followup_priority` | Integer | Priority rank |
| `question_value_score` | Float | RL-enhanced value score |
| `impact_explanation` | Text | Why this matters |

##### `FollowUpAttempt` (table: `followup_attempts`)

Records each follow-up communication sent to a reporter.

| Column | Type | Purpose |
|---|---|---|
| `attempt_id` | UUID | PK |
| `case_id` | UUID | FK → ae_cases |
| `decision_id` | UUID | FK → followup_decisions |
| `iteration_number` / `attempt_number` | Integer | Tracking counters |
| `safety_confidence` / `data_completeness` | Float | Scores at time of attempt |
| `risk_score` / `response_probability` | Float | Predicted values |
| `questions_sent` | JSON | Questions included |
| `channel` | String(50) | EMAIL / WHATSAPP / PHONE |
| `sent_to` | String(255) | Recipient address |
| `secure_token` | String(500) | Unique token for response portal |
| `decision` | String(50) | PROCEED / ESCALATE / DEFER / SKIP |
| `response_status` | String(50) | SENT / PENDING / RESPONDED / FAILED |
| `response_received` | Boolean | Got a response? |
| `response_data` | JSON | The response content |
| `status` | String(50) | Overall attempt status |

##### `FollowUpResponse` (table: `followup_responses`)

Individual question-level responses from reporters.

| Column | Type | Purpose |
|---|---|---|
| `response_id` | UUID | PK |
| `attempt_id` | UUID | FK → followup_attempts (CASCADE) |
| `case_id` | UUID | FK → ae_cases (CASCADE) |
| `field_name` | String(100) | Which field was answered |
| `response_text` | Text | Raw response text |
| `field_value` | Text | Extracted structured value |
| `ai_extracted_value` | Text | AI-parsed value |
| `extraction_confidence` | Float | Extraction confidence |
| `is_complete` / `is_validated` | Boolean | Quality flags |

##### `User` (table: `users`)

| Column | Type | Purpose |
|---|---|---|
| `user_id` | UUID | PK |
| `email` | String(255) | Unique, indexed |
| `username` | String(100) | Unique |
| `password_hash` | String(500) | Argon2 hash |
| `role` | String(50) | PV_SPECIALIST / SAFETY_OFFICER / ADMIN |
| `failed_login_attempts` | Integer | Lockout counter (max 5) |
| `is_active` | Boolean | Account status |
| `last_login` | DateTime | Last successful login |

##### `SafetySignal` (table: `safety_signals`)

Drug-event pair signal detection results.

| Column | Type | Purpose |
|---|---|---|
| `signal_id` | UUID | PK |
| `drug_name` | String(500) | Drug involved |
| `adverse_event` | String(1000) | Event type |
| `signal_type` | String(50) | CONFIRMED / EMERGING / DISMISSED |
| `case_count` | Integer | Number of cases |
| `proportional_reporting_ratio` | Float | PRR value |
| `signal_strength` | String(20) | STRONG / MODERATE / WEAK / MINIMAL |
| `risk_priority` | String(20) | CRITICAL / HIGH / MEDIUM / LOW |
| `trend` | String(20) | UP / DOWN / STABLE |

##### `FollowUpLifecycle` (table: `followup_lifecycle`)

Per-case lifecycle state tracking with regulatory deadline management.

| Column | Type | Purpose |
|---|---|---|
| `lifecycle_id` | UUID | PK |
| `case_id` | UUID | FK → ae_cases, **unique** |
| `reporter_type` | String(20) | HCP / NON_HCP |
| `attempt_count` / `max_attempts` | Integer | Progress tracking |
| `response_status` | String(20) | pending / partial / complete |
| `escalation_status` | String(50) | none / flagged / escalated_to_reviewer / escalated_to_medical |
| `seriousness_level` | String(20) | LOW / MEDIUM / HIGH / CRITICAL |
| `regulatory_deadline` | DateTime | 7 or 15-day deadline |
| `days_remaining` | Integer | Days until deadline |
| `completeness_score` / `safety_confidence_score` | Float | Current metrics |
| `dead_case_flag` | Boolean | No-response dead case |
| `lifecycle_status` | String(30) | active / awaiting_response / escalated / completed / dead_case / closed |

##### `PVAuditTrail` (table: `pv_audit_trail`)

Immutable, append-only audit log for FDA 21 CFR Part 11 compliance.

| Column | Type | Purpose |
|---|---|---|
| `audit_id` | UUID | PK |
| `case_id` | UUID | Indexed |
| `timestamp` | DateTime | Indexed |
| `actor_type` | String(20) | AI / HUMAN / SYSTEM / REPORTER |
| `action_type` | String(100) | Indexed (CASE_CREATED, AI_RISK_DECISION, etc.) |
| `previous_value` / `new_value` | JSON | Before/after state |
| `decision_metadata` | JSON | AI decision details |
| `confidence_score` | Float | AI confidence at time of action |
| `description` | Text | Human-readable description |

**Composite Indexes:** `(case_id, action_type)`, `(case_id, timestamp)`, `(actor_type, timestamp)`, `(signal_id, action_type)`

##### Other Models

| Model | Table | Purpose |
|---|---|---|
| `FollowUpDecision` | `followup_decisions` | AI follow-up decision records |
| `FieldUpdateHistory` | `field_update_history` | Case field change tracking |
| `CaseConfidenceHistory` | `case_confidence_history` | Confidence score over time |
| `AdaptiveLoopSession` | `adaptive_loop_sessions` | Convergence loop sessions |
| `CaseDocument` | `case_documents` | Per-case uploaded documents (CIOMS, TAFU, PREGNANCY, REVIEWER_NOTE, RESPONSE) |
| `RepoDocument` | `repo_documents` | Global document repository (JSONB extracted questions) |
| `AuditLog` | `audit_logs` | General activity audit log |
| `RegulatoryWorkflow` | `regulatory_workflows` | Regulatory escalation workflows |
| `LifecycleAttempt` | `lifecycle_attempts` | Per-lifecycle follow-up attempts |
| `LifecycleAuditLog` | `lifecycle_audit_log` | Lifecycle-specific audit entries |
| `ReporterPolicy` | `reporter_policies` | Configurable reporter-type policies |

---

### 4.4 Authentication & Security

#### Password Hashing — Argon2

```python
from argon2 import PasswordHasher
ph = PasswordHasher()

# Hash
hash = ph.hash("password123")    # → "$argon2id$v=19$m=65536..."

# Verify
ph.verify(hash, "password123")   # → True or raises VerifyMismatchError
```

**Why Argon2 over bcrypt?** No 72-byte password truncation limit, winner of the Password Hashing Competition (PHC), memory-hard (resists GPU attacks).

#### JWT Tokens

| Token | Algorithm | Expiry | Content |
|---|---|---|---|
| **Access Token** | HS256 | 60 minutes | `sub: user_email`, `exp: timestamp` |
| **Refresh Token** | HS256 | 7 days | `sub: user_email`, `exp: timestamp` |

```python
# Token creation
def create_access_token(data: dict, expires_delta=None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=60))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
```

#### Auth Flow

```
Client                          Backend
  │                               │
  │ POST /api/auth/login          │
  │ {email, password}             │
  │──────────────────────────────►│
  │                               │── Check rate limit (10/min)
  │                               │── Check account lockout (5 attempts max)
  │                               │── Verify Argon2 hash
  │                               │── Reset failed_login_attempts
  │                               │── Update last_login
  │                               │── Log security event
  │  {access_token, refresh_token}│
  │◄──────────────────────────────│
  │                               │
  │ GET /api/cases                │
  │ Authorization: Bearer <token> │
  │──────────────────────────────►│
  │                               │── Decode JWT
  │                               │── Lookup user by email
  │                               │── Check is_active
  │                               │── Return data
  │◄──────────────────────────────│
```

#### RBAC (Role-Based Access Control)

```python
# In route definitions:
@router.get("/admin-only")
async def admin_endpoint(user = Depends(require_role("ADMIN"))):
    ...

@router.post("/approve")
async def approve(user = Depends(require_permission("approve_high_risk"))):
    ...
```

**Three roles:** `PV_SPECIALIST`, `SAFETY_OFFICER`, `ADMIN`

#### Account Lockout

```python
MAX_FAILED_ATTEMPTS = 5

# On login failure:
user.failed_login_attempts += 1
if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
    # Account locked — requires admin intervention
    logger.warning(f"SECURITY: Account LOCKED | email={email}")
    raise HTTPException(403, "Account locked due to too many failed attempts")
```

#### Input Validation (Pydantic)

```python
class UserCreate(UserBase):
    password: str

    @field_validator("password")
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r'[A-Z]', v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r'[a-z]', v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r'\d', v):
            raise ValueError("Password must contain at least one digit")
        return v

    @field_validator("role")
    def validate_role(cls, v):
        v = v.upper() if isinstance(v, str) else v   # Case-insensitive
        if v not in {"PV_SPECIALIST", "SAFETY_OFFICER", "ADMIN"}:
            raise ValueError("Invalid role")
        return v
```

---

### 4.5 API Routes (21 Routers)

| # | Router | Prefix | Auth | Purpose |
|---|---|---|---|---|
| 1 | `auth` | `/api/auth` | Public (rate-limited) | Login, register, profile |
| 2 | `pdf_upload` | `/api/cases` | ✅ | CIOMS PDF upload |
| 3 | `case_documents` | `/api/cases` | ✅ | Per-case document management |
| 4 | `cioms_combined` | `/api/cases` | ✅ | Combined CIOMS question send |
| 5 | `repo_documents` | `/api/repo-documents` | ✅ | Global document repository CRUD |
| 6 | `cases` | `/api/cases` | ✅ | Case CRUD, analysis, reviewer questions |
| 7 | `followups` | `/api/followups` | ✅ | Follow-up attempts & responses |
| 8 | `reporter_portal` | `/api/reporter-portal` | ✅ | Reporter response submission |
| 9 | `signals` | `/api/signals` | ✅ | Safety signal CRUD |
| 10 | `analytics` | `/api/analytics` | ✅ | Dashboard metrics |
| 11 | `admin` | `/api/admin` | ✅ | Admin operations |
| 12 | `governance` | `/api/governance` | ✅ | Trust, privacy, human oversight |
| 13 | `lifecycle` | `/api` | ✅ | Lifecycle state machine |
| 14 | `regulatory` | `/api/regulatory` | ✅ | Regulatory workflow |
| 15 | `pv_audit` | `/api/audit` | ✅ | PV audit trail (21 CFR Part 11) |
| 16 | `twilio_webhooks` | `/api` | Public (webhook) | Twilio SMS/WhatsApp callbacks |
| 17 | `voice` | `/api/voice` | Public (webhook) | Twilio Voice TwiML |
| 18 | `whatsapp` | `/api/whatsapp` | Public (webhook) | WhatsApp message handling |
| 19 | `email_webhooks` | `/api` | Public (webhook) | Email response processing |
| 20 | `followup_agent` | `/api` | Public | Conversational follow-up portal |
| 21 | `reviewer` | `/api/review` | ✅ | Reviewer dashboard |

> **Router mounting order matters:** `pdf_upload`, `case_documents`, and `cioms_combined` are mounted **before** `cases` to prevent the `/{case_id}` catch-all from intercepting their routes.

#### Key Case Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `GET /api/cases/` | GET | List cases (pagination + filters: status, risk_level, drug, event) |
| `GET /api/cases/by-primaryid/{id}` | GET | Fetch case by FAERS primary ID |
| `GET /api/cases/by-primaryid/{id}/analysis` | GET | Get cached analysis results |
| `POST /api/cases/by-primaryid/{id}/analyze` | POST | Trigger full AI pipeline |
| `POST /api/cases/{id}/save-reviewer-questions` | POST | Save reviewer questions |
| `POST /api/cases/{id}/attach-repo-docs` | POST | Attach repository documents |
| `POST /api/cases/{id}/analyze-and-send` | POST | Run AI analysis + send follow-up |
| `POST /api/cases/upload-pdf` | POST | Upload CIOMS PDF |

---

### 4.6 Pydantic Schemas

#### Token Response

```python
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int          # Seconds until expiry
    user: UserInDB           # Nested user info
```

#### User Schemas

```python
class UserBase(BaseModel):
    email: EmailStr
    username: str            # 3-50 chars, alphanumeric + _.-
    full_name: Optional[str]
    role: str = "PV_SPECIALIST"   # Validated against VALID_ROLES

class UserCreate(UserBase):
    password: str            # 8+ chars, 1 uppercase, 1 lowercase, 1 digit

class UserInDB(UserBase):
    user_id: UUID
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]
```

---

## 5. AI Agent Pipeline

### 5.1 Pipeline Architecture

The 7-agent pipeline processes each adverse event case through three connected features:

```
┌─────────────────────────── FEATURE 1: Risk & Medical ───────────────────────────┐
│                                                                                  │
│  ┌──────────────┐    ┌──────────────────┐    ┌──────────────────┐               │
│  │   Agent 1    │───►│     Agent 2      │───►│     Agent 3      │               │
│  │    Data      │    │    Medical       │    │      Risk        │               │
│  │ Completeness │    │   Reasoning      │    │   Assessment     │               │
│  │              │    │   (RAG+BioBERT)  │    │    (ML+NLP)      │               │
│  └──────────────┘    └──────────────────┘    └──────────────────┘               │
│  missing_fields       seriousness_hint        risk_score                         │
│  completeness_score   critical_fields         risk_category                      │
│                       urgency_level           confidence_score                   │
└─────────────────────────────────────┬────────────────────────────────────────────┘
                                      │ Feeds into
                                      ▼
┌─────────────────────────── FEATURE 2: Strategy & Follow-Up ─────────────────────┐
│                                                                                  │
│  ┌──────────────────┐    ┌──────────────────┐                                   │
│  │     Agent 4      │───►│     Agent 5      │                                   │
│  │    Response      │    │    Escalation    │                                   │
│  │    Strategy      │    │      Logic       │                                   │
│  │  (ML+Adaptive)   │    │   (Rules+LLM)    │                                   │
│  └──────────────────┘    └──────────────────┘                                   │
│  response_probability     decision: PROCEED/ESCALATE/DEFER/SKIP                 │
│  optimal_timing           reasoning_text                                         │
│  engagement_priority      stop_followup_flag                                     │
└─────────────────────────────────────┬────────────────────────────────────────────┘
                                      │ If stop_followup == False
                                      ▼
┌─────────────────────────── FEATURE 3: Adaptive Questioning ─────────────────────┐
│                                                                                  │
│  ┌──────────────────┐    ┌──────────────────┐                                   │
│  │     Agent 6      │───►│     Agent 7      │                                   │
│  │    Question      │    │    Follow-Up     │                                   │
│  │   Generation     │    │  Orchestration   │                                   │
│  │   (RL Scoring)   │    │   (Channel+      │                                   │
│  │                  │    │    Timing)        │                                   │
│  └──────────────────┘    └──────────────────┘                                   │
│  ranked_questions         recommended_channel                                    │
│  adaptive_scores          optimal_timing_hours                                   │
│  stop_reason              final_output                                           │
└─────────────────────────────────────┬────────────────────────────────────────────┘
                                      │
                                      ▼
                        ┌──────────────────┐
                        │    Finalize      │
                        │   Weighted       │
                        │   Confidence     │
                        └──────────────────┘
                        final_confidence (weighted avg of all agents)
```

#### Graph State (`SmartFUState`)

The pipeline uses a TypedDict with ~40 fields that flows through all agents:

```python
class SmartFUState(TypedDict):
    # Core case data
    primaryid: int
    patient_age: Optional[int]
    patient_sex: Optional[str]
    suspect_drug: str
    adverse_event: str
    # ... (20+ case fields)

    # Memory
    decision_history: List
    reporter_history: Dict
    pattern_memory: Dict

    # Agent outputs (populated sequentially)
    missing_fields: List[Dict]
    completeness_score: float
    medical_seriousness_hint: str
    risk_score: float
    risk_category: str
    response_probability: float
    engagement_risk_priority: str
    escalation_decision: str
    escalation_reasoning: str
    stop_followup_flag: bool
    questions: List[Dict]
    recommended_channel: str
    optimal_timing_hours: int
    # ... (per-agent confidence scores)
```

---

### 5.2 Agent 1 — Data Completeness

**File:** `services/data_completeness.py`
**Type:** Deterministic (no LLM)

Checks 12 pharmacovigilance fields against the case data and computes a weighted completeness score.

#### Field Weights & Criticality

| Field | Category | Criticality | Weight |
|---|---|---|---|
| `patient_age` | Patient Demographics | CRITICAL | 10 |
| `patient_sex` | Patient Demographics | HIGH | 7 |
| `event_date` | Event Details | CRITICAL | 10 |
| `event_outcome` | Event Details | CRITICAL | 10 |
| `adverse_event` | Event Details | CRITICAL | 10 |
| `suspect_drug` | Drug Information | CRITICAL | 10 |
| `drug_dose` | Drug Information | CRITICAL | 9 |
| `drug_route` | Drug Information | HIGH | 7 |
| `patient_initials` | Patient Demographics | CRITICAL | 10 |
| `reporter_type` | Reporter Information | HIGH | 8 |
| `reporter_country` | Reporter Information | LOW | 3 |
| `receipt_date` | Administrative | MEDIUM | 5 |

**Total possible weight:** 99

#### Completeness Formula

$$\text{completeness\_score} = \frac{\sum_{f \in \text{present}} w_f}{\sum_{f \in \text{all}} w_f}$$

A field is "missing" if: `None`, empty string, whitespace-only, or matches placeholders (`MISSING`, `UNK`, `N/A`, `Unknown`, `Not reported`, etc.), or `patient_age == 0`.

#### Completeness Cap by Follow-Up Status

| Follow-Up State | Max Completeness |
|---|---|
| No follow-ups sent | 0.85 |
| Follow-up pending | 0.70 |
| No response received | 0.60 |
| All responses received | 1.00 (uncapped) |

---

### 5.3 Agent 2 — Medical Reasoning (RAG)

**File:** `agents/medical_reasoning_agent.py`
**Type:** RAG (Retrieval-Augmented Generation) — no hardcoded rules

Uses a FAISS vector index over FDA labels, MedDRA terminology, and WHO guidelines to assess medical seriousness.

#### RAG Pipeline

```
Query (adverse_event + case context)
    │
    ▼
┌────────────────────┐
│ Synonym Expansion  │ "anaphylactic shock" → + "anaphylaxis" + "severe allergic reaction"
└────────┬───────────┘
         ▼
┌────────────────────┐
│ BioBERT Embedding  │ pritamdeka/BioBERT-mnli-snli-scinli-scitail-mednli-stsb
│ (fallback: MiniLM) │ → 384D vector
└────────┬───────────┘
         ▼
┌────────────────────┐
│ FAISS Search       │ top_k=10 candidates from knowledge_base/faiss_index.bin
└────────┬───────────┘
         ▼
┌────────────────────┐
│ Cross-Encoder      │ cross-encoder/ms-marco-MiniLM-L-6-v2
│ Reranking          │ Score = 70% rerank + 30% original FAISS score
└────────┬───────────┘
         ▼
    Top 5 documents → Weighted seriousness voting → Confidence calculation
```

#### Confidence Calculation

$$\text{confidence} = \min(0.98, \; \text{top\_score} \times 0.6 + \text{consensus\_factor} \times 0.4)$$

Where `consensus_factor` = ratio of documents agreeing on the seriousness level.

#### Output

```python
{
    "medical_seriousness_hint": "SERIOUS",    # SERIOUS / NOT_SERIOUS / UNKNOWN
    "critical_followup_fields": ["event_outcome", "dechallenge"],
    "reasoning_text": "Based on 5 matched knowledge sources...",
    "confidence_score": 0.82,
    "matched_categories": ["hepatotoxicity", "drug-induced liver injury"],
    "regulatory_implication": "Expedited reporting required",
    "followup_urgency": "HIGH",
    "knowledge_sources": ["FDA Drug Labels", "MedDRA SOC"]
}
```

---

### 5.4 Agent 3 — Risk Assessment (ML)

**File:** `agents/risk_assessment_agent.py`
**Type:** Machine Learning (Logistic Regression + NLP Embeddings)

Uses a trained classifier on FAERS data to predict adverse event seriousness.

#### Feature Engineering (~795 dimensions)

| Feature | Dimensions | Method |
|---|---|---|
| Adverse event text | 384 | SentenceTransformer (MiniLM-L6-v2) embedding |
| Suspect drug text | 384 | SentenceTransformer (MiniLM-L6-v2) embedding |
| Patient age | 1 | StandardScaler normalized |
| Drug route | 21 | One-hot (top 20 routes + "Other") |
| Reporter type | 5 | One-hot (CN, HP, MD, LW, PH) |

**Total:** ~795 features

#### Model Training

```python
# Data: All AECase records from PostgreSQL
# Split: 80/20 stratified train-test
# Model: LogisticRegression(class_weight='balanced', max_iter=1000)
# Metrics: Classification report + ROC-AUC
# Persistence: joblib → models/ directory
```

#### Risk Classification

| Probability | Category |
|---|---|
| > 0.7 | **HIGH** |
| > 0.3 | **MEDIUM** |
| ≤ 0.3 | **LOW** |

#### Semantic Risk Engine (Fallback)

When the ML model is unavailable, a `SemanticRiskEngine` computes cosine similarity against 21 serious event embeddings and 7 medium event embeddings:

| Similarity Score | Risk |
|---|---|
| ≥ 0.6 | HIGH |
| ≥ 0.4 | MEDIUM |
| < 0.4 | LOW |

---

### 5.5 Agent 4 — Response Strategy

**Type:** ML + Adaptive

Predicts the probability that a reporter will respond to a follow-up request, and adapts the engagement strategy accordingly.

- Calls `predict_response()` → response probability estimation
- Calls `adapt_engagement_risk()` → adjusts engagement priority based on response prediction
- Sets: `response_probability`, `optimal_timing`, `engagement_risk_priority`, `engagement_frequency`

---

### 5.6 Agent 5 — Escalation Logic

**Type:** Rule-based + LLM

Decision tree that determines whether to proceed with follow-up or escalate:

| Decision | When |
|---|---|
| **ESCALATE** | Risk ≥ 0.8 OR (risk ≥ 0.6 AND completeness < 0.5) |
| **PROCEED** | Moderate risk, acceptable completeness |
| **DEFER** | Low-risk cases needing more data |
| **SKIP** | Very low risk, high completeness |

**Safety Overrides (cannot be bypassed):**
- Cannot SKIP or DEFER when seriousness = HIGH and confidence < 0.7
- Cannot stop follow-up when critical fields are missing

Uses **Mistral LLM** to generate human-readable reasoning text for the decision.

---

### 5.7 Agent 6 — Question Generation (RL)

**File:** `services/question_scoring.py`
**Type:** Deterministic + Reinforcement Learning

Scores, ranks, and selects follow-up questions using a hybrid approach.

#### Base Scoring Formula

$$\text{value} = \text{criticality\_weight} \times \text{risk\_weight} \times \text{urgency\_factor}$$

Where:
- `criticality_weight`: CRITICAL=1.0, HIGH=0.75, MEDIUM=0.5, LOW=0.25
- `risk_weight`: risk ≥0.8 → 1.0, risk ≥0.4 → 0.7, else → 0.4
- `urgency_factor`: $1.0 - \text{completeness} \times 0.3$

#### Enhanced RL Scoring Formula

$$\text{final} = \text{heuristic} + 0.2 \times \text{learned\_reward} - 0.5 \times \text{constraint\_penalty} - 0.3 \times \text{duplicate\_penalty}$$

| Component | Purpose |
|---|---|
| `learned_reward` | Average reward from RL state (persisted in `question_rl_state.json`) |
| `constraint_penalty` | Penalizes non-critical fields in high-risk/tight-deadline scenarios |
| `duplicate_penalty` | -0.3 boost for unanswered re-asks, +1.0 penalty for already-answered |
| `deadline_weighting` | +20% boost for regulatory-critical fields when deadline < 3 days |

#### RL Feedback Loop

```python
def update_rl_feedback(field_name, answered, completeness_increase, is_critical):
    if answered:
        reward += 2
        if completeness_increase > 0.20: reward += 3
        if is_critical: reward += 5
    else:
        reward -= 1
        if not is_critical: reward -= 2
    # Persists to models/question_rl_state.json
```

#### Question Selection Rules

1. **Always include:** All CRITICAL fields
2. **Include if completeness < 0.85:** HIGH fields
3. **Include only if no CRITICAL/HIGH:** MEDIUM fields
4. **Include only if no CRITICAL/HIGH/MEDIUM:** LOW fields
5. **Max questions per round:** 4 (configurable)

#### Adaptive Stopping Conditions

| Condition | Action |
|---|---|
| Completeness ≥ 0.85 AND no critical gaps | STOP |
| Decision = SKIP AND no critical missing | STOP |
| Low risk + completeness ≥ 0.70 | STOP |
| Medium risk + completeness ≥ 0.75 | STOP |

#### Question Text Generation

Uses **Mistral LLM** via `cioms_question_generator` to turn field names into natural-language PV questions. No generic fallback — returns `None` if LLM fails.

---

### 5.8 Agent 7 — Follow-Up Orchestration

Combines all previous agent outputs into a unified follow-up recommendation:

- Recommended channel (EMAIL / WHATSAPP / PHONE)
- Optimal timing (hours from now)
- Question list (ranked, with scores)
- Engagement priority
- Final decision summary

---

### 5.9 Final Confidence Aggregation

At the end of the pipeline, a weighted average produces the final confidence score:

| Agent | Weight |
|---|---|
| Risk Assessment | 20% |
| Medical Reasoning | 20% |
| Response Strategy | 25% |
| Escalation Logic | 20% |
| Question Generation | 10% |
| Follow-Up Orchestration | 5% |

$$\text{final\_confidence} = \sum_{i} w_i \times c_i$$

---

### 5.10 Connected Flow Orchestrator

The `UnifiedOrchestrator` enforces Feature-1 → Feature-2 → Feature-3 dependency order:

```python
class UnifiedOrchestrator:
    async def execute_connected_flow(state, context=None):
        context = CaseContext(...)

        # Feature 1: Data + Medical + Risk
        state = await execute_feature_1(state, context)

        # Feature 2: Response Strategy + Escalation
        state = await execute_feature_2(state, context)  # Validates Feature-1 completed

        # Feature 3: Questions + Orchestration (only if follow-up needed)
        if not state.get("stop_followup_flag"):
            state = await execute_feature_3(state, context)  # Blocks if Feature-2 incomplete

        return build_final_output(state, context)
```

**Safety guarantees:**
- Feature-2 cannot run until Feature-1 completes
- Feature-3 cannot run until Feature-2 completes
- Feature-3 is skipped entirely if `stop_followup_flag = True`
- Falls back to sequential `smartfu_agent()` on any failure

---

### 5.11 Adaptive Loop Engine

**File:** `agents/adaptive_loop.py`

Repeatedly runs the pipeline until safety confidence converges.

```
                    ┌────────────────────┐
                    │  Load case from DB │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
              ┌────►│  Run 7-agent       │
              │     │  pipeline          │
              │     └─────────┬──────────┘
              │               │
              │     ┌─────────▼──────────┐
              │     │  Calculate         │
              │     │  confidence        │
              │     └─────────┬──────────┘
              │               │
              │     ┌─────────▼──────────┐
              │  No │  Converged?        │
              │◄────│  (≥ 0.85 OR        │
              │     │   gain < 0.02 OR   │
              │     │   max iterations)  │
              │     └─────────┬──────────┘
              │               │ Yes
                    ┌─────────▼──────────┐
                    │  Return session    │
                    │  summary           │
                    └────────────────────┘
```

**Configuration:**
- `confidence_threshold`: 0.85 (default)
- `max_iterations`: 3
- `min_information_gain`: 0.02 (2% improvement threshold)

---

## 6. Core Services

### 6.1 CIOMS PDF Extraction

**File:** `services/cioms_extractor.py`

Extracts 24 structured fields from CIOMS Form-I PDFs using a two-tier pipeline.

#### Pipeline

```
PDF file
  │
  ▼ (pdfplumber)
Raw text (all pages concatenated)
  │
  ▼ (Mistral LLM — primary)
JSON extraction attempt
  │
  ├── Success → Validate → Return 24-field dict
  │
  └── Failure → Regex fallback
                  │
                  ▼
              Pattern matching for all 24 fields
                  │
                  ▼
              Validate → Return 24-field dict
```

#### 24 CIOMS Fields Extracted

| # | Field | Validation |
|---|---|---|
| 1 | `patient_initials` | String |
| 2 | `age` | Integer 0–150 |
| 3 | `sex` | Normalized to M/F |
| 4 | `country` | String |
| 5 | `reaction_description` | String |
| 6 | `reaction_onset` | Date (YYYY-MM-DD) |
| 7 | `seriousness` | String |
| 8 | `outcome` | String |
| 9 | `suspect_drug_name` | String |
| 10 | `dose` | String |
| 11 | `route` | String |
| 12 | `indication` | String |
| 13 | `therapy_start` | Date |
| 14 | `therapy_end` | Date |
| 15 | `therapy_duration` | Auto-computed from start/end |
| 16 | `dechallenge` | String |
| 17 | `rechallenge` | String |
| 18 | `concomitant_drugs` | String |
| 19 | `medical_history` | String |
| 20 | `report_source` | String |
| 21 | `report_type` | String |
| 22 | `reporter_email` | Validated (@ + .) |
| 23 | `reporter_phone` | String |
| 24 | `manufacturer_name` | String |

**LLM prompt design:** System prompt explicitly instructs to extract only stated values, never guess, return `null` for missing fields. Text truncated to 6000 chars for Mistral context window.

---

### 6.2 Combined Follow-Up Builder

**File:** `services/combined_followup.py`

Aggregates questions from 4 sources into a unified follow-up payload:

```
┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│  AI Missing      │   │  Reviewer Notes  │   │  TFU Mandatory   │   │  Checklist Docs  │
│  Field Questions │   │  (free-text →    │   │  (rule-based     │   │  (PDF extraction │
│  (completeness   │   │   Mistral LLM →  │   │   triggers)      │   │   via pdfplumber │
│   analysis)      │   │   structured PV  │   │                  │   │   + Mistral)     │
│                  │   │   questions)     │   │                  │   │                  │
└────────┬─────────┘   └────────┬─────────┘   └────────┬─────────┘   └────────┬─────────┘
         │                      │                      │                      │
         └──────────────────────┴──────────────────────┴──────────────────────┘
                                            │
                                  ┌─────────▼─────────┐
                                  │  Deduplicate by    │
                                  │  field_name        │
                                  │  Sort by priority  │
                                  └─────────┬─────────┘
                                            │
                                  ┌─────────▼─────────┐
                                  │  Unified follow-up │
                                  │  question list     │
                                  └───────────────────┘
```

---

### 6.3 Follow-Up Trigger (Multi-Channel)

**File:** `services/followup_trigger.py`

Dispatches follow-up requests across all available channels simultaneously.

#### Channel Availability Check

| Channel | Required Config |
|---|---|
| **Email** | SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD |
| **Phone** | TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN + non-localhost URL |
| **WhatsApp** | TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER + non-localhost |

#### Dispatch Flow

```python
# For each available channel:
attempt = FollowUpAttempt(
    case_id=case.case_id,
    decision_id=decision.decision_id,
    channel=channel,
    secure_token=generate_token(),    # Unique per attempt
    questions_sent=questions,
    status="PENDING"
)
db.add(attempt)

result = await _send_communication(channel, case, questions, token, attempt)
attempt.status = "SENT" if result["success"] else "FAILED"
```

#### Channel Selection (Deterministic Fallback)

| Condition | Preferred Channel |
|---|---|
| Decision = ESCALATE OR risk ≥ 0.8 | PHONE |
| Response probability ≥ 0.6 | EMAIL |
| Otherwise | WHATSAPP |

---

### 6.4 Communication Service

**File:** `services/communication_service.py`

#### Email (SMTP)

- Builds rich HTML emails with:
  - Questions sorted by priority (CRITICAL first)
  - Secure token link to follow-up portal (`/followup-agent?token=...`)
  - Multi-language subjects: English, Hindi, Spanish, French, German, Japanese, Chinese, Portuguese, Arabic
  - Re-follow-up detection (changes subject/intro for repeat requests)
  - PDF attachments (TAFU, Pregnancy forms)
- Sends via `smtplib.SMTP` with TLS

#### WhatsApp (Twilio)

- Sends first question via Twilio WhatsApp API
- Subsequent questions sent incrementally after each reply (webhook-driven)
- Alternative: sends secure link to conversational follow-up portal

#### Phone (Twilio Voice)

- Initiates outbound call via Twilio
- Points to TwiML URL that speaks questions aloud
- Records calls for compliance
- Used for HIGH-risk cases only

---

### 6.5 Signal Detection Service

**File:** `services/signal_service.py`

Detects drug-event safety signals using the **Proportional Reporting Ratio (PRR)**.

#### PRR Formula

$$PRR = \frac{a/b}{c/d}$$

Where:
- $a$ = cases with **this drug AND this event**
- $b$ = all cases with **this drug**
- $c$ = all cases with **this event**
- $d$ = **total cases** in the database

#### Signal Classification

| Strength | Criteria | Signal Type |
|---|---|---|
| **STRONG** | PRR ≥ 8.0 AND cases ≥ 5 | CONFIRMED |
| **MODERATE** | PRR ≥ 3.0 AND cases ≥ 3 | EMERGING |
| **WEAK** | PRR ≥ 2.0 | EMERGING |
| **MINIMAL** | Below thresholds | DISMISSED |

#### Trend Detection (7-day rolling window)

| Recent Cases Ratio | Trend |
|---|---|
| ≥ 30% of total | **UP** ↑ |
| ≤ 10% of total | **DOWN** ↓ |
| Otherwise | **STABLE** → |

#### Risk Priority Matrix

| PRR Strength + Trend | Priority |
|---|---|
| STRONG + UP | **CRITICAL** |
| STRONG + STABLE | **HIGH** |
| MODERATE + UP | **HIGH** |
| MODERATE + STABLE | **MEDIUM** |
| WEAK | **LOW** |

---

### 6.6 Explainability Builder

**File:** `services/explainability.py`

Generates deterministic, audit-ready explanations — **zero LLM calls**.

#### Output Structure

```python
{
    "explainability_version": "1.0.0",
    "deterministic": True,
    "llm_free": True,
    "generated_at": "2026-02-21T...",

    "decision_summary": {
        "decision": "PROCEED",
        "confidence_level": "HIGH",
        "primary_reasoning": "...",
        "regulatory_compliance": "..."
    },

    "contributing_factors": {
        "data_completeness": {"impact": "MODERATE", "weight": "40%"},
        "risk_severity": {"impact": "HIGH", "weight": "35%"},
        "reporter_engagement": {"impact": "LOW", "weight": "25%"}
    },

    "agent_trace": [
        {
            "agent": "DataCompleteness",
            "status": "completed",
            "regulatory_checkpoint": "ICH E2B(R3) data quality standards"
        },
        // ... (one entry per agent)
    ],

    "human_oversight": {
        "status": "MANDATORY_REVIEW",  // or RECOMMENDED or OPTIONAL
        "triggered_by": ["decision == ESCALATE", "risk_score >= 0.8"],
        "review_checklist": [...]
    }
}
```

#### Mandatory Review Triggers

| Condition | Oversight Level |
|---|---|
| Decision = ESCALATE | MANDATORY_REVIEW |
| Risk score ≥ 0.8 | MANDATORY_REVIEW |
| Confidence < 0.3 | MANDATORY_REVIEW |
| Otherwise | RECOMMENDED or OPTIONAL |

**Regulatory frameworks referenced:** GVP Module V/VI/IX, CIOMS, FDA 21 CFR 314.80, ICH E2B(R3).

---

### 6.7 Lifecycle Tracker

**File:** `services/lifecycle_tracker.py`

Manages the complete operational lifecycle per case.

#### Reporter Policies

| Setting | HCP Policy | Non-HCP Policy |
|---|---|---|
| Max attempts | 4 | 3 |
| Questions per round | 5 | 2 |
| Escalate after | 3 attempts | 2 attempts |
| Escalate to | Medical team | Supervisor |
| Auto dead-case | No | Yes |

**Reporter type mapping:** `MD`, `HP`, `PH`, `RPH`, `RN` → HCP; all others → Non-HCP.

#### Lifecycle State Machine

```
  ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
  │  ACTIVE  │────►│ AWAITING │────►│ESCALATED │────►│COMPLETED │     │DEAD_CASE │
  │  (init)  │     │ RESPONSE │     │          │     │          │     │          │
  └──────────┘     └──────────┘     └──────────┘     └──────────┘     └──────────┘
       │                │                                                   ▲
       │                │           24h reminder loop                       │
       │                ├──────────────────────┐                            │
       │                │                      │                            │
       │                │    ┌──────────┐      │   Max attempts + no response
       │                └───►│ REMINDER │──────┘────────────────────────────┘
       │                     │  SENT    │
       │                     └──────────┘
       │
       └─── Regulatory deadline tracking (7-day or 15-day)
```

#### Deadline Rules

| Seriousness | Deadline Type | Days |
|---|---|---|
| HIGH / CRITICAL | 7-day expedited | 7 |
| MEDIUM / LOW | 15-day standard | 15 |

#### Escalation Triggers

| Condition | Action |
|---|---|
| Max attempts reached | Escalate to supervisor/medical |
| Deadline ≤ 2 days remaining | Force escalation |
| High seriousness + no response after 2 attempts | Escalate |
| Deadline passed | Auto-escalate with urgency flag |

#### Dead Case Detection

| Condition | Result |
|---|---|
| Max attempts exceeded + no response | Dead case (Non-HCP) |
| Max attempts exceeded + no response + already escalated | Dead case (HCP) |

---

### 6.8 Audit Service

**File:** `services/audit_service.py`

Logs all AI decisions, human reviews, and overrides for regulatory compliance.

**Action types logged:**
- `CASE_CREATED`, `CIOMS_PARSED`, `CIOMS_EXTRACTED`
- `AI_RISK_DECISION`, `AI_ANALYSIS_COMPLETED`
- `FOLLOWUP_SENT`, `FOLLOWUP_RESPONSE_RECEIVED`
- `SIGNAL_DETECTED`, `SIGNAL_EVALUATED`
- `HUMAN_OVERRIDE`, `HUMAN_REVIEW`
- `LIFECYCLE_INITIALIZED`, `ESCALATION_TRIGGERED`
- `DEAD_CASE_MARKED`, `CASE_CLOSED`

Each entry captures: actor (AI/HUMAN/SYSTEM/REPORTER), before/after state, decision metadata, confidence score, model version, timestamp.

---

### 6.9 Case Service

**File:** `services/case_service.py`

Core business logic for case CRUD.

- **`create_case(case_data)`** — Creates AECase + identifies missing fields + calculates completeness + logs audit
- **`bulk_upload_csv(df)`** — Iterates DataFrame rows, maps CSV columns, creates cases
- **`_identify_missing_fields(case_data)`** — Checks 7 critical fields, creates MissingField records
- **`_calculate_completeness(case_data)`** — Simple ratio: present / total required fields

---

## 7. Frontend Deep Dive

### 7.1 Application Shell (`App.jsx`)

The root component provides:
- **React Router** with 22 routes
- **Authentication guard** — checks `localStorage` for `access_token` on every navigation
- **Navigation bar** with 7 main tabs + Admin dropdown (Audit Trail, Explainability)
- **CaseEventProvider** context wrapper for cross-component communication

#### Navigation Tabs

| Tab | Path | Icon |
|---|---|---|
| CIOMS Upload | `/cioms-upload` | Document upload |
| Case Repository | `/case-analysis` | Database |
| Follow-Up Tracker | `/followup-attempts` | Arrow path |
| Reviewer | `/reviewer` | Eye |
| Lifecycle | `/lifecycle` | Refresh cycle |
| Severity Monitor | `/signals` | Shield |
| Dashboard | `/dashboard` | Chart bars |

**Admin dropdown** (gear icon):
- Audit Trail → `/audit-trail`
- Explainability → `/explainability/:caseId`

---

### 7.2 Pages & Components

#### CIOMS Upload Page (`CiomsUploadPage.jsx`)

Primary entry point for case intake.

**Flow:**
1. User selects repository forms (checkboxes)
2. Optionally uploads new repo document inline
3. Toggles **Reviewer Mode** ON/OFF (persisted to `localStorage`)
4. Uploads CIOMS PDF → creates case → attaches repo docs
5. **AUTO mode:** Immediately triggers AI pipeline
6. **REVIEWER mode:** Skips auto-analysis, waits for reviewer
7. Shows result banner with case ID, template, confidence, missing fields

**16 state variables:** uploadResult, recentUploads, analyzing, analysisReady, analysisError, includeReviewer, repoDocs, selectedRepoIds, repoUploadFile/Name/Type/ing/Error, showRepoUpload

#### Case Analysis Page (`CaseAnalysis.jsx`)

Detailed single-case analysis with 6 tabs.

**Tabs:**

| Tab | Content |
|---|---|
| **Overview** | Case header, risk ring gauges, missing fields panel, lifecycle strip |
| **AI Decision** | Decision badge (PROCEED/ESCALATE/DEFER/SKIP), confidence scores, reasoning |
| **Follow-Up Strategy** | Channel recommendation, timing, response probability, question list |
| **Question Scoring** | Per-question RL scores, criticality badges, value breakdown |
| **Documents** | CIOMS, TAFU, Pregnancy forms, uploaded documents |
| **Reviewer Oversight** | Audit trail timeline, decision metadata, human oversight actions (only visible when Reviewer Mode is ON) |

**"No Analysis Yet" view:** When AI analysis hasn't run, shows:
- TFU mandatory questions (if any)
- Saved reviewer questions (if reviewer mode ON)
- Reviewer question textarea (if reviewer mode ON)
- "Analyze & Send" button

**Reviewer Mode**: Read from `localStorage('reviewerMode')` — controls visibility of the Reviewer Oversight tab and reviewer questions panel.

#### Dashboard (`Dashboard.jsx`)

KPI overview with:
- KPI strip: total cases, PDF uploads, serious cases, high-risk, pending follow-ups, escalated
- Status distribution donut chart
- Completeness bar chart
- Severity monitor preview (active/strong/emerging signals)
- High-risk cases table
- Inline PDF upload & redirect

#### Signals / Severity Monitor (`Signals.jsx`)

- Signal list with search/filter/sort
- Signal detail panel (PRR, case count, trend, seriousness ratio)
- PRR distribution bar chart + case volume chart
- Regulatory escalation workflow button
- 60-second auto-polling

#### Lifecycle Tracking (`LifecycleTracking.jsx`)

- 5-step visual timeline: Intake → Validation → Follow-Up → Medical Review → Closure
- Status strip: case ID, reporter type, stage, follow-up status, escalation, days remaining
- Activity log with chronological entries
- Policy cards (HCP vs Non-HCP rules)

#### Explainability (`Explainability.jsx`)

Full AI decision audit page showing:
1. Decision summary card
2. Contributing factors breakdown (40% data, 35% risk, 25% reporter)
3. Agent trace (expandable per agent)
4. Clinical context with reasoning text
5. Regulatory compliance checks
6. Inline audit log
7. Human oversight actions (review note modal, override decision modal)

#### Audit Trail (`AuditTrail.jsx`)

System-wide immutable audit browser:
- 17 action types with icons and colors
- 4 actor types (AI, HUMAN, SYSTEM, REPORTER) with color coding
- Filter by action type, actor type, text search
- Per-case audit search
- Statistics strip (total entries + breakdown)

#### Login (`Login.jsx`)

Simple email/password form with pre-filled test credentials. JWT token stored in `localStorage` on success.

---

### 7.3 API Client (`api.js`)

Centralized HTTP client with 45+ methods. All use `fetch()` with Bearer token from `localStorage`.

**Error handling:**
- HTTP 401 → clears token, redirects to `/login`
- Other errors → parses `detail` from JSON response body

**Key method categories:**

| Category | Count | Examples |
|---|---|---|
| Analytics | 1 | `getDashboardMetrics` |
| Cases | 6 | `getCaseAnalysis`, `analyzeCase`, `getCaseByPrimaryId` |
| Follow-ups | 6 | `getFollowUp`, `submitFollowUp`, `getNextQuestion` |
| Reviewer | 5 | `saveReviewerQuestions`, `analyzeAndSend`, `submitReviewerDecision` |
| Signals | 5 | `getActiveSignals`, `escalateSignal`, `reviewSignal` |
| Governance | 6 | `getCaseTrust`, `getCaseOversight`, `submitOversightAction` |
| Lifecycle | 12 | `initLifecycle`, `getLifecycleStatus`, `triggerEscalation`, etc. |
| CIOMS | 2 | `uploadCiomsPdf`, `listPdfUploads` |
| Audit | 5 | `getAuditTrail`, `getCaseAuditTrailPV`, `getAuditStats` |
| Repo Docs | 6 | `listRepoDocuments`, `uploadRepoDocument`, `attachRepoDocs` |

**Base URL:** Empty string — Vite dev proxy forwards `/api` to `localhost:8000`.

---

### 7.4 State Management

- **No Redux/Zustand** — pure React `useState` / `useEffect` throughout
- **Cross-component events:** `CaseEventContext` provides `emitCaseUpdate()` and `useCaseEventListener()` for inter-page data refresh
- **Reviewer mode:** Persisted in `localStorage('reviewerMode')`, read by both CiomsUploadPage and CaseAnalysis
- **Auth token:** Stored in `localStorage('access_token')`, read by `api.js` for every request

---

## 8. Data Flow — End to End

### Complete Case Processing Flow

```
Step 1: PDF Upload
─────────────────
  User uploads CIOMS PDF
    → POST /api/cases/upload-pdf
    → pdfplumber extracts text
    → Mistral LLM extracts 24 fields (regex fallback)
    → AECase created in DB with primaryid
    → MissingField records created
    → Data completeness score calculated
    → Audit: CASE_CREATED, CIOMS_PARSED

Step 2: Repository Documents (Optional)
────────────────────────────────────────
  User selects TAFU/Pregnancy forms from repo
    → POST /api/cases/{id}/attach-repo-docs
    → CaseDocument records created
    → Checklist questions extracted from PDFs

Step 3: Reviewer Questions (Optional — Reviewer Mode ON)
────────────────────────────────────────────────────────
  Reviewer adds free-text questions
    → POST /api/cases/{id}/save-reviewer-questions
    → Saved as CaseDocument (type: REVIEWER_NOTE)
    → Mistral LLM converts notes → structured PV questions

Step 4: AI Analysis Pipeline
─────────────────────────────
  Triggered by: auto (Step 1) or manual ("Analyze & Send")
    → POST /api/cases/by-primaryid/{id}/analyze
    → Agent 1: Data Completeness → missing_fields, completeness_score
    → Agent 2: Medical Reasoning (RAG) → seriousness_hint, critical_fields
    → Agent 3: Risk Assessment (ML) → risk_score, risk_category
    → Agent 4: Response Strategy → response_probability, timing
    → Agent 5: Escalation Logic → decision (PROCEED/ESCALATE/DEFER/SKIP)
    → Agent 6: Question Generation (RL) → ranked questions
    → Agent 7: Follow-Up Orchestration → channel, timing, final output
    → Final: Weighted confidence aggregation
    → Explainability builder generates explanation
    → Audit: AI_ANALYSIS_COMPLETED, AI_RISK_DECISION

Step 5: Follow-Up Dispatch
──────────────────────────
  If decision ≠ SKIP:
    → Combined follow-up builder merges 4 question sources
    → FollowUpDecision record created
    → For each available channel (EMAIL, WHATSAPP, PHONE):
        → FollowUpAttempt record created (unique secure_token)
        → Communication service sends follow-up
        → Status updated: SENT or FAILED
    → Audit: FOLLOWUP_SENT

Step 6: Response Collection
───────────────────────────
  Reporter responds via:
    → Email link → /followup-agent?token=... → conversational portal
    → WhatsApp reply → /api/twilio/whatsapp/webhook → incremental Q&A
    → Phone call → /api/voice/... → TwiML voice flow
  Response processed:
    → FollowUpResponse records created
    → Fields extracted (AI + validation)
    → Case fields updated
    → Audit: FOLLOWUP_RESPONSE_RECEIVED

Step 7: Lifecycle Management
────────────────────────────
  Continuous monitoring:
    → 24-hour compliance reminders
    → Deadline tracking (7/15-day)
    → Escalation triggers (max attempts, tight deadline, non-response)
    → Dead case detection (max attempts + no response)
    → Closure on target completeness (≥ 0.85)

Step 8: Signal Detection
────────────────────────
  On case create/update:
    → PRR calculated for drug-event pair
    → Signal classified: STRONG/MODERATE/WEAK/MINIMAL
    → Trend computed (7-day window)
    → Risk priority assigned
    → Audit: SIGNAL_DETECTED
```

---

## 9. Security Architecture

### Defense-in-Depth Layers

| Layer | Mechanism | Detail |
|---|---|---|
| **Transport** | HTTPS (deployment) | TLS encryption in production |
| **Authentication** | JWT Bearer tokens | HS256, 60-min expiry |
| **Password** | Argon2 hashing | Memory-hard, no truncation |
| **Authorization** | RBAC | 3 roles: PV_SPECIALIST, SAFETY_OFFICER, ADMIN |
| **Rate Limiting** | slowapi | 60/min global, 10/min login, 5/min register |
| **Account Protection** | Lockout after 5 failures | Requires admin intervention |
| **Input Validation** | Pydantic schemas | Password strength, role enum, username regex |
| **HTTP Headers** | 6 security headers | CSP, X-Frame-Options, etc. |
| **CORS** | Strict origins | Only localhost:3000/5173/3001/3002 |
| **Admin Protection** | Self-registration blocked | Cannot register as ADMIN |
| **Audit** | Immutable logging | FDA 21 CFR Part 11 compliant |
| **Security Events** | Structured logging | All auth events logged with IP |

### Security Event Logging

Every authentication-related event is logged:

```python
# Examples:
"SECURITY: Successful login | email=test@example.com | role=ADMIN | ip=127.0.0.1"
"SECURITY: Failed login attempt | email=test@example.com | ip=127.0.0.1"
"SECURITY: Account LOCKED | email=test@example.com | ip=127.0.0.1"
"SECURITY: ADMIN registration BLOCKED | email=hacker@evil.com | ip=192.168.1.1"
"SECURITY: New user registered | email=new@example.com | role=PV_SPECIALIST"
```

---

## 10. Configuration Reference

All settings are loaded from `.env` via Pydantic Settings.

### Required Environment Variables

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `DB_PASSWORD` | Database password |
| `SECRET_KEY` | JWT signing key |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `MISTRAL_API_KEY` | Mistral AI API key |

### Optional Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `ENVIRONMENT` | `development` | App environment |
| `DEBUG` | `True` | Debug mode |
| `LOG_LEVEL` | `INFO` | Logging level |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | JWT access token TTL |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | JWT refresh token TTL |
| `RATE_LIMIT_PER_MINUTE` | `60` | Global rate limit |
| `SMTP_HOST/PORT/USER/PASSWORD` | — | Email sending |
| `TWILIO_ACCOUNT_SID/AUTH_TOKEN` | — | SMS/Voice/WhatsApp |
| `TWILIO_FROM_NUMBER` | — | Twilio phone number |
| `TWILIO_WHATSAPP_NUMBER` | — | WhatsApp business number |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `ENABLE_AI_AGENTS` | — | Feature flag |
| `ENABLE_EMAIL_FOLLOWUPS` | — | Feature flag |
| `ENABLE_SMS_FOLLOWUPS` | — | Feature flag |
| `ENABLE_SIGNAL_DETECTION` | — | Feature flag |
| `MAX_UPLOAD_SIZE_MB` | `50` | Max PDF upload size |

---

## 11. Dependencies

### Backend (Python)

| Package | Version | Purpose |
|---|---|---|
| `fastapi` | 0.109.0 | Web framework |
| `uvicorn` | 0.27.0 | ASGI server |
| `sqlalchemy` | 2.0.25 | ORM |
| `alembic` | 1.13.1 | Migrations |
| `psycopg2-binary` | 2.9.9 | PostgreSQL driver |
| `pgvector` | 0.2.4 | Vector similarity extension |
| `pydantic` | 2.5.3 | Data validation |
| `pydantic-settings` | 2.1.0 | Environment config |
| `python-jose` | 3.3.0 | JWT encoding/decoding |
| `argon2-cffi` | 23.1.0 | Password hashing |
| `slowapi` | 0.1.9 | Rate limiting |
| `pandas` | 2.2.0 | Data processing |
| `numpy` | 1.26.3 | Numerical computing |
| `pdfplumber` | 0.10.3 | PDF text extraction |
| `scikit-learn` | 1.4.0 | ML classifiers |
| `xgboost` | 2.0.3 | Gradient boosting |
| `imbalanced-learn` | 0.12.0 | Class imbalance handling |
| `joblib` | 1.3.2 | Model serialization |
| `mistralai` | ≥0.4.0 | Mistral LLM API |
| `langchain` | 0.1.4 | LLM framework |
| `langchain-anthropic` | 0.1.0 | Anthropic integration |
| `langgraph` | 0.0.19 | Agent graph orchestration |
| `anthropic` | 0.18.1 | Anthropic API client |
| `sentence-transformers` | 2.2.2 | Text embeddings (MiniLM-L6-v2) |
| `faiss-cpu` | 1.7.4 | Vector similarity search |
| `twilio` | ≥8.0.0 | Voice/SMS/WhatsApp |
| `redis` | 5.0.1 | Caching |
| `httpx` | 0.26.0 | Async HTTP client |
| `aiohttp` | 3.9.1 | Async HTTP |
| `lxml` | 5.1.0 | XML/HTML parsing |
| `cryptography` | 42.0.0 | Crypto primitives |

### Frontend (JavaScript)

| Package | Version | Purpose |
|---|---|---|
| `react` | 18.2 | UI library |
| `react-dom` | 18.2 | DOM rendering |
| `react-router-dom` | 7.13 | Client-side routing |
| `vite` | 5.0 | Build tool / dev server |
| `tailwindcss` | 3.4 | Utility-first CSS |
| `recharts` | — | Charting library |
| `autoprefixer` | — | CSS vendor prefixes |
| `postcss` | — | CSS processing |

---

## 12. Glossary

| Term | Definition |
|---|---|
| **AE** | Adverse Event — any undesirable medical occurrence in a patient taking a pharmaceutical product |
| **CIOMS** | Council for International Organizations of Medical Sciences — standardized AE reporting form |
| **FAERS** | FDA Adverse Event Reporting System — US FDA's AE database |
| **PV** | Pharmacovigilance — science of monitoring drug safety |
| **PRR** | Proportional Reporting Ratio — disproportionality metric for signal detection |
| **MedDRA** | Medical Dictionary for Regulatory Activities — standardized medical terminology |
| **ICH E2B(R3)** | International Council for Harmonisation guideline for AE reporting |
| **GVP** | Good Pharmacovigilance Practices — EU regulatory framework |
| **21 CFR Part 11** | FDA regulation for electronic records and signatures |
| **TFU** | Triggered Follow-Up — automated follow-up based on case analysis |
| **HCP** | Healthcare Professional — doctors, nurses, pharmacists |
| **RAG** | Retrieval-Augmented Generation — combining search with LLM generation |
| **FAISS** | Facebook AI Similarity Search — vector similarity library |
| **BioBERT** | Biomedical domain-specific BERT language model |
| **RL** | Reinforcement Learning — learning from reward signals |
| **RBAC** | Role-Based Access Control |
| **JWT** | JSON Web Token — stateless authentication token |
| **Argon2** | Memory-hard password hashing algorithm (PHC winner) |
| **CSP** | Content Security Policy — HTTP header restricting resource loading |
| **CORS** | Cross-Origin Resource Sharing — HTTP header controlling cross-domain requests |
| **TwiML** | Twilio Markup Language — XML instructions for Twilio voice/SMS |

---

*Generated: 21 February 2026 | SmartFU v1.0.0*
