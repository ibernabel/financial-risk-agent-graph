# Phase 7: Underwriter & Integration - Implementation

## Overview

Implementation of the production Underwriter agent with decision matrix logic, confidence scoring, and HITL escalation capabilities. Completed **2026-02-12**.

---

## Components Implemented

### 1. Decision Matrix Module

**File:** [`app/agents/underwriter/decision_matrix.py`](file:///home/ibernabel/develop/aisa/financial-risk-agent-graph/app/agents/underwriter/decision_matrix.py)

**Stakeholder-Approved Thresholds** (2026-02-12):

| Threshold               | Value      | Purpose                  |
| ----------------------- | ---------- | ------------------------ |
| `IRS_SCORE_APPROVED`    | 85         | Minimum IRS for APPROVED |
| `IRS_SCORE_REJECTED`    | 60         | Below this → REJECTED    |
| `CONFIDENCE_THRESHOLD`  | 0.85       | 85% confidence cutoff    |
| `HIGH_AMOUNT_THRESHOLD` | 50,000 DOP | Always → MANUAL_REVIEW   |

**Decision Logic:**

```python
if loan_amount > 50,000:
    return "MANUAL_REVIEW"  # Override
elif irs_score >= 85 and confidence >= 0.85:
    return "APPROVED"
elif irs_score >= 85 and confidence < 0.85:
    return "APPROVED_PENDING_REVIEW"
elif 60 <= irs_score < 85:
    return "MANUAL_REVIEW"  # Always suggest reduced amount
else:  # irs_score < 60
    return "REJECTED"
```

**Risk Levels:**

- **LOW:** IRS ≥ 85
- **MEDIUM:** IRS 70-84
- **HIGH:** IRS 60-69
- **CRITICAL:** IRS < 60

**Suggested Amount Calculation:**

For MEDIUM risk (IRS 60-84):

```python
suggested_amount = payment_capacity × term_months × 0.8
```

**Business Rules:**

- Always suggest reduced amount for MEDIUM risk (20% buffer)
- Never suggest longer terms (per stakeholder policy)
- Minimum 10% payment capacity ratio required
- Finance team to review formula post-MVP

---

### 2. Confidence Scoring Module

**File:** [`app/agents/underwriter/confidence.py`](file:///home/ibernabel/develop/aisa/financial-risk-agent-graph/app/agents/underwriter/confidence.py)

**5 Weighted Factors:**

| Factor              | Weight | Criteria                                            |
| ------------------- | ------ | --------------------------------------------------- |
| Document Quality    | 30%    | All documents parsed successfully, no OCR errors    |
| Data Completeness   | 25%    | Salary, credit score, bank account, employment date |
| Cross-Validation    | 20%    | Declared vs. detected salary within ±20%            |
| OSINT Coverage      | 15%    | Business found (DVS score) OR formal employment     |
| IRS Deduction Count | 10%    | Fewer deductions = higher confidence                |

**Configuration:**

- **Minimum Confidence Floor:** 0.30 (even with missing data)
- **OSINT Skip:** Redistribute weight when `skip_osint=True`
- **Graceful Degradation:** Handle missing agent outputs

**Formula:**

```python
confidence = Σ(factor_weight × factor_score)
confidence = max(confidence, 0.30)  # Apply floor
```

---

### 3. Narrative Generation Module

**File:** [`app/agents/underwriter/narrative.py`](file:///home/ibernabel/develop/aisa/financial-risk-agent-graph/app/agents/underwriter/narrative.py)

**Supported Languages:** Spanish (default), English

**Structure:**

1. **Header:** Decision, IRS score, risk level, confidence
2. **Key Findings:**
   - Credit history (from IRS narrative)
   - Financial analysis (salary, credit score, risk flags)
   - OSINT validation (DVS score, business found)
   - Suggested amount/term (if applicable)
3. **Recommendation:** Detailed reasoning in business language

**Configuration:**

```python
language = state.config.get("narrative_language", "es")
```

---

### 4. Production Underwriter Node

**File:** [`app/agents/underwriter/node.py`](file:///home/ibernabel/develop/aisa/financial-risk-agent-graph/app/agents/underwriter/node.py)

**Process Flow:**

1. Calculate confidence score from all agent outputs
2. Apply decision matrix (IRS + confidence + loan amount)
3. Calculate suggested amount for MEDIUM risk using payment capacity
4. Merge IRS flags with decision flags
5. Generate bilingual narrative
6. Return `FinalDecision` with full justification

**Payment Capacity Calculation (Simplified):**

```python
payment_capacity = monthly_salary × 0.30
payment_capacity -= (dependents × 2,000 DOP)  # Adjust for dependents
```

> **Note:** Full Variable B cash flow calculation will replace this in future phase.

---

## Testing

### Test Suite

**File:** [`tests/test_underwriter.py`](file:///home/ibernabel/develop/aisa/financial-risk-agent-graph/tests/test_underwriter.py)

**Results:** ✅ **35/35 tests passed** (100% coverage)

**Breakdown:**

| Category               | Tests | Coverage                                                                        |
| ---------------------- | ----- | ------------------------------------------------------------------------------- |
| Decision Matrix        | 7     | All decision paths (APPROVED, REJECTED, MANUAL_REVIEW, APPROVED_PENDING_REVIEW) |
| Risk Levels            | 4     | LOW, MEDIUM, HIGH, CRITICAL mapping                                             |
| Human Review Logic     | 4     | HITL escalation rules                                                           |
| Suggested Amount       | 3     | MEDIUM risk calculation, no suggestion for other risks                          |
| Decision Flags         | 4     | HIGH_AMOUNT, LOW_CONFIDENCE, MEDIUM_RISK, CRITICAL_RISK                         |
| Confidence Calculation | 5     | Perfect data, missing data, salary mismatch, floor, OSINT skip                  |
| Full Integration       | 4     | End-to-end workflows with all agents                                            |
| Edge Cases             | 4     | Partial workflow, zero IRS, rejected, missing financial                         |

---

## Stakeholder Decisions

### Decision Matrix Thresholds

**Confirmed:** 2026-02-12

- **IRS ≥85 + Confidence ≥85%** → `APPROVED`
- **IRS ≥85 + Confidence <85%** → `APPROVED_PENDING_REVIEW`
- **IRS 60-84** → `MANUAL_REVIEW`
- **IRS <60** → `REJECTED`
- **Loan >50K DOP** → `MANUAL_REVIEW` (override)

### Suggested Amount Logic

**Confirmed:** 2026-02-12

For MEDIUM risk (IRS 60-84):

- Always suggest reduced amount
- Never extend term
- Formula: `payment_capacity × term_months × 0.80`
- Finance team to review post-MVP

### Narrative Language

**Default:** Spanish (`es`)

**Configuration:**

```python
{
  "narrative_language": "es"  # or "en"
}
```

---

## API Contract

### FinalDecision Model

```python
class FinalDecision(BaseModel):
    decision: Literal["APPROVED", "REJECTED", "MANUAL_REVIEW", "APPROVED_PENDING_REVIEW"]
    confidence: float
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    suggested_amount: Optional[float] = None
    suggested_term: Optional[int] = None
    reasoning: str  # Bilingual narrative
    requires_human_review: bool
```

**LAMAS Integration:**

| Decision                  | LAMAS Action                  |
| ------------------------- | ----------------------------- |
| `APPROVED`                | Auto-approve                  |
| `APPROVED_PENDING_REVIEW` | Route to junior analyst queue |
| `MANUAL_REVIEW`           | Route to senior analyst queue |
| `REJECTED`                | Auto-reject with reasoning    |

---

## Performance

### Execution Time

- **Average:** <100ms per underwriter decision
- **Bottleneck:** None (pure Python logic, no LLM calls)

### Memory Usage

- **State Size:** ~50KB per case (with full agent outputs)
- **Checkpointing:** PostgreSQL for state persistence

---

## Security & Compliance

### Data Privacy

- **Law 172-13 Compliance:** No PII exposed in narratives
- **Audit Trail:** All decisions logged with `case_id`
- **Error Handling:** Graceful degradation, no crashes on missing data

### HITL Escalation Triggers

| Trigger            | Condition            | Action                                       |
| ------------------ | -------------------- | -------------------------------------------- |
| Low Confidence     | Confidence < 85%     | `APPROVED_PENDING_REVIEW` or `MANUAL_REVIEW` |
| High Amount        | Loan > 50,000 DOP    | `MANUAL_REVIEW`                              |
| Medium Risk        | IRS 60-84            | `MANUAL_REVIEW`                              |
| Data Inconsistency | Salary mismatch >20% | Lower confidence → escalation                |

---

## Future Enhancements

### Post-MVP Improvements

1. **Payment Capacity Integration:**
   - Replace simplified 30% rule with full Variable B calculation from IRS engine
   - Use actual cash flow analysis

2. **Confidence Calibration:**
   - Collect production data: confidence scores vs. actual outcomes
   - Adjust weights empirically

3. **Suggested Amount Refinement:**
   - Finance team review of 80% buffer
   - Consider loan product-specific adjustments

4. **Narrative Customization:**
   - Configurable templates per loan product
   - Additional language support (Haitian Creole)

---

## Related Documentation

- [PRD: Underwriter Agent](file:///home/ibernabel/develop/aisa/financial-risk-agent-graph/docs/planning/prd.md) (Section 5.5)
- [Phase 6: IRS Engine](file:///home/ibernabel/develop/aisa/financial-risk-agent-graph/docs/implementation/phase-6-irs-engine.md)
- [Walkthrough](file:///home/ibernabel/.gemini/antigravity/brain/e4ef1d8d-f193-4306-9496-f5931ae03036/walkthrough.md)

---

**Status:** ✅ **COMPLETE** (2026-02-12)
