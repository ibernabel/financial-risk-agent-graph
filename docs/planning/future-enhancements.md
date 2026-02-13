# Future Enhancements - Post-MVP Roadmap

## Overview

This document outlines planned enhancements for the CreditFlow AI system after MVP launch. Prioritized based on stakeholder feedback and production data insights.

---

## Priority 1: Critical Enhancements (Q2 2026)

### 1.1 Payment Capacity Integration

**Current State:** Simplified 30% salary rule in underwriter node  
**Target State:** Full Variable B cash flow calculation from IRS engine

**Motivation:**

- Current 30% rule doesn't account for actual expenses
- IRS engine already calculates detailed cash flow (Variable B)
- Better accuracy in suggested amount calculations

**Implementation:**

**Step 1:** Expose `payment_capacity` from IRS engine

```python
# app/agents/irs_engine/payment_capacity.py
def calculate_payment_capacity(
    monthly_income: Decimal,
    monthly_expenses: Decimal,
    existing_debts: list[dict],
) -> Decimal:
    """
    Calculate realistic payment capacity using Variable B logic.

    Formula:
    payment_capacity = (income - expenses - existing_debts) * safety_margin
    """
    # Already implemented in Phase 6, expose in IRSScore model
```

**Step 2:** Update underwriter suggested amount calculation

```python
# app/agents/underwriter/node.py
if state.irs_score and state.irs_score.payment_capacity:
    # Use IRS engine payment capacity instead of 30% rule
    payment_capacity = state.irs_score.payment_capacity
```

**Expected Impact:**

- **Accuracy:** ±10% → ±5% suggested amount variance
- **Approval Rate:** +5% (fewer over/under suggestions)

**Timeline:** 2 weeks  
**Dependencies:** None (IRS engine logic already exists)  
**Owner:** Backend Dev

---

### 1.2 Confidence Calibration Based on Production Data

**Current State:** Weights set based on intuition (30%, 25%, 20%, 15%, 10%)  
**Target State:** Empirically calibrated weights from production outcomes

**Motivation:**

- Current weights are educated guesses
- Production data will reveal which factors truly predict accuracy
- Data-driven approach reduces bias

**Implementation:**

**Step 1:** Collect production data (First 90 days)

```sql
-- Track confidence vs. outcome
CREATE TABLE confidence_calibration (
  case_id VARCHAR PRIMARY KEY,
  predicted_confidence FLOAT,
  decision VARCHAR,
  actual_outcome VARCHAR, -- Analyst override, default, manual approval
  override_reason TEXT,
  confidence_breakdown JSONB -- Factor scores
);
```

**Step 2:** Analyze confidence vs. outcome correlation

```python
# scripts/calibrate_confidence.py
import pandas as pd
from sklearn.linear_model import LogisticRegression

# Load data
df = pd.read_sql("SELECT * FROM confidence_calibration LIMIT 1000", engine)

# Features: factor scores
X = df[['doc_quality', 'data_completeness', 'cross_validation', 'osint', 'irs_deductions']]
y = df['was_accurate'] # Binary: did confidence match outcome?

# Train model to find optimal weights
model = LogisticRegression()
model.fit(X, y)

# New weights
weights = model.coef_[0]
print(f"Optimal weights: {weights}")
```

**Step 3:** Update confidence scoring module

```python
# Update WEIGHT constants based on calibration
WEIGHT_DOCUMENT_QUALITY = 0.28  # Was 0.30
WEIGHT_DATA_COMPLETENESS = 0.27  # Was 0.25
# ... etc
```

**Expected Impact:**

- **Accuracy:** Confidence ≥85% cases should have <5% override rate
- **Precision:** Better distinguish high vs. medium confidence cases

**Timeline:** Ongoing (quarterly calibration after enough data)  
**Dependencies:** 90 days of production data  
**Owner:** Data Analyst + ML Engineer

---

### 1.3 Suggested Amount Logic Refinement

**Current State:** Fixed 80% buffer for MEDIUM risk  
**Target State:** Dynamic buffer based on risk sub-factors

**Stakeholder Feedback:** Finance team to review 80% buffer

**Motivation:**

- 80% might be too conservative for IRS 80-84 (low-end MEDIUM)
- Should consider other factors: credit history, stability, etc.

**Proposed Logic:**

**Risk-Adjusted Buffer:**

| IRS Range | Credit History | Stability | Buffer |
| --------- | -------------- | --------- | ------ |
| 80-84     | Good (20+)     | High      | 90%    |
| 75-79     | Fair (15-19)   | Medium    | 85%    |
| 70-74     | Fair           | Medium    | 80%    |
| 65-69     | Poor (<15)     | Low       | 75%    |
| 60-64     | Poor           | Low       | 70%    |

