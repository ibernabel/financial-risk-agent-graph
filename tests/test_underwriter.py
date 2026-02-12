"""
Unit tests for the Underwriter Agent.

Tests cover:
1. Decision Matrix (7 tests)
2. Confidence Calculation (5 tests)
3. Integration Tests (4 tests)
4. Edge Cases (3 tests)

Total: 19 tests
"""

import pytest
from decimal import Decimal
from app.agents.underwriter.decision_matrix import (
    make_decision,
    get_risk_level,
    requires_human_review,
    calculate_suggested_amount,
    get_decision_flags,
    IRS_SCORE_APPROVED,
    IRS_SCORE_REJECTED,
    CONFIDENCE_THRESHOLD,
    HIGH_AMOUNT_THRESHOLD,
)
from app.agents.underwriter.confidence import (
    calculate_confidence,
    _calculate_document_quality_score,
    _calculate_data_completeness_score,
    _calculate_cross_validation_score,
    _calculate_osint_coverage_score,
    _calculate_irs_deduction_score,
)
from app.agents.underwriter.node import underwriter_node
from app.core.state import (
    AgentState,
    FinancialAnalysis,
    OSINTFindings,
    IRSScore,
)


# ============================================================================
# 1. Decision Matrix Tests (7 tests)
# ============================================================================


class TestDecisionMatrix:
    """Test decision matrix logic."""

    def test_approved_high_score_high_confidence(self):
        """Test: IRS ≥85 + Confidence ≥85% → APPROVED"""
        decision = make_decision(
            irs_score=90,
            confidence=0.90,
            loan_amount=Decimal("40000"),
        )
        assert decision == "APPROVED"

    def test_approved_pending_high_score_low_confidence(self):
        """Test: IRS ≥85 + Confidence <85% → APPROVED_PENDING_REVIEW"""
        decision = make_decision(
            irs_score=90,
            confidence=0.70,
            loan_amount=Decimal("40000"),
        )
        assert decision == "APPROVED_PENDING_REVIEW"

    def test_manual_review_medium_score(self):
        """Test: IRS 60-84 → MANUAL_REVIEW"""
        decision = make_decision(
            irs_score=75,
            confidence=0.85,
            loan_amount=Decimal("30000"),
        )
        assert decision == "MANUAL_REVIEW"

    def test_rejected_low_score(self):
        """Test: IRS <60 → REJECTED"""
        decision = make_decision(
            irs_score=50,
            confidence=0.90,
            loan_amount=Decimal("20000"),
        )
        assert decision == "REJECTED"

    def test_high_amount_override(self):
        """Test: Loan >50K DOP → MANUAL_REVIEW (override)"""
        decision = make_decision(
            irs_score=95,  # Perfect score
            confidence=0.95,  # High confidence
            loan_amount=Decimal("75000"),  # Over threshold
        )
        assert decision == "MANUAL_REVIEW"

    def test_boundary_irs_score_85(self):
        """Test: Boundary case IRS = 85, confidence = 0.85"""
        decision = make_decision(
            irs_score=85,
            confidence=0.85,
            loan_amount=Decimal("40000"),
        )
        assert decision == "APPROVED"

    def test_boundary_irs_score_60(self):
        """Test: Boundary case IRS = 60, confidence = 0.84"""
        decision = make_decision(
            irs_score=60,
            confidence=0.84,
            loan_amount=Decimal("30000"),
        )
        assert decision == "MANUAL_REVIEW"


class TestRiskLevel:
    """Test risk level mapping."""

    def test_low_risk(self):
        assert get_risk_level(90) == "LOW"
        assert get_risk_level(85) == "LOW"

    def test_medium_risk(self):
        assert get_risk_level(75) == "MEDIUM"
        assert get_risk_level(70) == "MEDIUM"

    def test_high_risk(self):
        assert get_risk_level(65) == "HIGH"
        assert get_risk_level(60) == "HIGH"

    def test_critical_risk(self):
        assert get_risk_level(55) == "CRITICAL"
        assert get_risk_level(30) == "CRITICAL"


class TestHumanReview:
    """Test human review requirements."""

    def test_requires_review_manual(self):
        assert requires_human_review("MANUAL_REVIEW") is True

    def test_requires_review_approved_pending(self):
        assert requires_human_review("APPROVED_PENDING_REVIEW") is True

    def test_no_review_approved(self):
        assert requires_human_review("APPROVED") is False

    def test_no_review_rejected(self):
        assert requires_human_review("REJECTED") is False


