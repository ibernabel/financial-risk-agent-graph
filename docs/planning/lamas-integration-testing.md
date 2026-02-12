# LAMAS Integration Testing Plan

## Overview

This document outlines the plan for testing the CreditFlow AI integration with LAMAS (Loan Application Management System) in staging environment.

**Objective:** Validate end-to-end workflow from LAMAS webhook trigger to final decision response.

---

## Prerequisites

### 1. Environment Setup

**Staging Environment Requirements:**

- [ ] CreditFlow AI deployed to staging server
- [ ] PostgreSQL database configured with checkpointing
- [ ] API endpoint accessible from LAMAS staging
- [ ] Environment variables configured (`.env.staging`)
- [ ] LAMAS staging environment accessible

**Configuration Variables:**

```bash
# CreditFlow AI Staging
ENVIRONMENT=staging
DATABASE_URL=postgresql://user:pass@staging-db:5432/creditflow_staging
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=DEBUG

# LAMAS Integration
LAMAS_WEBHOOK_SECRET=<shared-secret>
LAMAS_CALLBACK_URL=https://lamas-staging.example.com/api/v1/decisions
```

### 2. Test Data Preparation

**Required Test Cases:**

1. **APPROVED** - Perfect profile (IRS 90, confidence 92%)
2. **APPROVED_PENDING_REVIEW** - High IRS, low confidence (IRS 88, confidence 75%)
3. **MANUAL_REVIEW (MEDIUM)** - Medium risk (IRS 72, confidence 85%)
4. **MANUAL_REVIEW (HIGH_AMOUNT)** - High amount override (IRS 95, amount 75K DOP)
5. **REJECTED** - Critical risk (IRS 45, confidence 60%)

**Test Documents:**

- Bank statements (PDF + CSV fallback)
- Credit reports (DataCrédito format)
- Identity documents (Cédula)
- Business documents (RNC, contracts - for self-employed)

---

## Testing Phases

### Phase 1: API Contract Validation

**Objective:** Verify request/response schemas match LAMAS expectations

**Tasks:**

1. **Review API Contract**
   - [ ] Obtain LAMAS API specification (OpenAPI/Swagger)
   - [ ] Compare with CreditFlow AI `/api/v1/analyze` endpoint
   - [ ] Identify any schema differences

2. **Request Schema Validation**

   ```bash
   # Test LAMAS request format
   curl -X POST http://localhost:8000/api/v1/analyze \
     -H "Content-Type: application/json" \
     -d @test/fixtures/lamas_request_sample.json
   ```

3. **Response Schema Validation**
   - [ ] Verify `decision` enum matches LAMAS expectations
   - [ ] Confirm `suggested_amount` and `suggested_term` are nullable
   - [ ] Test `reasoning` narrative formatting (Spanish)
   - [ ] Validate `flags` array structure

**Expected Output:**

```json
{
  "case_id": "TEST-LAMAS-001",
  "decision": "APPROVED",
  "irs_score": 90,
  "confidence": 0.92,
  "risk_level": "LOW",
  "suggested_amount": null,
  "suggested_term": null,
  "flags": [],
  "irs_breakdown": { ... },
  "osint_validation": { ... },
  "reasoning": "✅ **APROBADO**\n**IRS Score:** 90/100 ..."
}
```

**Success Criteria:**

- ✅ All required fields present
- ✅ Data types match schema
- ✅ No validation errors in LAMAS staging

---

### Phase 2: Webhook Integration Testing

**Objective:** Test LAMAS-to-CreditFlow webhook trigger

**Tasks:**

1. **Webhook Setup**
   - [ ] Configure LAMAS staging to send webhook to CreditFlow AI
   - [ ] Implement webhook authentication (HMAC signature verification)
   - [ ] Set up ngrok tunnel for local testing (if needed)

2. **Trigger Test Webhooks**

   ```bash
   # From LAMAS staging, trigger analysis for test case
   # LAMAS sends POST to: https://creditflow-staging.example.com/api/v1/webhook/analyze
   ```

3. **Validate Webhook Receipt**
   - [ ] Check CreditFlow AI logs for webhook receipt
   - [ ] Verify request signature validation
   - [ ] Confirm `case_id` generated correctly
   - [ ] Track execution through LangGraph workflow

**Success Criteria:**