**Implementation:**

```python
# app/agents/underwriter/decision_matrix.py
def get_risk_adjusted_buffer(irs_score: int, irs_breakdown: dict) -> Decimal:
    """Dynamic buffer based on IRS sub-scores."""
    credit_history = irs_breakdown.get("credit_history", 0)
    stability = irs_breakdown.get("stability", 0)

    if irs_score >= 80 and credit_history >= 20 and stability >= 12:
        return Decimal("0.90")
    elif irs_score >= 75:
        return Decimal("0.85")
    # ... etc
```

**Expected Impact:**

- **Approval Rate:** +8% (more nuanced risk assessment)
- **Default Rate:** No change (still risk-aware)

**Timeline:** 1 week (after finance team review)  
**Dependencies:** Finance team sign-off  
**Owner:** Backend Dev + Finance Analyst

---

## Priority 2: User Experience Enhancements (Q3 2026)

### 2.1 Narrative Customization by Loan Product

**Current State:** Generic narrative for all loan types  
**Target State:** Product-specific templates (personal, business, vehicle, etc.)

**Motivation:**

- Different products have different risk factors
- Analysts want product-specific reasoning

**Implementation:**

**Narrative Templates:**

```python
# app/agents/underwriter/narrative.py
TEMPLATES = {
    "PERSONAL_LOAN": {
        "focus": ["credit_history", "salary_stability", "debt_ratio"],
        "header": "Préstamo Personal"
    },
    "BUSINESS_LOAN": {
        "focus": ["digital_veracity", "business_stability", "cash_flow"],
        "header": "Préstamo Empresarial"
    },
    "VEHICLE_LOAN": {
        "focus": ["collateral_value", "payment_capacity", "credit_history"],
        "header": "Préstamo Vehicular"
    }
}

def generate_narrative(state, decision, product_type="PERSONAL_LOAN"):
    template = TEMPLATES[product_type]
    # Generate narrative focused on product-specific factors
```

**Timeline:** 2 weeks  
**Dependencies:** Product definitions from LAMAS  
**Owner:** Backend Dev + UX Writer

---

## Priority 3: Advanced Features (Q4 2026)

### 3.1 Machine Learning Model for IRS Score Prediction

**Current State:** Rule-based IRS scoring (Variable A-E)  
**Target State:** Hybrid model (rules + ML for edge cases)

**Motivation:**

- ML can detect non-linear patterns in data
- Better handle edge cases not covered by rules

**Implementation:**

**Hybrid Approach:**

1. **Use rules** for Variable A-D (well-defined logic)
2. **Train ML model** for Variable E (Payment Morality) - hardest to predict

**Model Training:**

```python
# Train on historical data
import xgboost as xgb

# Features: credit history, payment patterns, OSINT signals
X = df[['credit_score', 'days_past_due', 'loan_count', 'dvs_score', ...]]
y = df['payment_morality_score']  # Target: 0-20

model = xgb.XGBRegressor()
model.fit(X, y)

# Use in IRS engine
predicted_morality = model.predict(features)
```

**Expected Impact:**

- **Accuracy:** +3% IRS score accuracy
- **Edge Cases:** Better handle informal borrowers

**Timeline:** 6 weeks (research + training + integration)  
**Dependencies:** ML infrastructure, production data  
**Owner:** ML Engineer + Data Scientist

---

### 3.2 Real-Time Credit Bureau Integration

**Current State:** Upload credit report manually (PDF)  
**Target State:** Query DataCrédito API in real-time

**Motivation:**

- Eliminate manual document upload step
- Always get latest credit data

**Implementation:**

**API Integration:**

```python
# app/services/datacredito.py
import httpx

async def fetch_credit_report(cedula: str) -> dict:
    """Fetch credit report from DataCrédito API."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.datacredito.com.do/v1/reports",
            headers={"Authorization": f"Bearer {API_KEY}"},
            json={"cedula": cedula}
        )
        return response.json()
```

**Update Document Processor:**

```python
# app/agents/document_processor/node.py
if state.config.get("use_datacredito_api", False):
    credit_report = await fetch_credit_report(state.applicant["cedula"])
else:
    # Parse uploaded PDF (fallback)
    credit_report = parse_credit_report_pdf(...)
```

**Timeline:** 3 weeks (API integration + testing)  
**Dependencies:** DataCrédito API access, contract  
**Owner:** Backend Dev + Integrations Lead

