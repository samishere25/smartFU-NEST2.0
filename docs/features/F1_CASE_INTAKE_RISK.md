# Feature 1: Intelligent Case Intake & Risk Assessment

---

## Overview
SmartFU supports three methods of adverse event case intake, each with AI-powered data extraction and automatic risk assessment.

---

## 1.1 Multi-Source Case Intake

### Method 1: CSV Bulk Upload
- Upload FAERS-format CSV files containing 50+ adverse event cases
- `pandas` parses CSV → each row becomes an `AECase` record
- Batch insert into PostgreSQL with auto-generated `primaryid` and `case_id` (UUID)
- All cases appear on Dashboard immediately
- `intake_source` = `'CSV'`

**Endpoint**: `POST /api/cases/upload`

### Method 2: CIOMS Form-I PDF Upload
- Upload scanned or digital CIOMS Form-I (Council for International Organizations of Medical Sciences)
- AI extracts all 26 standard fields automatically
- `intake_source` = `'PDF'`

**Endpoint**: `POST /api/cases/upload-pdf`

### Method 3: Manual Entry
- Create individual cases through API
- `intake_source` = `'MANUAL'`

---

## 1.2 CIOMS PDF Extraction Pipeline

### Step-by-Step Process

```
PDF File Upload
      │
      ▼
┌─────────────────────────┐
│  pdfplumber.open(pdf)   │  ← Extract raw text from PDF
│  page.extract_text()    │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  Regex Pattern Matching │  ← Attempt structured extraction
│  26 CIOMS field patterns│
│  - Patient initials     │
│  - Drug name + dose     │
│  - Adverse event        │
│  - Therapy dates        │
│  - Reporter info        │
│  - Seriousness criteria │
└───────────┬─────────────┘
            │
            ▼ (Fields regex can't extract)
┌─────────────────────────┐
│  Mistral LLM Extraction │  ← Intelligent fallback
│  Prompt: "Extract these │
│  CIOMS fields from the  │
│  following text..."     │
│  Model: mistral-large   │
│  Temperature: 0.3       │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  Field Normalization     │
│  - Dates → ISO format   │
│  - Drug names → cleaned │
│  - Seriousness flags    │
│  - Age groups derived   │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  AECase Created         │
│  PostgreSQL INSERT      │
│  PV Audit Trail logged  │
│  (action: CASE_CREATED) │
│  (action: CIOMS_PARSED) │
│  (action: FIELDS_EXTRACTED) │
└─────────────────────────┘
```

### CIOMS Form-I Fields Extracted (26 fields)
| # | Field | Maps To | Type |
|---|---|---|---|
| 1 | Patient Initials | `patient_initials` | String |
| 2 | Patient Age | `patient_age` | Integer |
| 3 | Patient Sex | `patient_sex` | String |
| 4 | Patient Age Group | `patient_age_group` | String |
| 5 | Suspect Drug | `suspect_drug` | String |
| 6 | Drug Dose | `drug_dose` | String |
| 7 | Drug Route | `drug_route` | String |
| 8 | Indication | `indication` | String |
| 9 | Therapy Start Date | `therapy_start` | DateTime |
| 10 | Therapy End Date | `therapy_end` | DateTime |
| 11 | Therapy Duration | `therapy_duration` | Integer (days) |
| 12 | Adverse Event | `adverse_event` | String |
| 13 | Event Date | `event_date` | DateTime |
| 14 | Event Outcome | `event_outcome` | String |
| 15 | Dechallenge | `dechallenge` | String |
| 16 | Rechallenge | `rechallenge` | String |
| 17 | Concomitant Drugs | `concomitant_drugs` | Text |
| 18 | Medical History | `medical_history` | Text |
| 19 | Reporter Type | `reporter_type` | String |
| 20 | Reporter Country | `reporter_country` | String |
| 21 | Reporter Email | `reporter_email` | String |
| 22 | Reporter Phone | `reporter_phone` | String |
| 23 | Is Serious | `is_serious` | Boolean |
| 24 | Seriousness Score | `seriousness_score` | Float |
| 25 | Manufacturer | `manufacturer_name` | String |
| 26 | Report Type | `report_type` | String |