- ✅ Webhook received and authenticated
- ✅ Analysis triggered successfully
- ✅ `case_id` returned immediately (async processing)

---

### Phase 3: End-to-End Workflow Testing

**Objective:** Execute full analysis and verify LAMAS callback

**Test Scenarios:**

#### Scenario 1: APPROVED (Auto-Approve)

**Input:**

- IRS Score: 90
- Confidence: 0.92
- Loan Amount: 40,000 DOP
- Term: 24 months

**Expected Flow:**

1. LAMAS sends webhook → CreditFlow AI
2. CreditFlow executes agents (Triage → Document → Financial + OSINT → IRS → Underwriter)
3. Underwriter returns `APPROVED`
4. CreditFlow calls LAMAS callback with decision
5. LAMAS auto-approves loan

**Validation:**

- [ ] Decision = `APPROVED`
- [ ] Confidence ≥ 0.85
- [ ] No `suggested_amount` or `suggested_term`
- [ ] LAMAS loan status = "Auto-Approved"

---

#### Scenario 2: APPROVED_PENDING_REVIEW (Junior Analyst Queue)

**Input:**

- IRS Score: 88
- Confidence: 0.75 (low due to missing credit report)
- Loan Amount: 35,000 DOP

**Expected Flow:**

1. Underwriter returns `APPROVED_PENDING_REVIEW`
2. CreditFlow sends decision to LAMAS
3. LAMAS routes to junior analyst queue

**Validation:**

- [ ] Decision = `APPROVED_PENDING_REVIEW`
- [ ] `requires_human_review` = `true`
- [ ] Flags include `LOW_CONFIDENCE`
- [ ] LAMAS loan status = "Pending Review (Junior)"

---

#### Scenario 3: MANUAL_REVIEW (Medium Risk - Senior Analyst)

**Input:**

- IRS Score: 72
- Confidence: 0.85
- Loan Amount: 50,000 DOP (requested)
- Payment Capacity: 2,500 DOP/month

**Expected Flow:**

1. Underwriter returns `MANUAL_REVIEW`
2. Calculates `suggested_amount` = 2,500 × 24 × 0.8 = 48,000 DOP
3. LAMAS routes to senior analyst queue

**Validation:**

- [ ] Decision = `MANUAL_REVIEW`
- [ ] `suggested_amount` = 48,000 (reduced)
- [ ] `suggested_term` = `null` (never extend)
- [ ] Flags include `MEDIUM_RISK`
- [ ] LAMAS loan status = "Manual Review (Senior)"

---

#### Scenario 4: MANUAL_REVIEW (High Amount Override)

**Input:**

- IRS Score: 95 (perfect)
- Confidence: 0.95
- Loan Amount: 75,000 DOP (>50K threshold)

**Expected Flow:**

1. High-amount override triggers `MANUAL_REVIEW`
2. LAMAS routes to senior analyst queue (even with perfect score)

**Validation:**

- [ ] Decision = `MANUAL_REVIEW`
- [ ] Flags include `HIGH_AMOUNT`
- [ ] Reasoning mentions 50K DOP threshold

---

#### Scenario 5: REJECTED (Auto-Reject)

**Input:**

- IRS Score: 45 (critical risk)
- Confidence: 0.60
- Loan Amount: 30,000 DOP

**Expected Flow:**

1. Underwriter returns `REJECTED`
2. LAMAS auto-rejects with reasoning

**Validation:**

- [ ] Decision = `REJECTED`
- [ ] Risk level = `CRITICAL`
- [ ] Reasoning explains rejection (Spanish)
- [ ] LAMAS loan status = "Rejected"

---

### Phase 4: Error Handling & Edge Cases

**Objective:** Test failure scenarios and recovery

**Test Cases:**

1. **Missing Documents**
   - Scenario: No bank statement uploaded
   - Expected: `MANUAL_REVIEW` with low confidence
   - Validation: Graceful degradation, no crash

2. **OCR Failure**
   - Scenario: Corrupted PDF, OCR error
   - Expected: Document processing error logged, workflow continues
   - Validation: Confidence penalized, decision based on available data

3. **OSINT Timeout**
   - Scenario: OSINT agent takes >30s, timeout
   - Expected: OSINT skipped, confidence adjusted
   - Validation: Decision made without OSINT, flag added

