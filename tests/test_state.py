"""
Unit tests for state management models.
"""

import pytest
from app.core.state import (
    AgentState,
    TriageResult,
    FinancialAnalysis,
    OSINTFindings,
    IRSScore,
    FinalDecision,
)


def test_triage_result_creation():
    """Test TriageResult model creation."""
    result = TriageResult(
        status="PASSED",
        rejection_reason=None,
        eligibility_flags=["FLAG1", "FLAG2"],
    )

    assert result.status == "PASSED"
    assert result.rejection_reason is None
    assert len(result.eligibility_flags) == 2


def test_financial_analysis_creation():
    """Test FinancialAnalysis model creation."""
    from decimal import Decimal

    analysis = FinancialAnalysis(
        bank_account_verified=True,
        salary_verified=True,
        detected_salary_amount=Decimal("35000.0"),
        total_monthly_credits=Decimal("100000.0"),
        total_monthly_debits=Decimal("80000.0"),
        average_balance=Decimal("20000.0"),
        credit_score=750,
        risk_flags=["FIN-01: Fast Withdrawal"],
        financial_behavior_score=85,
    )

    assert analysis.bank_account_verified is True
    assert analysis.total_monthly_credits == Decimal("100000.0")
    assert analysis.average_balance == Decimal("20000.0")
    assert analysis.credit_score == 750
    assert analysis.financial_behavior_score == 85


def test_osint_findings_creation():
    """Test OSINTFindings model creation."""
    findings = OSINTFindings(
        business_found=True,
        digital_veracity_score=0.85,
        sources_checked=["google_maps", "instagram"],
        evidence={"google_maps": {"found": True}},
    )

    assert findings.business_found is True
    assert findings.digital_veracity_score == 0.85
    assert len(findings.sources_checked) == 2


def test_irs_score_creation():
    """Test IRSScore model creation."""
    score = IRSScore(
        score=78,
        breakdown={
            "credit_history": 20,
            "payment_capacity": 18,
            "stability": 15,
            "collateral": 10,
            "payment_morality": 15,
        },
        flags=["FLAG1"],
        deductions=[{"variable": "test",
                     "rule": "test_rule", "points_deducted": 5}],
        narrative="Test narrative",
    )

    assert score.score == 78
    assert len(score.breakdown) == 5
    assert len(score.flags) == 1


def test_final_decision_creation():
    """Test FinalDecision model creation."""
    decision = FinalDecision(
        decision="APPROVED",
        confidence=0.92,
        risk_level="LOW",
        suggested_amount=None,
        suggested_term=None,
        reasoning="Test reasoning",
        requires_human_review=False,
    )

    assert decision.decision == "APPROVED"
    assert decision.confidence == 0.92
    assert decision.risk_level == "LOW"
    assert decision.requires_human_review is False


def test_agent_state_creation():
    """Test AgentState model creation."""
    state = AgentState(
        case_id="TEST-001",
        applicant={"id": "001-XXXXXXX-X", "full_name": "Test User"},
        loan={"requested_amount": 50000.0, "term_months": 12},
        documents=[],
        config={},
    )

    assert state.case_id == "TEST-001"
    assert state.current_step == "initialized"
    assert len(state.agents_executed) == 0
    assert state.llm_calls == 0


def test_agent_state_with_results():
    """Test AgentState with populated results."""
    triage_result = TriageResult(status="PASSED", eligibility_flags=[])

    state = AgentState(
        case_id="TEST-002",
        applicant={"id": "002-XXXXXXX-X"},
        loan={"requested_amount": 75000.0, "term_months": 24},
        documents=[],
        config={},
        triage_result=triage_result,
        agents_executed=["triage"],
    )

    assert state.triage_result is not None
    assert state.triage_result.status == "PASSED"
    assert "triage" in state.agents_executed
