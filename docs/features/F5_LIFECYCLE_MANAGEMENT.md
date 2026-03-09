# Feature 5: Follow-Up Lifecycle Management

---

## Overview
SmartFU implements a **policy-driven lifecycle state machine** that manages follow-up campaigns from initiation to completion. It differentiates between **HCP (Healthcare Professional)** and **Non-HCP** reporters, applying different question limits, escalation thresholds, and deadlines. This is based on EMA GVP Module VI guidance.

---

## 5.1 Architecture

**File**: `backend/app/services/lifecycle_tracker.py` (904 lines)

```
┌──────────────────────────────────────────────────────┐
│              FollowUpLifecycleTracker                  │
│                                                       │
│  ┌─────────────┐     ┌─────────────────────────┐     │
│  │  Reporter    │────▶│  Policy Selection        │     │
│  │  Type Check  │     │  HCP_POLICY / NON_HCP   │     │
│  └─────────────┘     └────────────┬────────────┘     │
│                                    │                   │
│  ┌─────────────────────────────────▼────────────────┐ │
│  │           Lifecycle State Machine                  │ │
│  │                                                    │ │
│  │  INITIATED → ACTIVE → ESCALATED → COMPLETED      │ │
│  │                ↓                      ↓            │ │
│  │           STALLED              DEAD_LETTER         │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │         Regulatory Deadline Engine                  │ │
│  │  HIGH risk → 7-day deadline                        │ │
│  │  LOW risk  → 15-day deadline                       │ │
│  │  Target completeness → 0.85                        │ │
│  └────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

---

## 5.2 Reporter Policies

### ReporterPolicyConfig Dataclass

```python
@dataclass
class ReporterPolicyConfig:
    max_attempts: int             # Maximum follow-up rounds
    questions_per_round: int      # Max questions per round
    escalate_after: int           # Escalate after N failed rounds
    escalate_to: str              # Escalation target role
    auto_dead_letter: bool        # Auto close after max attempts?
```

### HCP Policy (Healthcare Professionals)

```python
HCP_POLICY = ReporterPolicyConfig(
    max_attempts=4,                # Up to 4 follow-up rounds
    questions_per_round=5,         # Up to 5 questions per round
    escalate_after=3,              # Escalate after 3 unanswered rounds
    escalate_to="medical_team",    # Escalate to Medical Team
    auto_dead_letter=False         # Do NOT auto-close (need manual review)
)
```

**HCP Types**: MD, HP, PH, HCP, RPH, RN (doctors, pharmacists, healthcare providers, registered nurses)

### Non-HCP Policy (Consumers/Patients)

```python
NON_HCP_POLICY = ReporterPolicyConfig(
    max_attempts=3,                # Only 3 follow-up rounds
    questions_per_round=2,         # Only 2 questions per round (simpler)
    escalate_after=2,              # Escalate after just 2 unanswered
    escalate_to="supervisor",      # Escalate to Supervisor
    auto_dead_letter=True          # Auto-close after max attempts
)
```

### Why Different?
- **HCPs** can provide detailed medical info → more questions allowed
- **Non-HCPs** (patients/consumers) → simpler language, fewer questions, quicker escalation
- Per EMA GVP Module VI, reporter qualification affects follow-up strategy

---

## 5.3 Lifecycle States

```
                    ┌──────────┐
                    │ INITIATED│  ← Case created, first follow-up pending
                    └────┬─────┘
                         │ First follow-up sent
                         ▼
                    ┌──────────┐
              ┌────│  ACTIVE   │────┐
              │    └────┬─────┘    │
              │         │          │ No response after
              │         │          │ multiple attempts
              │    Response        │
              │    received        ▼
              │         │    ┌──────────┐
              │         │    │ STALLED  │  ← No progress
              │         │    └────┬─────┘
              │         │         │ Escalation triggered
              │         │         ▼
              │         │    ┌──────────┐
              │         │    │ESCALATED │  ← Sent to supervisor/medical team
              │         │    └────┬─────┘
              │         │         │
              │         ▼         ▼
              │    ┌──────────────────┐
              ├───▶│    COMPLETED     │  ← All questions answered OR
              │    └──────────────────┘    completeness ≥ 0.85
              │
              │    ┌──────────────────┐
              └───▶│   DEAD_LETTER    │  ← Max attempts exceeded
                   └──────────────────┘    (Non-HCP only, auto)