4. **Invalid Loan Amount**
   - Scenario: Requested amount = 0 or negative
   - Expected: Triage rejects early
   - Validation: Error message, no full analysis

5. **Duplicate Case ID**
   - Scenario: LAMAS sends duplicate `case_id`
   - Expected: Return cached result from checkpoint
   - Validation: No re-execution, same decision

---

## Performance Testing

### Load Testing

**Objective:** Verify system handles production volume

**Tools:** `locust` or `k6`

**Test Parameters:**

- **Concurrent Users:** 50
- **Analysis Duration:** 10 minutes
- **Target RPS:** 5 analyses/second

**Metrics to Track:**

- Average response time (target: <5s for full analysis)
- 95th percentile response time
- Error rate (target: <1%)
- Database connection pool usage
- Memory consumption

**Load Test Script:**

```python
# locustfile.py
from locust import HttpUser, task, between

class CreditFlowUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def analyze_loan(self):
        self.client.post("/api/v1/analyze", json={
            "applicant": { ... },
            "loan": { ... },
            "documents": [ ... ]
        })
```

---

## Monitoring & Logging

### Staging Observability

**Logging:**

- [ ] Enable DEBUG level logging in staging
- [ ] Configure structured JSON logs
- [ ] Send logs to centralized logging (e.g., ELK, Datadog)

**Metrics:**

- [ ] Track decision distribution (APPROVED, REJECTED, etc.)
- [ ] Monitor agent execution times
- [ ] Track confidence score distribution
- [ ] Monitor error rates per agent

**Alerts:**

- [ ] Alert on error rate >5%
- [ ] Alert on avg response time >10s
- [ ] Alert on webhook authentication failures

---

## Rollback Plan

### If Critical Issues Found

**Criteria for Rollback:**

- Decision accuracy <80%
- Error rate >10%
- LAMAS integration breaks production

**Rollback Steps:**

1. Disable LAMAS webhook pointing to CreditFlow AI
2. Revert LAMAS to previous decision engine
3. Investigate failed test cases
4. Fix issues in CreditFlow AI
5. Re-test in staging

---

## Sign-off Checklist

### Before Production Deployment

- [ ] All 5 test scenarios pass (APPROVED, APPROVED_PENDING_REVIEW, MANUAL_REVIEW x2, REJECTED)
- [ ] API contract validated with LAMAS team
- [ ] Webhook authentication working
- [ ] Error handling tested (missing docs, OCR failure, etc.)
- [ ] Load test results acceptable (<5s avg response time)
- [ ] Monitoring and alerts configured
- [ ] Stakeholder demo completed
- [ ] Finance team approved suggested amount logic
- [ ] Rollback plan documented and team trained

---

## Timeline

| Phase                 | Duration    | Dependencies                 | Owner          |
| --------------------- | ----------- | ---------------------------- | -------------- |
| Environment Setup     | 2 days      | DevOps, LAMAS team           | DevOps         |
| API Contract Review   | 1 day       | LAMAS API spec               | Backend Lead   |
| Webhook Integration   | 2 days      | LAMAS staging access         | Backend Dev    |
| E2E Testing           | 3 days      | Test data, environment ready | QA + Dev       |
| Error Handling        | 2 days      | -                            | QA             |
| Performance Testing   | 2 days      | Load test scripts            | QA + DevOps    |
| Stakeholder Demo      | 1 day       | All tests passing            | Product + Tech |
| Production Deployment | 1 day       | Sign-off from stakeholders   | DevOps         |
| **Total**             | **14 days** | **(~3 weeks with buffer)**   |                |

---

## Success Metrics

### Post-Deployment (First Month)

- **Accuracy:** >95% of decisions align with manual analyst review
- **Confidence Calibration:** High confidence cases (≥85%) have <5% manual override rate
- **Performance:** <3s avg response time in production
- **Uptime:** >99.9% availability
- **LAMAS Integration:** <1% webhook failures

---

## Next Steps

1. **Schedule Kick-off Meeting** with LAMAS team
2. **Provision Staging Environment** (DevOps)
3. **Prepare Test Data** (QA + Finance)
4. **Execute Phase 1** (API Contract Validation)
5. **Iterate based on findings**

---

**Document Status:** Draft (Pending stakeholder review)  
**Last Updated:** 2026-02-12  
**Owner:** Tech Lead + QA Lead