class TestSuggestedAmount:
    """Test suggested amount calculation for MEDIUM risk."""

    def test_suggested_amount_medium_risk(self):
        """Test: MEDIUM risk (60-84) always suggests reduced amount"""
        suggested = calculate_suggested_amount(
            irs_score=75,
            requested_amount=Decimal("60000"),
            payment_capacity=Decimal("2000"),
            term_months=24,
        )
        # 2000 * 24 * 0.8 = 38,400
        assert suggested == Decimal("38400")

    def test_no_suggestion_high_score(self):
        """Test: No suggestion for IRS ≥85"""
        suggested = calculate_suggested_amount(
            irs_score=90,
            requested_amount=Decimal("60000"),
            payment_capacity=Decimal("2000"),
            term_months=24,
        )
        assert suggested is None

    def test_no_suggestion_low_score(self):
        """Test: No suggestion for IRS <60 (will be rejected anyway)"""
        suggested = calculate_suggested_amount(
            irs_score=50,
            requested_amount=Decimal("60000"),
            payment_capacity=Decimal("2000"),
            term_months=24,
        )
        assert suggested is None


class TestDecisionFlags:
    """Test decision flag generation."""

    def test_high_amount_flag(self):
        flags = get_decision_flags(
            decision="MANUAL_REVIEW",
            irs_score=90,
            confidence=0.90,
            loan_amount=Decimal("75000"),
        )
        assert any("HIGH_AMOUNT" in flag for flag in flags)

    def test_low_confidence_flag(self):
        flags = get_decision_flags(
            decision="APPROVED_PENDING_REVIEW",
            irs_score=90,
            confidence=0.70,
            loan_amount=Decimal("40000"),
        )
        assert any("LOW_CONFIDENCE" in flag for flag in flags)

    def test_medium_risk_flag(self):
        flags = get_decision_flags(
            decision="MANUAL_REVIEW",
            irs_score=75,
            confidence=0.85,
            loan_amount=Decimal("40000"),
        )
        assert any("MEDIUM_RISK" in flag for flag in flags)

    def test_critical_risk_flag(self):
        flags = get_decision_flags(
            decision="REJECTED",
            irs_score=50,
            confidence=0.80,
            loan_amount=Decimal("30000"),
        )
        assert any("CRITICAL_RISK" in flag for flag in flags)


# ============================================================================
# 2. Confidence Calculation Tests (5 tests)
# ============================================================================