```

### State Transitions

| Current State | Trigger | New State |
|---|---|---|
| INITIATED | First follow-up sent | ACTIVE |
| ACTIVE | All fields answered | COMPLETED |
| ACTIVE | Completeness ≥ 0.85 | COMPLETED |
| ACTIVE | No response × N rounds | STALLED |
| ACTIVE | Deadline passed + no response | STALLED |
| STALLED | Escalation triggered | ESCALATED |
| ESCALATED | Response finally received | ACTIVE |
| ESCALATED | Still no response | DEAD_LETTER |
| ACTIVE (Non-HCP) | max_attempts exceeded + auto_dead_letter=True | DEAD_LETTER |
| ACTIVE (HCP) | max_attempts exceeded + auto_dead_letter=False | STALLED (needs manual) |

---

## 5.4 Regulatory Deadlines

| Risk Level | Deadline | Regulatory Basis |
|---|---|---|
| HIGH (serious AEs) | **7 calendar days** | ICH E2A: Expedited safety reports |
| MEDIUM | **15 calendar days** | EMA GVP Module VI: Standard periodicity |
| LOW | **15 calendar days** | Standard follow-up window |

**Target Completeness Score**: `0.85` (85% of required fields filled)

### Deadline Urgency Calculation

```python
def _calculate_urgency(self, case, days_elapsed):
    if risk_category == "HIGH":
        deadline_days = 7
    else:
        deadline_days = 15
    
    days_remaining = deadline_days - days_elapsed
    
    if days_remaining <= 0:
        return "OVERDUE"
    elif days_remaining <= 3:
        return "CRITICAL"
    elif days_remaining <= 7:
        return "URGENT"
    else:
        return "NORMAL"
```

---

## 5.5 Core Methods (11 Operational)

| Method | Purpose |
|---|---|
| `initiate_lifecycle(case_id)` | Create lifecycle record, select policy |
| `record_attempt(case_id, channel, questions)` | Log a follow-up attempt |
| `record_response(case_id, responses)` | Process reporter response |
| `check_status(case_id)` | Get current lifecycle state + metrics |
| `_determine_next_action(case_id)` | AI-driven next step decision |
| `check_deadline_compliance(case_id)` | Check against regulatory deadline |
| `escalate(case_id, reason)` | Trigger escalation to supervisor/medical team |
| `close_lifecycle(case_id, outcome)` | Mark lifecycle complete |
| `_select_policy(reporter_type)` | Choose HCP or Non-HCP policy |
| `get_lifecycle_history(case_id)` | Full audit history |
| `_should_auto_dead_letter(case_id)` | Check if auto-close applies |

### _determine_next_action() — 8 Possible Actions

```python
def _determine_next_action(self, lifecycle, policy):
    """
    Returns one of:
    1. SEND_FOLLOWUP     → Send next round of questions
    2. WAIT_FOR_RESPONSE → Still waiting, not yet timed out
    3. ESCALATE          → Escalate to supervisor/medical team
    4. DEAD_LETTER       → Close case (Non-HCP auto)
    5. COMPLETE          → Sufficient data collected
    6. CHANGE_CHANNEL    → Try different communication channel
    7. REDUCE_QUESTIONS  → Ask fewer questions next round
    8. EXTEND_DEADLINE   → Request regulatory deadline extension
    """
```

---

## 5.6 Database Models

### FollowUpLifecycle
```python
class FollowUpLifecycle(Base):
    __tablename__ = "followup_lifecycle"
    
    id: int                         # Primary key
    case_id: int                    # FK → ae_cases.id
    reporter_type: str              # HCP / NON_HCP
    policy_applied: str             # "HCP_POLICY" / "NON_HCP_POLICY"
    status: LifecycleStatus         # Enum: INITIATED/ACTIVE/STALLED/ESCALATED/COMPLETED/DEAD_LETTER
    current_attempt: int            # Current round number
    total_questions_asked: int
    total_questions_answered: int
    completeness_at_start: float
    completeness_current: float
    deadline_date: datetime
    escalation_count: int
    created_at: datetime
    updated_at: datetime
