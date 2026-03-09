# Feature 6: Safety Signal Detection

---

## Overview
SmartFU implements **Proportional Reporting Ratio (PRR)** based safety signal detection per EU Pharmacovigilance legislation. The system continuously monitors drug-event relationships across all cases, classifies emerging signals, and surfaces them for regulatory review on a dedicated dashboard.

---

## 6.1 Architecture

**File**: `backend/app/services/signal_service.py` (251 lines)

```
┌─────────────────────────────────────────────────────────┐
│                    SignalService                          │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐     ┌─────────────────────────────┐   │
│  │  Case Data    │────▶│  PRR Calculator              │   │
│  │  ae_cases     │     │  (drug-event pair analysis)   │   │
│  └──────────────┘     └──────────┬──────────────────┘   │
│                                   │                       │
│                          ┌────────▼──────────┐           │
│                          │ Signal Classifier  │           │
│                          │ STRONG/MODERATE/   │           │
│                          │ WEAK/NONE          │           │
│                          └────────┬──────────┘           │
│                                   │                       │
│                          ┌────────▼──────────┐           │
│                          │  Trend Analyzer    │           │
│                          │  (7-day window)    │           │
│                          └────────┬──────────┘           │
│                                   │                       │
│                          ┌────────▼──────────┐           │
│                          │ Risk Priority      │           │
│                          │ Auto-calculation    │           │
│                          └───────────────────┘           │
└─────────────────────────────────────────────────────────┘
```

---

## 6.2 PRR (Proportional Reporting Ratio)

### Formula

$$PRR = \frac{a/(a+b)}{c/(c+d)}$$

Where:
- $a$ = cases with **both** the target drug AND target event
- $b$ = cases with the **target drug** but **different** events
- $c$ = cases with **different drugs** but the **target event**
- $d$ = cases with **different drugs** AND **different events**

This is the standard pharmacovigilance disproportionality measure used by EMA and WHO.

### Example Calculation

Suppose we're checking the signal for **Drug X + Hepatotoxicity**:

| | Hepatotoxicity | Other Events | Total |
|---|---|---|---|
| **Drug X** | a = 8 | b = 42 | 50 |
| **Other Drugs** | c = 12 | d = 938 | 950 |
| **Total** | 20 | 980 | 1000 |

$$PRR = \frac{8/(8+42)}{12/(12+938)} = \frac{8/50}{12/950} = \frac{0.16}{0.01263} = 12.67$$

PRR = 12.67 with 8 cases → **STRONG signal** → status: CONFIRMED

---

## 6.3 Signal Thresholds

```python
SIGNAL_THRESHOLDS = {
    "min_cases": 2,          # Minimum cases to consider a signal
    "prr_threshold": 2.0,    # Minimum PRR to flag ANY signal
    "prr_strong": 8.0,       # PRR for strong signal
    "prr_moderate": 3.0,     # PRR for moderate signal
}
```

### Classification Logic

| PRR Value | Case Count | Classification | Status |
|---|---|---|---|
| ≥ 8.0 | ≥ 5 cases | **STRONG** | CONFIRMED |
| ≥ 8.0 | < 5 cases | **STRONG** | EMERGING |
| ≥ 3.0 | ≥ 3 cases | **MODERATE** | EMERGING |
| ≥ 3.0 | < 3 cases | **MODERATE** | EMERGING |
| ≥ 2.0 | ≥ 2 cases | **WEAK** | EMERGING |
| < 2.0 | any | **NONE** | — |

### Implementation

```python
def classify_signal(self, prr: float, case_count: int) -> Dict:
    if prr >= SIGNAL_THRESHOLDS["prr_strong"]:
        strength = "STRONG"
        status = "CONFIRMED" if case_count >= 5 else "EMERGING"
    elif prr >= SIGNAL_THRESHOLDS["prr_moderate"]:
        strength = "MODERATE"
        status = "EMERGING"
    elif prr >= SIGNAL_THRESHOLDS["prr_threshold"]:
        strength = "WEAK"
        status = "EMERGING"
    else:
        return None  # No signal
    
    return {
        "strength": strength,
        "status": status,
        "prr": prr,
        "case_count": case_count
    }
```

---

## 6.4 Trend Analysis (7-Day Window)

The system computes a **trend indicator** based on case volume change over a 7-day rolling window:

```python
def calculate_trend(self, drug: str, event: str) -> str:
    """
    Compare cases in last 7 days vs previous 7 days.
    
    Returns:
      "INCREASING"  → ≥ 50% more cases in recent window
      "STABLE"      → Change within ±50%
      "DECREASING"  → ≥ 50% fewer cases in recent window
    """
```

| Recent 7d Cases | Previous 7d Cases | Trend |
|---|---|---|
| 8 | 3 | INCREASING (167% increase) |
| 5 | 5 | STABLE (0% change) |
| 2 | 7 | DECREASING (71% decrease) |

---

## 6.5 Risk Priority Auto-Calculation

Each signal gets an automatic risk priority based on multiple factors:

```python
def calculate_risk_priority(self, signal) -> str:
    """
    Priority = f(PRR, case_count, seriousness, trend)
    
    Returns: CRITICAL / HIGH / MEDIUM / LOW
    """
```

| Factor | CRITICAL | HIGH | MEDIUM | LOW |
|---|---|---|---|---|
| PRR | ≥ 8.0 | ≥ 5.0 | ≥ 3.0 | ≥ 2.0 |
| Cases | ≥ 10 | ≥ 5 | ≥ 3 | ≥ 2 |
| Seriousness | Fatal/Life-threatening | Serious | Non-serious | — |
| Trend | INCREASING | STABLE | — | DECREASING |

