# Feature 7: Compliance & Immutable Audit Trail

---

## Overview
SmartFU maintains a **regulatory-grade, append-only audit trail** that tracks every action on every case. This is designed for compliance with **FDA 21 CFR Part 11** (electronic records) and **EMA GVP Module I** (quality management). Every AI decision, human override, field change, and communication is permanently logged and timestamped.

---

## 7.1 Architecture

**File**: `backend/app/services/pv_audit_service.py` (441 lines)

```
┌─────────────────────────────────────────────────────────┐
│                    PVAuditService                         │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Principle: APPEND-ONLY                                  │
│  → Records are NEVER updated or deleted                  │
│  → Each action creates a NEW row                         │
│  → Complete history preserved forever                    │
│                                                          │
│  ┌─────────────┐  ┌─────────┐  ┌──────────────────┐    │
│  │ 17 Action   │  │ 4 Actor │  │ Composite        │    │
│  │ Types       │  │ Types   │  │ Indexes          │    │
│  └─────────────┘  └─────────┘  └──────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

---

## 7.2 Action Types (17)

| # | Action Constant | Category | Description |
|---|---|---|---|
| 1 | `CASE_CREATED` | Case | New AE case created |
| 2 | `CIOMS_PARSED` | Case | CIOMS form parsed and fields extracted |
| 3 | `FIELDS_EXTRACTED` | Case | Individual fields extracted from CIOMS |
| 4 | `AI_RISK_DECISION` | AI | Risk score and category determined |
| 5 | `AI_FOLLOWUP_DECISION` | AI | Follow-up decision (PROCEED/SKIP/DEFER/ESCALATE) |
| 6 | `HUMAN_OVERRIDE` | Governor | Human PV specialist overrides AI decision |
| 7 | `FOLLOWUP_SENT` | Communication | Follow-up questions sent via any channel |
| 8 | `RESPONSE_RECEIVED` | Communication | Reporter response received and processed |
| 9 | `REVIEWER_NOTE_ADDED` | Review | Reviewer adds notes or questions |
| 10 | `LIFECYCLE_STAGE_CHANGE` | Lifecycle | Lifecycle state transition |
| 11 | `CASE_CLOSED` | Case | Case marked as complete/closed |
| 12 | `SIGNAL_DETECTED` | Signal | Safety signal auto-detected by PRR |
| 13 | `SIGNAL_REVIEWED` | Signal | Signal reviewed by Safety Officer |
| 14 | `SIGNAL_PRIORITY_CHANGED` | Signal | Signal priority level changed |
| 15 | `SIGNAL_FALSE_POSITIVE` | Signal | Signal classified as false positive |
| 16 | `REGULATORY_ESCALATION` | Regulatory | Case escalated for regulatory submission |
| 17 | `REGULATORY_WORKFLOW_CREATED` | Regulatory | Regulatory submission workflow initiated |

---

## 7.3 Actor Types (4)

| Actor | Description | Examples |
|---|---|---|
| `SYSTEM` | Automated system actions | Case creation, CIOMS parsing, lifecycle transitions |
| `AI` | AI/ML model decisions | Risk scoring, follow-up decisions, question generation |
| `HUMAN` | Human users (PV specialists, reviewers) | Overrides, notes, signal reviews |
| `REPORTER` | External reporters (HCPs, patients) | Response submissions via portal/phone/email |

---

## 7.4 Database Model

### PVAuditTrail

```python
class PVAuditTrail(Base):
    __tablename__ = "pv_audit_trail"
    
    id: int                    # Primary key (auto-increment)
    case_id: int               # FK → ae_cases.id
    action: str                # One of 17 action types
    actor_type: str            # SYSTEM / AI / HUMAN / REPORTER
    actor_id: str              # User ID, system name, or reporter identifier
    details: JSON              # Action-specific metadata
    previous_value: JSON       # Value before change (for field updates)
    new_value: JSON            # Value after change
    regulatory_context: str    # Which regulation this relates to
    timestamp: datetime        # When the action occurred (UTC)
    created_at: datetime       # Record creation time
```

### Composite Indexes (Performance)

```python
# For fast case-history queries
Index("ix_pv_audit_case_time", "case_id", "timestamp")

# For action-type filtering
Index("ix_pv_audit_action", "action")

# For actor-based queries
Index("ix_pv_audit_actor", "actor_type", "actor_id")

