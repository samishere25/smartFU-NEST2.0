# SmartFU — Project Overview
## Intelligent Pharmacovigilance Follow-Up System

---

## What is Pharmacovigilance?

Pharmacovigilance (PV) is the science of **detecting, assessing, understanding, and preventing adverse effects of medicines**. Every pharmaceutical company is legally required to:
- Collect adverse event (AE) reports from doctors, patients, and healthcare professionals
- Investigate each report for missing safety-critical data
- Send follow-up questionnaires to reporters to fill data gaps
- Submit complete reports to regulators (FDA, EMA, MHRA) within **7-15 day deadlines**
- Maintain an immutable audit trail of every action taken

**This is not optional** — it's mandated by law in every country. Failure to comply results in regulatory action, fines, and potential drug recalls.

---

## The Problem

When an adverse event is reported, the initial report is almost always **incomplete**. A doctor calls in saying _"My patient took Aspirin and had a bleeding event"_ — but the report is missing:
- When did the bleeding start? (onset date)
- Did the patient stop taking Aspirin? (dechallenge)
- What was the outcome? (recovered / not recovered / fatal)
- Was the patient on blood thinners? (concomitant medication)
- How old is the patient? (demographics)

### Current Industry Process (Manual)
1. PV Specialist manually reviews the case (15-30 min per case)
2. Drafts a follow-up letter with 15-20 questions (standardized checklist)
3. Sends via email/fax/mail
4. Waits for response (days to weeks)
5. Manually sends reminders every 24 hours
6. If no response after 3 attempts → escalates to supervisor
7. If still no response → marks as "dead case"
8. Manually logs every action in an audit trail
9. Updates the case with received data
10. Submits to regulators

### Problems with Manual Process
| Problem | Impact |
|---|---|
| **15-20 question checklists** | Reporters get fatigued, response rate drops to ~30% |
| **Inconsistent questions** | Different reviewers ask different questions for same case |
| **Missed reminders** | 24-hour compliance rule often violated |
| **No risk prioritization** | A mild rash gets same treatment as anaphylactic shock |
| **Slow turnaround** | Cases miss 7-day regulatory deadlines |
| **Manual audit trail** | Incomplete, error-prone, non-compliant |
| **No medical intelligence** | Questions not informed by drug-event knowledge |

---

## Our Solution: SmartFU

SmartFU replaces this entire manual process with an **AI-powered, end-to-end automation system**:

### Core Innovation: "5 Questions, Not 20"
Instead of dumping a 20-question checklist, SmartFU:
1. **Analyzes the case** using 7 specialized AI agents
2. **Determines risk level** using semantic similarity + ML models
3. **Generates only 3-5 targeted questions** based on what's actually missing
4. **Selects the optimal delivery channel** (email, phone, WhatsApp)
5. **Manages the entire lifecycle** — reminders, escalation, dead-case classification
6. **Maintains regulatory compliance** — immutable audit trail, field versioning

### Key Metrics
| Metric | Before SmartFU | After SmartFU |
|---|---|---|
| Questions per follow-up | 15-20 | 3-5 |
| Time to analyze a case | 15-30 min | < 10 seconds |
| Reminder compliance | ~60% | 100% (automated) |
| Audit trail completeness | ~70% | 100% (immutable) |
| Risk-based prioritization | None | Automatic (HIGH/MEDIUM/LOW) |
| Channel selection | Manual | AI-driven (risk-based) |

---

## Technology Stack Summary

| Layer | Technologies |
|---|---|
| **Frontend** | React 18.2, Tailwind CSS 3.4, Vite 5.0, Recharts 3.7 |
| **Backend** | Python 3.11, FastAPI 0.109, SQLAlchemy 2.0, Uvicorn 0.27 |
| **Database** | PostgreSQL 15 (pgvector), Redis 7 |
| **AI/ML** | Mistral AI, LangChain 0.1.4, LangGraph 0.0.19, BioBERT, FAISS 1.7.4, scikit-learn 1.4, XGBoost 2.0, SentenceTransformers 2.2 |
| **Communication** | Twilio (Voice + WhatsApp), SMTP Email |
| **Security** | Argon2, JWT HS256, Role-based Access Control |
| **DevOps** | Docker, Docker Compose |

---

## 8 Major Features

| # | Feature | What It Does |
|---|---|---|
| F1 | **Case Intake & Risk Assessment** | Multi-source intake (CSV/PDF/Manual) + AI risk scoring |
| F2 | **7-Agent AI Pipeline** | Sequential multi-agent analysis (LangGraph) |
| F3 | **Intelligent Question Generation** | TFU Decision Agent + 4-source merge + 5-question cap |
| F4 | **Multi-Channel Communication** | Email, Phone IVR, WhatsApp, Web Portal |
| F5 | **Lifecycle Management** | HCP/Non-HCP policies, reminders, escalation, dead-case |
| F6 | **Safety Signal Detection** | PRR calculation, trend analysis, regulatory workflow |
| F7 | **Compliance & Audit Trail** | Immutable PV audit, field versioning, FDA 21 CFR Part 11 |
| F8 | **Explainability & Governance** | Human-readable AI explanations, override controls |

---

## System Scale

| Component | Count |
|---|---|
| Database Tables | 19 |
| API Endpoints | 80+ |
| Frontend Pages | 14 |
| AI Agents | 7 (sequential pipeline) |
| Backend Services | 25+ |
| Supported Languages | 9 (en, hi, es, fr, de, ja, zh, pt, ar) |
| Communication Channels | 4 (Email, Phone, WhatsApp, Web Portal) |

---

## Regulatory Standards Implemented

| Standard | What It Covers | Our Implementation |
|---|---|---|
| **ICH E2A** | Seriousness criteria definitions | TFU Decision Agent evaluates all 6 ICH E2A criteria |
| **ICH E2B(R3)** | Data elements for AE transmission | Data Completeness Agent validates all required fields |
| **EMA GVP Module VI** | Follow-up best practices | 24h reminders, risk-based questioning, lifecycle management |
| **EMA GVP Module IX** | Signal management | PRR calculation, signal classification, regulatory workflow |
| **FDA 21 CFR Part 11** | Electronic records compliance | Immutable audit trail, field versioning, actor attribution |
| **MedDRA** | Medical terminology standard | Integrated in RAG knowledge base |
| **WHO-UMC** | Causality assessment | Medical reasoning agent uses WHO-UMC criteria |

---

*See individual feature documents in `docs/features/` for deep technical details.*