---

## 6.6 Database Model

### SafetySignal

```python
class SafetySignal(Base):
    __tablename__ = "safety_signals"
    
    id: int                    # Primary key
    drug_name: str             # Suspect drug
    event_type: str            # Adverse event (MedDRA preferred term)
    prr_score: float           # Calculated PRR
    case_count: int            # Number of cases in signal
    signal_strength: str       # STRONG/MODERATE/WEAK
    status: str                # EMERGING/CONFIRMED/UNDER_REVIEW/FALSE_POSITIVE/CLOSED
    trend: str                 # INCREASING/STABLE/DECREASING
    risk_priority: str         # CRITICAL/HIGH/MEDIUM/LOW
    first_detected: datetime   # When signal first emerged
    last_updated: datetime     # Last recalculation
    reviewer_notes: str        # Human reviewer comments
    frozen_snapshot: JSON      # Regulatory snapshot at time of detection
    created_at: datetime
    updated_at: datetime
```

### Signal Status Flow

```
EMERGING → UNDER_REVIEW → CONFIRMED → CLOSED
                ↓
          FALSE_POSITIVE → CLOSED
```

---

## 6.7 Regulatory Workflow

When a signal is detected:

```
1. Signal auto-detected
   ├── PRR calculated across all cases
   ├── Signal record created in safety_signals table
   └── Risk priority auto-assigned

2. Notification
   ├── Signal appears on dashboard Signals panel
   ├── If CRITICAL → immediate alert to Safety Officer
   └── PV audit trail entry: SIGNAL_DETECTED

3. Review
   ├── Safety Officer reviews signal
   ├── Can add reviewer_notes
   ├── Can change status to UNDER_REVIEW
   └── PV audit trail: SIGNAL_REVIEWED

4. Decision
   ├── CONFIRMED → Regulatory submission required
   │   ├── frozen_snapshot captures case data at decision point
   │   ├── Regulatory workflow created
   │   └── PV audit trail: REGULATORY_WORKFLOW_CREATED
   │
   ├── FALSE_POSITIVE → Close signal
   │   └── PV audit trail: SIGNAL_FALSE_POSITIVE
   │
   └── PRIORITY_CHANGED → Adjust priority level
       └── PV audit trail: SIGNAL_PRIORITY_CHANGED
```

### Frozen Snapshot
When a signal is confirmed, the system captures an **immutable snapshot** of all supporting case data:

```json
{
    "snapshot_date": "2024-01-15T14:30:00Z",
    "drug_name": "Metformin",
    "event_type": "Lactic Acidosis",
    "prr_at_detection": 12.67,
    "case_count": 8,
    "supporting_case_ids": [42, 78, 93, 105, 112, 134, 156, 178],
    "seriousness_breakdown": {
        "fatal": 1,
        "hospitalized": 5,
        "other_serious": 2
    }
}
```

---

## 6.8 API Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/signals` | GET | List all signals (with filtering) |
| `/api/signals/{id}` | GET | Get signal details |
| `/api/signals/detect` | POST | Trigger signal detection run |
| `/api/signals/{id}/review` | PUT | Update signal status/notes |
| `/api/signals/{id}/priority` | PUT | Change signal priority |
| `/api/signals/dashboard` | GET | Signal statistics for dashboard |

---

## 6.9 Frontend: Signals Dashboard

**File**: `frontend/src/pages/Signals.jsx`

```
┌──────────────────────────────────────────────────────────┐
│                   SAFETY SIGNALS                          │
├──────────┬──────────┬───────────┬────────────────────────┤
│ 🔴 3     │ 🟡 7     │ 🟢 12    │ Search / Filter        │
│ CRITICAL │ MODERATE │ WEAK     │ [Drug ▼] [Event ▼]     │
├──────────┴──────────┴───────────┴────────────────────────┤
│                                                           │
│  Drug          Event              PRR    Cases  Status    │
│  ─────────────────────────────────────────────────────    │
│  Metformin     Lactic Acidosis   12.67    8    CONFIRMED  │
│  Lisinopril    Angioedema         8.34    6    EMERGING   │
│  Atorvastatin  Rhabdomyolysis     5.21    4    UNDER_REV  │
│  Amoxicillin   Anaphylaxis        3.15    3    EMERGING   │
│  ...                                                      │
│                                                           │
│  📈 Trend: ▲ INCREASING (3 signals)                      │
│  📊 PRR Distribution: [Bar Chart]                         │
└──────────────────────────────────────────────────────────┘
```

### Dashboard Integration
On the main Dashboard.jsx, a **Signals Monitor** mini-panel shows:
- Count of active signals by priority
- Most recent signal detection
- Quick link to full Signals page

---

## 6.10 How to Explain to Judges

> "Safety signal detection is how the pharmaceutical industry spots dangerous patterns. If Drug X is causing liver failure more often than expected, we need to catch that. SmartFU calculates PRR — Proportional Reporting Ratio — the standard WHO/EMA disproportionality measure. A PRR of 8 or more with 5+ cases is a confirmed strong signal. We track trends over 7-day windows and auto-assign risk priority. When a signal is confirmed, we capture an immutable snapshot for regulatory submission. This turns reactive pharmacovigilance into proactive safety monitoring."

---

*See F7_COMPLIANCE_AUDIT.md for how all signal actions are tracked in the audit trail.*