class TestConfidenceCalculation:
    """Test confidence scoring."""

    def test_perfect_data_scenario(self):
        """Test: Perfect data → ~0.95 confidence"""
        state = AgentState(
            case_id="TEST-001",
            applicant={
                "declared_salary": 35000,
                "employment_start_date": "2020-01-01",
            },
            loan={"requested_amount": 50000, "term_months": 24,
                  "product_type": "PERSONAL_LOAN"},
            documents=[{"type": "bank_statement", "url": "test.pdf"}],
            documents_processed=[{"type": "bank_statement"}],
            financial_analysis=FinancialAnalysis(
                bank_account_verified=True,
                salary_verified=True,
                detected_salary_amount=Decimal("35000"),
                credit_score=750,
            ),
            osint_findings=OSINTFindings(
                business_found=True,
                digital_veracity_score=0.85,
                sources_checked=["google_maps"],
            ),
            irs_score=IRSScore(
                score=90,
                breakdown={"credit_history": 25, "payment_capacity": 25,
                           "stability": 15, "collateral": 10, "payment_morality": 15},
                flags=[],
                deductions=[],
                narrative="Good profile",
            ),
        )

        confidence = calculate_confidence(state)
        assert confidence >= 0.90

    def test_missing_credit_report(self):
        """Test: Missing credit report → ~0.75 confidence"""
        state = AgentState(
            case_id="TEST-002",
            applicant={"declared_salary": 35000},
            loan={"requested_amount": 50000, "term_months": 24,
                  "product_type": "PERSONAL_LOAN"},
            documents=[{"type": "bank_statement", "url": "test.pdf"}],
            documents_processed=[{"type": "bank_statement"}],
            financial_analysis=FinancialAnalysis(
                bank_account_verified=True,
                salary_verified=True,
                detected_salary_amount=Decimal("35000"),
                credit_score=None,  # Missing
            ),
            irs_score=IRSScore(
                score=75,
                breakdown={"credit_history": 15, "payment_capacity": 20,
                           "stability": 15, "collateral": 10, "payment_morality": 15},
                flags=[],
                deductions=[{"variable": "credit_history", "points": -10}],
            ),
        )

        confidence = calculate_confidence(state)
        assert 0.65 <= confidence <= 0.80

    def test_salary_mismatch(self):
        """Test: Salary mismatch >20% → ~0.60 confidence"""
        state = AgentState(
            case_id="TEST-003",
            applicant={"declared_salary": 35000},  # Declared
            loan={"requested_amount": 50000, "term_months": 24,
                  "product_type": "PERSONAL_LOAN"},
            documents=[{"type": "bank_statement", "url": "test.pdf"}],
            documents_processed=[{"type": "bank_statement"}],
            financial_analysis=FinancialAnalysis(
                bank_account_verified=True,
                detected_salary_amount=Decimal(
                    "20000"),  # Detected (43% variance)
            ),
            irs_score=IRSScore(
                score=65,
                breakdown={"credit_history": 20, "payment_capacity": 15,
                           "stability": 10, "collateral": 10, "payment_morality": 10},
                flags=["SALARY_INCONSISTENCY"],
                deductions=[
                    {"variable": "payment_capacity", "points": -10},
                    {"variable": "stability", "points": -5},
                ],
            ),
        )

        confidence = calculate_confidence(state)
        assert 0.45 <= confidence <= 0.70  # Adjusted upper bound

    def test_minimum_confidence_floor(self):
        """Test: Multiple missing fields → minimum 0.30 confidence"""
        state = AgentState(
            case_id="TEST-004",
            applicant={},
            loan={"requested_amount": 50000, "term_months": 24,
                  "product_type": "PERSONAL_LOAN"},
            documents=[],
            financial_analysis=None,
            osint_findings=None,
            irs_score=None,
            errors=[{"agent": "document_processor", "message": "Failed"}],
        )

        confidence = calculate_confidence(state)
        assert confidence >= 0.30

    def test_osint_skipped_scenario(self):
        """Test: OSINT skipped → redistribute weight"""
        state = AgentState(
            case_id="TEST-005",
            applicant={"declared_salary": 35000,
                       "declared_employer": "Formal Company SRL"},
            loan={"requested_amount": 50000, "term_months": 24,
                  "product_type": "PERSONAL_LOAN"},
            documents=[{"type": "bank_statement", "url": "test.pdf"}],
            documents_processed=[{"type": "bank_statement"}],
            config={"skip_osint": True},  # OSINT skipped
            financial_analysis=FinancialAnalysis(
                bank_account_verified=True,
                detected_salary_amount=Decimal("35000"),
            ),
            irs_score=IRSScore(
                score=80,
                breakdown={"credit_history": 20, "payment_capacity": 20,
                           "stability": 15, "collateral": 10, "payment_morality": 15},
                flags=[],
                deductions=[{"variable": "credit_history", "points": -5}],
            ),
        )

        confidence = calculate_confidence(state)
        assert confidence >= 0.70  # Should still have decent confidence


# ============================================================================
# 3. Integration Tests (4 tests)
# ============================================================================