# For regulatory compliance searches
Index("ix_pv_audit_regulatory", "case_id", "action", "regulatory_context")
```

These composite indexes ensure that even with millions of audit records, queries remain fast.

---

## 7.5 Audit Entry Examples

### AI Risk Decision
```json
{
    "case_id": 42,
    "action": "AI_RISK_DECISION",
    "actor_type": "AI",
    "actor_id": "SemanticRiskEngine_v2",
    "details": {
        "risk_score": 0.78,
        "risk_category": "HIGH",
        "risk_confidence": 0.85,
        "semantic_similarity": 0.72,
        "closest_match": "Stevens-Johnson syndrome",
        "method": "sentence_transformer",
        "model": "all-MiniLM-L6-v2"
    },
    "regulatory_context": "GVP Module IX - Signal Management",
    "timestamp": "2024-01-15T10:30:45Z"
}
```

### Human Override
```json
{
    "case_id": 42,
    "action": "HUMAN_OVERRIDE",
    "actor_type": "HUMAN",
    "actor_id": "user_15",
    "details": {
        "field": "decision",
        "override_reason": "Reporter is an oncologist - can provide critical tumor data",
        "ai_recommendation": "SKIP",
        "human_decision": "PROCEED"
    },
    "previous_value": {"decision": "SKIP"},
    "new_value": {"decision": "PROCEED"},
    "regulatory_context": "ICH E2A - Human Oversight Required",
    "timestamp": "2024-01-15T11:15:22Z"
}
```

### Follow-Up Sent
```json
{
    "case_id": 42,
    "action": "FOLLOWUP_SENT",
    "actor_type": "SYSTEM",
    "actor_id": "CommunicationService",
    "details": {
        "channel": "PHONE",
        "recipient": "+1234567890",
        "questions_count": 5,
        "question_sources": {
            "REVIEWER_QUESTION": 1,
            "TFU_MANDATORY": 2,
            "REPO_FORM": 1,
            "AI_GENERATED": 1
        },
        "attempt_number": 2,
        "language": "en",
        "lifecycle_status": "ACTIVE"
    },
    "regulatory_context": "EMA GVP Module VI - Follow-up",
    "timestamp": "2024-01-15T14:00:00Z"
}
```

### Response Received
```json
{
    "case_id": 42,
    "action": "RESPONSE_RECEIVED",
    "actor_type": "REPORTER",
    "actor_id": "dr.smith@hospital.com",
    "details": {
        "channel": "PORTAL",
        "questions_answered": 4,
        "questions_total": 5,
        "fields_updated": ["event_onset_date", "event_outcome", "dechallenge", "medical_history"],
        "completeness_before": 0.67,
        "completeness_after": 0.82
    },
    "regulatory_context": "EMA GVP Module VI - Data Collection",
    "timestamp": "2024-01-16T09:45:30Z"
}
```

---

## 7.6 Field Update History

Separate from the general audit trail, every individual field change is tracked:

### FieldUpdateHistory Model

```python
class FieldUpdateHistory(Base):
    __tablename__ = "field_update_history"
    
    id: int
    case_id: int               # FK → ae_cases.id
    field_name: str            # e.g., "event_onset_date"
    old_value: str             # Previous value
    new_value: str             # New value
    source: str                # REPORTER/AI/REVIEWER/CIOMS
    confidence: float          # Confidence in the update
    updated_by: str            # Who made the change
    updated_at: datetime
```

This enables:
- **Full version history** for any field
- **Change tracking** for regulatory audits
- **Conflict resolution** when multiple sources update the same field
- **Rollback capability** if needed

---

## 7.7 Additional Audit Models

### AuditLog (General)
```python
class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id: int
    user_id: int
    action: str
    resource_type: str
    resource_id: str
    details: JSON
    ip_address: str
    created_at: datetime
```

### CaseConfidenceHistory
```python
class CaseConfidenceHistory(Base):
    __tablename__ = "case_confidence_history"
    
    id: int
    case_id: int
    confidence_score: float
    completeness_score: float
    risk_score: float
    agent_confidences: JSON    # Per-agent breakdown
    recorded_at: datetime
```

---

## 7.8 Regulatory Compliance Mapping

| Regulation | What We Comply With | How |
|---|---|---|
| **FDA 21 CFR Part 11** | Electronic records must be trustworthy, reliable, equivalent to paper | Append-only records, timestamps, actor tracking |
| **FDA 21 CFR Part 11 §11.10(e)** | Audit trails for record changes | FieldUpdateHistory, PVAuditTrail with previous/new values |
| **EMA GVP Module I** | Quality management system | All actions logged with regulatory context |
| **EMA GVP Module VI** | Follow-up tracking | FOLLOWUP_SENT, RESPONSE_RECEIVED logged |
| **EMA GVP Module IX** | Signal management | SIGNAL_DETECTED through SIGNAL_FALSE_POSITIVE |
| **ICH E2B(R3)** | Structured AE reporting | CIOMS_PARSED, FIELDS_EXTRACTED with field-level detail |
| **ICH E2A** | Expedited safety reporting | AI_RISK_DECISION with regulatory deadlines |

---

## 7.9 Querying the Audit Trail

### API Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/audit/{case_id}` | GET | Full audit history for a case |
| `/api/audit/{case_id}/actions/{action}` | GET | Filter by action type |
| `/api/audit/{case_id}/timeline` | GET | Chronological timeline view |
| `/api/audit/field-history/{case_id}/{field}` | GET | History of a specific field |

### Common Queries

**"Show me all AI decisions that were overridden by humans"**
```sql
SELECT * FROM pv_audit_trail
WHERE action = 'HUMAN_OVERRIDE'
ORDER BY timestamp DESC;
```

**"Show me every change to the risk score for case 42"**
```sql
SELECT * FROM pv_audit_trail
WHERE case_id = 42 
  AND action = 'AI_RISK_DECISION'
ORDER BY timestamp ASC;
```

**"Show me the complete field history for event_outcome"**
```sql
SELECT * FROM field_update_history
WHERE case_id = 42 AND field_name = 'event_outcome'
ORDER BY updated_at ASC;
```

---

## 7.10 How to Explain to Judges

> "Pharmaceutical regulators can audit us at any time and ask, 'Why did your AI make this decision?' We have the answer — permanently. Every AI risk score, every human override, every field change, every communication sent and received — it's all in an append-only audit trail. We never delete or modify records. Each entry has a timestamp, an actor (AI, human, or system), and the regulatory context. We even track before-and-after values for every field update. This is how you build trust in AI for a regulated industry."

---

*See F8_EXPLAINABILITY_GOVERNANCE.md for how we explain AI decisions to regulators and humans.*