> **Note:** The interactive explainability dashboard will be implemented on the **LAMAS side** (see [`docs/planning/lamas-integration-requirements.md`](file:///home/ibernabel/develop/aisa/financial-risk-agent-graph/docs/planning/lamas-integration-requirements.md)). CreditFlow is a stateless headless backend that provides comprehensive data in its API response, and LAMAS is responsible for presenting this data to analysts through a rich UI.

---

## Priority 4: Infrastructure & DevOps (Ongoing)

### 4.1 Horizontal Scaling for High Volume

**Current State:** Single instance deployment  
**Target State:** Auto-scaling with Kubernetes

**Implementation:**

```yaml
# kubernetes/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: creditflow-api
spec:
  replicas: 3 # Start with 3 pods
  selector:
    matchLabels:
      app: creditflow-api
  template:
    spec:
      containers:
        - name: api
          image: creditflow:latest
          resources:
            requests:
              memory: "1Gi"
              cpu: "500m"
            limits:
              memory: "2Gi"
              cpu: "1000m"
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: creditflow-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: creditflow-api
  minReplicas: 3
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

**Timeline:** 2 weeks  
**Dependencies:** Kubernetes cluster  
**Owner:** DevOps

---

### 4.2 Advanced Monitoring & Alerting

**Current State:** Basic logging  
**Target State:** Comprehensive observability

**Tools:**

- **Metrics:** Prometheus + Grafana
- **Logs:** ELK Stack (Elasticsearch, Logstash, Kibana)
- **Tracing:** OpenTelemetry + Jaeger
- **Alerts:** PagerDuty

**Dashboards:**

- **Business Metrics:** Decision distribution, confidence distribution, approval rate
- **Technical Metrics:** Response time, error rate, database connections
- **Agent Metrics:** Execution time per agent, success rate

**Timeline:** 3 weeks  
**Dependencies:** Observability stack setup  
**Owner:** DevOps + SRE

---

## Roadmap Summary

| Priority | Feature                      | Timeline | Impact          | Dependencies            |
| -------- | ---------------------------- | -------- | --------------- | ----------------------- |
| **P1**   | Payment Capacity Integration | 2 weeks  | High accuracy   | None                    |
| **P1**   | Confidence Calibration       | Ongoing  | High accuracy   | 90 days production data |
| **P1**   | Suggested Amount Refinement  | 1 week   | Higher approval | Finance sign-off        |
| **P2**   | Narrative Customization      | 2 weeks  | Better UX       | Product definitions     |
| **P3**   | ML for IRS Prediction        | 6 weeks  | Edge cases      | ML infra, data          |
| **P3**   | Real-Time Credit Bureau      | 3 weeks  | Faster flow     | DataCrédito API         |
| **P4**   | Kubernetes Auto-Scaling      | 2 weeks  | High volume     | K8s cluster             |
| **P4**   | Advanced Monitoring          | 3 weeks  | Reliability     | Observability stack     |

> **Dashboard Implementation:** See [LAMAS Integration Requirements](file:///home/ibernabel/develop/aisa/financial-risk-agent-graph/docs/planning/lamas-integration-requirements.md) for detailed dashboard specifications (LAMAS-side).

---

## Resource Requirements

### Team Structure

| Role               | Allocation | Duration |
| ------------------ | ---------- | -------- |
| Backend Developer  | 1 FTE      | 6 months |
| Frontend Developer | 0.5 FTE    | 2 months |
| ML Engineer        | 1 FTE      | 3 months |
| Data Analyst       | 0.5 FTE    | 3 months |
| DevOps Engineer    | 0.5 FTE    | 2 months |
| QA Engineer        | 0.5 FTE    | 6 months |

### Budget Estimate

| Category         | Cost (USD)   |
| ---------------- | ------------ |
| Personnel        | $150,000     |
| Infrastructure   | $10,000      |
| Third-party APIs | $5,000       |
| Tools & Services | $5,000       |
| **Total**        | **$170,000** |

---

## Success Metrics (6 Months Post-MVP)

| Metric                      | Current (MVP) | Target (6M) | Measurement                |
| --------------------------- | ------------- | ----------- | -------------------------- |
| Decision Accuracy           | 92%           | 97%         | Analyst override rate      |
| Confidence Calibration      | N/A           | ±5%         | Predicted vs. actual       |
| Suggested Amount Accuracy   | ±10%          | ±5%         | vs. analyst final decision |
| Avg Response Time           | 5s            | 3s          | API latency                |
| Analyst Satisfaction        | Baseline      | 4.5/5       | Survey (quarterly)         |
| Loan Approval Rate (MEDIUM) | 45%           | 55%         | Better risk assessment     |

---

**Document Status:** Draft (Pending stakeholder prioritization)  
**Last Updated:** 2026-02-12  
**Owner:** Product Lead + Tech Lead