```

### LifecycleAttempt
```python
class LifecycleAttempt(Base):
    __tablename__ = "lifecycle_attempts"
    
    id: int
    lifecycle_id: int               # FK → followup_lifecycle.id
    attempt_number: int
    channel: str                    # EMAIL/PHONE/WHATSAPP/PORTAL
    questions_sent: int
    questions_answered: int
    sent_at: datetime
    responded_at: datetime          # Nullable
    response_time_hours: float      # Nullable
    status: str                     # SENT/RESPONDED/NO_RESPONSE/PARTIAL
```

### LifecycleAuditLog
```python
class LifecycleAuditLog(Base):
    __tablename__ = "lifecycle_audit_log"
    
    id: int
    lifecycle_id: int
    action: str                     # State transition action
    from_status: str
    to_status: str
    actor: str                      # SYSTEM/AI/HUMAN
    reason: str
    metadata: JSON
    created_at: datetime
```

### ReporterPolicy
```python
class ReporterPolicy(Base):
    __tablename__ = "reporter_policies"
    
    id: int
    reporter_type: str              # HCP / NON_HCP
    max_attempts: int
    questions_per_round: int
    escalate_after: int
    escalate_to: str
    auto_dead_letter: bool
    is_active: bool
    created_at: datetime
```

### Enums

```python
class LifecycleStatus(str, Enum):
    INITIATED = "initiated"
    ACTIVE = "active"
    STALLED = "stalled"
    ESCALATED = "escalated"
    COMPLETED = "completed"
    DEAD_LETTER = "dead_letter"

class ResponseStatus(str, Enum):
    SENT = "sent"
    RESPONDED = "responded"
    NO_RESPONSE = "no_response"
    PARTIAL = "partial"

class EscalationStatus(str, Enum):
    NOT_ESCALATED = "not_escalated"
    ESCALATED = "escalated"
    RESOLVED = "resolved"

class SeriousnessLevel(str, Enum):
    SERIOUS = "serious"
    NON_SERIOUS = "non_serious"
    UNKNOWN = "unknown"

class ReporterType(str, Enum):
    HCP = "hcp"
    NON_HCP = "non_hcp"
```

---

## 5.7 Escalation Chain (5 Levels)

```
Level 1: AI System (automatic follow-up)
    │ No response after escalate_after rounds
    ▼
Level 2: Supervisor / Medical Team (per policy)
    │ Still no response
    ▼
Level 3: Safety Officer review
    │ Case flagged for manual intervention
    ▼
Level 4: Regulatory team notification
    │ Deadline at risk
    ▼
Level 5: Dead letter / regulatory submission with available data
```

---

## 5.8 Frontend: Lifecycle Stepper

**File**: `frontend/src/pages/CaseAnalysis.jsx` — Right panel

```
┌─────────────────────────────────┐
│      Follow-Up Lifecycle         │
│                                  │
│  ● INITIATED     ✅ Complete     │
│  │                               │
│  ● ACTIVE        🔄 In Progress │
│  │  Attempt 2/4                  │
│  │  Questions: 3/5 answered      │
│  │                               │
│  ○ STALLED       ⬜ Pending     │
│  │                               │
│  ○ ESCALATED     ⬜ Pending     │
│  │                               │
│  ○ COMPLETED     ⬜ Pending     │
│                                  │
│  ⏱️ Deadline: 3 days remaining  │
│  📊 Completeness: 67% → 85%     │
│  👤 Reporter: HCP (MD)          │
│  📋 Policy: HCP_POLICY          │
└─────────────────────────────────┘
```

---

## 5.9 How to Explain to Judges

> "In pharmacovigilance, you can't treat a doctor the same as a patient. Doctors can handle 5 technical questions; patients need simpler language and fewer questions. Our lifecycle manager applies different policies — HCPs get up to 4 rounds of 5 questions, consumers get 3 rounds of 2 questions. The system tracks every attempt, monitors regulatory deadlines (7 days for serious, 15 days for routine), and automatically escalates when the reporter stops responding. And for HCP cases, we never auto-close — they always require human review."

---

*See F6_SIGNAL_DETECTION.md for how completed cases feed into safety signal analysis.*