### CiomsExtractor Service
- **File**: `backend/app/services/cioms_extractor.py`
- Uses `pdfplumber 0.10.3` for text extraction
- Regex patterns for each CIOMS field section
- Mistral LLM fallback for unstructured PDFs
- Returns dict of all extracted fields + extraction confidence score

---

## 1.3 Data Completeness Agent (Agent 1)

### What It Does
Scans all 30+ case fields against ICH E2B requirements and classifies each missing field.

### Technical Details
- **File**: `backend/app/agents/graph.py` → `data_completeness_agent(state)`
- **Service**: `backend/app/services/data_completeness.py` → `DataCompletenessService`
- **Input**: `SmartFUState.case_data`
- **Output**: Updates `SmartFUState.missing_fields`

### Classification per Missing Field
| Attribute | Values | Purpose |
|---|---|---|
| `safety_criticality` | CRITICAL / HIGH / MEDIUM / LOW | How important for patient safety |
| `regulatory_requirement` | True / False | Is this mandatory for CIOMS Form-I? |
| `followup_priority` | Integer (1-10) | Question ordering priority |
| `question_value_score` | 0.0 - 1.0 | Information value score |
| `is_missing` | Boolean | Data absent |
| `is_unclear` | Boolean | Data present but ambiguous |
| `is_inconsistent` | Boolean | Data contradicts other fields |

### Regulatory Critical Fields (always flagged)
- `event_date` — When did the adverse event occur?
- `event_outcome` — What happened to the patient?
- `adverse_event` — What was the event?
- `suspect_drug` — Which drug caused it?
- `patient_age` — How old is the patient?
- `patient_sex` — Patient's sex?

### Records Created
- `MissingField` records in `missing_fields` table (one per field)
- PV audit entry: `FIELDS_EXTRACTED`

---

## 1.4 Medical Reasoning Agent (Agent 2) — RAG System

### What It Does
Uses Retrieval-Augmented Generation to reason about the case using biomedical knowledge.

### Technical Details
- **File**: `backend/app/agents/medical_reasoning_agent.py` (569 lines)
- **Classes**: `MedicalSynonymExpander`, `RAGRetriever` (Singleton), `MedicalReasoningAgent`

### RAG Pipeline (5 Steps)

```
Step 1: Query Expansion
  "aspirin bleeding" → "aspirin bleeding hemorrhage gastrointestinal"
  Using MedicalSynonymExpander (medical_synonyms.json)

Step 2: Embedding
  BioBERT model: pritamdeka/BioBERT-mnli-snli-scinli-scitail-mednli-stsb
  Fallback: all-MiniLM-L6-v2 (if BioBERT unavailable)
  Query → 384-dim vector

Step 3: FAISS Search
  faiss.read_index("knowledge_base/faiss_index.bin")
  Top-k=10 nearest neighbors retrieved
  Metadata from knowledge_base/metadata.pkl

Step 4: Cross-Encoder Reranking
  Model: cross-encoder/ms-marco-MiniLM-L-6-v2
  Weighted: 70% rerank score + 30% original FAISS score
  
Step 5: Response Generation
  Top 5 results aggregated
  Seriousness voting (weighted by similarity scores)
  Confidence = top_score × 0.6 + consensus_factor × 0.4
  Capped at 0.98
```

### Knowledge Sources
| Source | Content |
|---|---|
| FDA Safety Guidelines | Drug safety labels, black box warnings |
| MedDRA Terminology | Medical Dictionary for Regulatory Activities |
| WHO-UMC Criteria | Causality assessment (certain/probable/possible) |
| ICH E2A/E2B Standards | International harmonization guidelines |