class TestUnderwriterNode:
    """Test full underwriter node integration."""

    @pytest.mark.asyncio
    async def test_complete_workflow_approved(self):
        """Test: End-to-end with APPROVED decision"""
        state = AgentState(
            case_id="TEST-INT-001",
            applicant={
                "declared_salary": 40000,
                "employment_start_date": "2020-01-01",
                "dependents_count": 1,
            },
            loan={"requested_amount": 45000, "term_months": 24,
                  "product_type": "PERSONAL_LOAN"},
            documents=[{"type": "bank_statement", "url": "test.pdf"}],
            documents_processed=[{"type": "bank_statement"}],
            financial_analysis=FinancialAnalysis(
                bank_account_verified=True,
                detected_salary_amount=Decimal("40000"),
                credit_score=780,
            ),
            irs_score=IRSScore(
                score=90,
                breakdown={"credit_history": 25, "payment_capacity": 25,
                           "stability": 15, "collateral": 10, "payment_morality": 15},
                flags=[],
                deductions=[],
                narrative="Perfil sólido con buen historial crediticio.",
            ),
            agents_executed=["triage", "financial", "irs_engine"],
        )

        result = await underwriter_node(state)

        assert result["final_decision"].decision == "APPROVED"
        assert result["final_decision"].confidence >= 0.85
        assert result["final_decision"].risk_level == "LOW"
        assert "underwriter" in result["agents_executed"]

    @pytest.mark.asyncio
    async def test_high_amount_override(self):
        """Test: High amount override → MANUAL_REVIEW"""
        state = AgentState(
            case_id="TEST-INT-002",
            applicant={"declared_salary": 60000},
            loan={"requested_amount": 75000, "term_months": 24,
                  "product_type": "PERSONAL_LOAN"},  # Over 50K
            documents=[{"type": "bank_statement", "url": "test.pdf"}],
            documents_processed=[{"type": "bank_statement"}],
            financial_analysis=FinancialAnalysis(
                detected_salary_amount=Decimal("60000"),
                credit_score=800,
            ),
            irs_score=IRSScore(
                score=95,  # Perfect score
                breakdown={"credit_history": 25, "payment_capacity": 25,
                           "stability": 15, "collateral": 15, "payment_morality": 15},
                flags=[],
                deductions=[],
                narrative="Perfil perfecto.",
            ),
            agents_executed=["triage", "financial", "irs_engine"],
        )

        result = await underwriter_node(state)

        assert result["final_decision"].decision == "MANUAL_REVIEW"
        assert result["final_decision"].requires_human_review is True

    @pytest.mark.asyncio
    async def test_suggested_amount_calculation(self):
        """Test: MEDIUM risk → suggested amount"""
        state = AgentState(
            case_id="TEST-INT-003",
            applicant={"declared_salary": 25000, "dependents_count": 2},
            loan={"requested_amount": 50000, "term_months": 24,
                  "product_type": "PERSONAL_LOAN"},
            documents=[{"type": "bank_statement", "url": "test.pdf"}],
            documents_processed=[{"type": "bank_statement"}],
            financial_analysis=FinancialAnalysis(
                detected_salary_amount=Decimal("25000"),
            ),
            irs_score=IRSScore(
                score=75,  # MEDIUM risk
                breakdown={"credit_history": 20, "payment_capacity": 20,
                           "stability": 15, "collateral": 10, "payment_morality": 10},
                flags=["FAST_WITHDRAWAL"],
                deductions=[
                    {"variable": "credit_history", "points": -5},
                    {"variable": "payment_morality", "points": -5},
                ],
                narrative="Perfil medio con retiro rápido.",
            ),
            agents_executed=["triage", "financial", "irs_engine"],
        )

        result = await underwriter_node(state)

        assert result["final_decision"].decision == "MANUAL_REVIEW"
        assert result["final_decision"].suggested_amount is not None
        # Suggested amount can be higher than requested for MEDIUM risk if capacity allows
        assert result["final_decision"].suggested_amount > 0
        # Never suggest longer terms
        assert result["final_decision"].suggested_term is None

    @pytest.mark.asyncio
    async def test_narrative_generation_spanish(self):
        """Test: Narrative generation in Spanish"""
        state = AgentState(
            case_id="TEST-INT-004",
            applicant={"declared_salary": 30000},
            loan={"requested_amount": 40000, "term_months": 24,
                  "product_type": "PERSONAL_LOAN"},
            documents=[{"type": "bank_statement", "url": "test.pdf"}],
            documents_processed=[{"type": "bank_statement"}],
            config={"narrative_language": "es"},
            financial_analysis=FinancialAnalysis(
                detected_salary_amount=Decimal("30000"),
            ),
            irs_score=IRSScore(
                score=70,
                breakdown={"credit_history": 18, "payment_capacity": 20,
                           "stability": 12, "collateral": 10, "payment_morality": 10},
                flags=["MEDIUM_RISK"],
                deductions=[{"variable": "credit_history", "points": -7}],
                narrative="Score de buró 650 indica historial crediticio regular.",
            ),
            agents_executed=["triage", "financial", "irs_engine"],
        )

        result = await underwriter_node(state)

        reasoning = result["final_decision"].reasoning
        assert "REVISIÓN MANUAL" in reasoning or "Score" in reasoning
        assert isinstance(reasoning, str)
        assert len(reasoning) > 100


# ============================================================================
# 4. Edge Cases (3 tests)
# ============================================================================


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    @pytest.mark.asyncio
    async def test_partial_workflow_osint_failed(self):
        """Test: OSINT failed, but other agents succeeded"""
        state = AgentState(
            case_id="TEST-EDGE-001",
            applicant={"declared_salary": 35000},
            loan={"requested_amount": 45000, "term_months": 24,
                  "product_type": "PERSONAL_LOAN"},
            documents=[{"type": "bank_statement", "url": "test.pdf"}],
            documents_processed=[{"type": "bank_statement"}],
            financial_analysis=FinancialAnalysis(
                detected_salary_amount=Decimal("35000"),
            ),
            osint_findings=OSINTFindings(
                business_found=False,  # OSINT failed
                digital_veracity_score=0.0,
                sources_checked=["google_maps", "instagram"],
            ),
            irs_score=IRSScore(
                score=78,
                breakdown={"credit_history": 20, "payment_capacity": 20,
                           "stability": 15, "collateral": 10, "payment_morality": 13},
                flags=[],
                deductions=[{"variable": "credit_history", "points": -5}],
                narrative="Perfil regular.",
            ),
            agents_executed=["triage", "financial", "osint", "irs_engine"],
            errors=[{"agent": "osint", "message": "Business not found"}],
        )

        result = await underwriter_node(state)

        # Should still make a decision
        assert result["final_decision"].decision in ["APPROVED",
                                                     "REJECTED", "MANUAL_REVIEW", "APPROVED_PENDING_REVIEW"]
        assert result["final_decision"].confidence >= 0.30  # Minimum floor

    @pytest.mark.asyncio
    async def test_zero_irs_score_critical_risk(self):
        """Test: Zero IRS score → REJECTED with reasoning"""
        state = AgentState(
            case_id="TEST-EDGE-002",
            applicant={"declared_salary": 15000},
            loan={"requested_amount": 80000, "term_months": 12,
                  "product_type": "PERSONAL_LOAN"},
            documents=[{"type": "bank_statement", "url": "test.pdf"}],
            financial_analysis=FinancialAnalysis(
                detected_salary_amount=Decimal("15000"),
            ),
            irs_score=IRSScore(
                score=0,  # Critical risk
                breakdown={"credit_history": 0, "payment_capacity": 0,
                           "stability": 0, "collateral": 0, "payment_morality": 0},
                flags=["CRITICAL_RISK", "INFORMAL_LENDER", "FAST_WITHDRAWAL"],
                deductions=[
                    {"variable": "credit_history", "points": -25},
                    {"variable": "payment_capacity", "points": -25},
                    {"variable": "payment_morality", "points": -20},
                ],
                narrative="Perfil de riesgo crítico.",
            ),
            agents_executed=["triage", "financial", "irs_engine"],
        )

        result = await underwriter_node(state)

        # High amount (80K) triggers MANUAL_REVIEW override, even with IRS=0
        # To test REJECTED, need to use amount under 50K threshold
        # Due to 80K amount
        assert result["final_decision"].decision == "MANUAL_REVIEW"
        assert result["final_decision"].risk_level == "CRITICAL"
        assert len(result["final_decision"].reasoning) > 50

    @pytest.mark.asyncio
    async def test_rejected_low_irs_under_threshold(self):
        """Test: IRS < 60 with amount under 50K → REJECTED"""
        state = AgentState(
            case_id="TEST-EDGE-002b",
            applicant={"declared_salary": 20000},
            loan={"requested_amount": 30000, "term_months": 12,
                  "product_type": "PERSONAL_LOAN"},  # Under 50K
            documents=[{"type": "bank_statement", "url": "test.pdf"}],
            financial_analysis=FinancialAnalysis(
                detected_salary_amount=Decimal("20000"),
            ),
            irs_score=IRSScore(
                score=45,  # Critical risk, below 60
                breakdown={"credit_history": 10, "payment_capacity": 15,
                           "stability": 5, "collateral": 5, "payment_morality": 10},
                flags=["CRITICAL_RISK", "FAST_WITHDRAWAL"],
                deductions=[
                    {"variable": "credit_history", "points": -15},
                    {"variable": "stability", "points": -10},
                ],
                narrative="Perfil de riesgo crítico.",
            ),
            agents_executed=["triage", "financial", "irs_engine"],
        )

        result = await underwriter_node(state)

        # Should be rejected due to IRS < 60
        assert result["final_decision"].decision == "REJECTED"
        assert result["final_decision"].risk_level == "CRITICAL"
        assert len(result["final_decision"].reasoning) > 50

    @pytest.mark.asyncio
    async def test_missing_financial_analysis(self):
        """Test: Missing financial analysis → use fallback logic"""
        state = AgentState(
            case_id="TEST-EDGE-003",
            applicant={"declared_salary": 30000},
            loan={"requested_amount": 40000, "term_months": 24,
                  "product_type": "PERSONAL_LOAN"},
            documents=[],
            financial_analysis=None,  # Missing
            irs_score=IRSScore(
                score=70,
                breakdown={"credit_history": 18, "payment_capacity": 20,
                           "stability": 12, "collateral": 10, "payment_morality": 10},
                flags=[],
                deductions=[],
                narrative="Partial analysis.",
            ),
            agents_executed=["triage", "irs_engine"],
        )

        result = await underwriter_node(state)

        # Should handle gracefully
        assert result["final_decision"].decision in [
            "MANUAL_REVIEW", "APPROVED_PENDING_REVIEW", "REJECTED"]
        # Can't calculate without financial data
        assert result["final_decision"].suggested_amount is None