### Output
```json
{
  "medical_seriousness_hint": "SERIOUS",
  "medical_critical_fields": ["event_outcome", "dechallenge"],
  "medical_reasoning_text": "Based on FDA guidelines...",
  "medical_confidence": 0.82,
  "medical_regulatory_implication": "7-day expedited report required",
  "medical_followup_urgency": "HIGH"
}
```

---

## 1.5 Risk Assessment Agent (Agent 3)

### What It Does
Classifies case risk level using semantic similarity and ML models.

### Technical Details
- **File**: `backend/app/agents/graph.py` → `SemanticRiskEngine` class
- **Model**: SentenceTransformer `all-MiniLM-L6-v2`

### Semantic Risk Engine

#### Training Data (Hardcoded Examples)
- **21 Serious Event Examples**: "death", "cardiac arrest", "anaphylactic shock", "hepatic failure", "renal failure", "respiratory failure", "seizure", "stroke", "pulmonary embolism", "sepsis", "stevens-johnson syndrome", "toxic epidermal necrolysis", etc.
- **7 Medium Event Examples**: "nausea", "dizziness", "headache", "rash", "fatigue", "insomnia", "constipation"

#### Scoring Process
```
1. Encode all examples at startup → cached embeddings
2. For each case:
   a. Encode adverse_event text → 384-dim vector
   b. Compute cosine similarity against all serious examples
   c. Compute cosine similarity against all medium examples
   d. Take max serious similarity score and max medium score
   e. Classification:
      - max_serious ≥ 0.6 → HIGH risk
      - max_serious ≥ 0.4 OR max_medium ≥ 0.6 → MEDIUM risk
      - else → LOW risk
3. Fallback: keyword matching if SentenceTransformer unavailable
```

### Output
```json
{
  "risk_score": 0.78,
  "risk_category": "HIGH",
  "risk_confidence": 0.85,
  "risk_reasoning": "Adverse event 'anaphylactic shock' has 0.92 similarity to known serious events"
}
```

---

## 1.6 ICH E2A Seriousness Criteria

The system evaluates all 6 ICH E2A criteria automatically:

| # | Criterion | Keywords Checked |
|---|---|---|
| 1 | Death | death, fatal, died |
| 2 | Life-threatening | life-threatening, life threatening |
| 3 | Hospitalization | hospitalisation, hospitalization, hospital |
| 4 | Disability | disability, incapacity, persistent |
| 5 | Congenital anomaly | congenital, birth defect, anomaly |
| 6 | Medically significant | medically significant, important medical event |

If any criterion matches → `is_serious = True` → triggers 7-day regulatory deadline (vs 15-day for non-serious).

---

## 1.7 Frontend — Dashboard Case Intake

### Dashboard (Dashboard.jsx, 452 lines)

**Row 1 — KPI Strip (5 cards)**:
- Total Cases
- PDF Uploads (% of total)
- Serious Cases (% of total)
- Open Follow-Ups
- Escalated Cases

**PDF Upload Section**:
- File input for CIOMS Form-I PDF
- "Upload & Create Case" button
- On success: shows template detected, extraction confidence
- Auto-redirects to newly created case

**Row 2 — Case Status Distribution**:
- Custom SVG donut chart (`MiniDonut`)
- Status badges: INITIAL_RECEIVED, PENDING_FOLLOWUP, FOLLOWUP_RECEIVED, ESCALATED, COMPLETE, FOLLOWUP_DECLINED

**Row 3 — Signals Monitor**:
- Active signals count, High PRR count, Emerging signals
- Signal list with drug name, event, PRR value, case count

**Row 4 — Completeness Before vs After**:
- Grouped bar chart (Recharts)
- Red bars = before follow-up, Green bars = after
- Shows average improvement percentages

---

*This document covers Feature 1. See F2_AI_AGENT_PIPELINE.md for the complete 7-agent pipeline deep dive.*
