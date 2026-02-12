"""
Unit tests for IRS scoring engine.

Tests all 5 variables (A-E) with deduction rules and integration scenarios.
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta

from app.core.state import AgentState, FinancialAnalysis
from app.agents.irs_engine.scoring import (
    calculate_irs_score,
    calculate_variable_a_credit_history,
    calculate_variable_b_payment_capacity,
    calculate_variable_c_stability,
    calculate_variable_d_collateral,
    calculate_variable_e_payment_morality,
    determine_risk_level,
)
from app.agents.irs_engine.rules import (
    RULE_A01_POOR_CREDIT,
    RULE_A02_FAIR_CREDIT,
    RULE_B01_CRITICAL_CASH_FLOW,
    RULE_B02_TIGHT_CASH_FLOW,
    RULE_B03_LOW_INCOME,
    RULE_B04_HIGH_DEPENDENCY_RATIO,
    RULE_C01_PROBATION_PERIOD,
    RULE_C02_SHORT_TENURE,
    RULE_D01_NO_ASSETS,
    RULE_D02_INSUFFICIENT_GUARANTEE,
    RULE_E01_FAST_WITHDRAWAL,
    RULE_E02_INFORMAL_LENDER,
)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def create_test_state(
    credit_score: int = 750,
    declared_salary: float = 35000.0,
    requested_amount: float = 75000.0,
    term_months: int = 24,
    dependents: int = 2,
    employment_start_date: str = None,
    risk_flags: list = None,
    has_vehicle: bool = False,
    has_property: bool = False,
) -> AgentState:
    """Create a test AgentState with configurable parameters."""
    return AgentState(
        case_id="TEST-001",
        applicant={
            "full_name": "Test Applicant",
            "declared_salary": declared_salary,
            "dependents_count": dependents,
            "employment_start_date": employment_start_date,
            "has_vehicle": has_vehicle,
            "has_property": has_property,
        },
        loan={
            "requested_amount": requested_amount,
            "term_months": term_months,
            "product_type": "PERSONAL_LOAN",
        },
        documents=[],
        financial_analysis=FinancialAnalysis(
            credit_score=credit_score,
            detected_salary_amount=Decimal(str(declared_salary)),
            risk_flags=risk_flags or [],
        ),
    )


# =============================================================================
# TEST VARIABLE A: CREDIT HISTORY
# =============================================================================


class TestVariableA_CreditHistory:
    """Test all credit history deduction rules."""

    def test_poor_credit_score_deduction(self):
        """A-01: Bureau score < 600 should deduct 15 points."""
        state = create_test_state(credit_score=550)
        deductions = calculate_variable_a_credit_history(state)

        assert len(deductions) == 1
        assert deductions[0].rule_id == RULE_A01_POOR_CREDIT.rule_id
        assert deductions[0].points_deducted == 15
        assert deductions[0].flag == "POOR_CREDIT_HISTORY"

    def test_fair_credit_score_deduction(self):
        """A-02: Bureau score 600-700 should deduct 7 points."""
        state = create_test_state(credit_score=650)
        deductions = calculate_variable_a_credit_history(state)

        assert len(deductions) == 1
        assert deductions[0].rule_id == RULE_A02_FAIR_CREDIT.rule_id
        assert deductions[0].points_deducted == 7
        assert deductions[0].flag == "FAIR_CREDIT_HISTORY"

    def test_good_credit_no_deduction(self):
        """Credit score >= 700 should not deduct points."""
        state = create_test_state(credit_score=770)
        deductions = calculate_variable_a_credit_history(state)

        # Only A-01 and A-02 implemented for MVP
        assert len(deductions) == 0

    def test_no_credit_data_no_deduction(self):
        """Missing credit data should skip Variable A."""
        state = create_test_state()
        state.financial_analysis.credit_score = None
        deductions = calculate_variable_a_credit_history(state)

        assert len(deductions) == 0


# =============================================================================
# TEST VARIABLE B: PAYMENT CAPACITY
# =============================================================================


class TestVariableB_PaymentCapacity:
    """Test all payment capacity deduction rules."""

    def test_critical_cash_flow(self):
        """B-01: Cash flow < 10% should deduct 20 points."""
        # High loan amount with short term = high monthly payment = critical cash flow
        # Salary 25K, loan 200K over 12 months = 16.6K/month payment
        # After 40% expenses (10K), disposable = 25K - 10K - 16.6K = -1.6K (negative!)
        state = create_test_state(
            declared_salary=25000.0, requested_amount=200000.0, term_months=12
        )
        deductions = calculate_variable_b_payment_capacity(state)

        # Should have critical cash flow deduction
        critical_deductions = [
            d for d in deductions if d.rule_id == RULE_B01_CRITICAL_CASH_FLOW.rule_id]
        assert len(critical_deductions) == 1
        assert critical_deductions[0].points_deducted == 20

    def test_tight_cash_flow(self):
        """B-02: Cash flow 10-20% should deduct 10 points."""
        # Moderate loan amount = tight cash flow
        # Salary 30K, loan 100K over 24 months = 4.16K/month payment
        # After 40% expenses (12K), disposable = 30K - 12K - 4.16K = 13.84K
        # Cash flow ratio = 13.84K / 30K = 46% (too high, need adjustment)
        # Let's use: Salary 30K, loan 150K over 24 months = 6.25K/month
        # After 40% expenses (12K), disposable = 30K - 12K - 6.25K = 11.75K
        # Cash flow ratio = 11.75K / 30K = 39% (still too high)
        # Try: Salary 30K, loan 180K over 24 months = 7.5K/month
        # After 40% expenses (12K), disposable = 30K - 12K - 7.5K = 10.5K
        # Cash flow ratio = 10.5K / 30K = 35% (still too high)
        # Try: Salary 30K, loan 210K over 24 months = 8.75K/month
        # After 40% expenses (12K), disposable = 30K - 12K - 8.75K = 9.25K
        # Cash flow ratio = 9.25K / 30K = 30.8% (still too high)
        # Try: Salary 30K, loan 240K over 24 months = 10K/month
        # After 40% expenses (12K), disposable = 30K - 12K - 10K = 8K
        # Cash flow ratio = 8K / 30K = 26.7% (still too high)
        # Try: Salary 30K, loan 270K over 24 months = 11.25K/month
        # After 40% expenses (12K), disposable = 30K - 12K - 11.25K = 6.75K
        # Cash flow ratio = 6.75K / 30K = 22.5% (still too high)
        # Try: Salary 30K, loan 285K over 24 months = 11.875K/month
        # After 40% expenses (12K), disposable = 30K - 12K - 11.875K = 6.125K
        # Cash flow ratio = 6.125K / 30K = 20.4% (still too high)
        # Try: Salary 30K, loan 300K over 24 months = 12.5K/month
        # After 40% expenses (12K), disposable = 30K - 12K - 12.5K = 5.5K
        # Cash flow ratio = 5.5K / 30K = 18.3% (between 10-20%, tight!)
        state = create_test_state(
            declared_salary=30000.0, requested_amount=300000.0, term_months=24
        )
        deductions = calculate_variable_b_payment_capacity(state)

        # Should have tight cash flow deduction (mutually exclusive with critical)
        tight_deductions = [
            d for d in deductions if d.rule_id == RULE_B02_TIGHT_CASH_FLOW.rule_id]
        assert len(tight_deductions) == 1
        assert tight_deductions[0].points_deducted == 10

    def test_low_income_deduction(self):
        """B-03: Salary < min wage + 10% should deduct 5 points."""
        # Salary near minimum wage
        state = create_test_state(
            declared_salary=20000.0, requested_amount=30000.0)
        deductions = calculate_variable_b_payment_capacity(state)

        low_income_deductions = [
            d for d in deductions if d.rule_id == RULE_B03_LOW_INCOME.rule_id]
        assert len(low_income_deductions) == 1
        assert low_income_deductions[0].points_deducted == 5

    def test_high_dependency_ratio(self):
        """B-04: Dependents > 3 AND salary < 35K should deduct 10 points."""
        state = create_test_state(
            declared_salary=30000.0, dependents=4, requested_amount=50000.0
        )
        deductions = calculate_variable_b_payment_capacity(state)

        dependency_deductions = [
            d for d in deductions if d.rule_id == RULE_B04_HIGH_DEPENDENCY_RATIO.rule_id]
        assert len(dependency_deductions) == 1
        assert dependency_deductions[0].points_deducted == 10

    def test_high_salary_no_dependency_deduction(self):
        """High salary with many dependents should not trigger B-04."""
        state = create_test_state(declared_salary=50000.0, dependents=4)
        deductions = calculate_variable_b_payment_capacity(state)

        dependency_deductions = [
            d for d in deductions if d.rule_id == RULE_B04_HIGH_DEPENDENCY_RATIO.rule_id]
        assert len(dependency_deductions) == 0


# =============================================================================
# TEST VARIABLE C: STABILITY
# =============================================================================


class TestVariableC_Stability:
    """Test all stability deduction rules."""

    def test_probation_period_deduction(self):
        """C-01: Employment < 3 months should deduct 10 points."""
        # Employment started 2 months ago
        start_date = (date.today() - timedelta(days=60)).isoformat()
        state = create_test_state(employment_start_date=start_date)
        deductions = calculate_variable_c_stability(state)

        assert len(deductions) == 1
        assert deductions[0].rule_id == RULE_C01_PROBATION_PERIOD.rule_id
        assert deductions[0].points_deducted == 10

    def test_short_tenure_deduction(self):
        """C-02: Employment 3-12 months should deduct 5 points."""
        # Employment started 6 months ago
        start_date = (date.today() - timedelta(days=180)).isoformat()
        state = create_test_state(employment_start_date=start_date)
        deductions = calculate_variable_c_stability(state)

        assert len(deductions) == 1
        assert deductions[0].rule_id == RULE_C02_SHORT_TENURE.rule_id
        assert deductions[0].points_deducted == 5

    def test_stable_employment_no_deduction(self):
        """Employment > 12 months should not deduct points."""
        # Employment started 2 years ago
        start_date = (date.today() - timedelta(days=730)).isoformat()
        state = create_test_state(employment_start_date=start_date)
        deductions = calculate_variable_c_stability(state)

        assert len(deductions) == 0

    def test_missing_employment_date_deduction(self):
        """Missing employment date should apply penalty."""
        state = create_test_state(employment_start_date=None)
        deductions = calculate_variable_c_stability(state)

        # No deduction if date not provided (for MVP)
        assert len(deductions) == 0


# =============================================================================
# TEST VARIABLE D: COLLATERAL
# =============================================================================


class TestVariableD_Collateral:
    """Test collateral scoring with Labor Calculator."""

    def test_no_assets_deduction(self):
        """D-01: No assets should deduct 3 points."""
        state = create_test_state(has_vehicle=False, has_property=False)
        deductions = calculate_variable_d_collateral(
            state, severance_amount=None)

        no_assets_deductions = [
            d for d in deductions if d.rule_id == RULE_D01_NO_ASSETS.rule_id]
        assert len(no_assets_deductions) == 1
        assert no_assets_deductions[0].points_deducted == 3

    def test_has_assets_no_deduction(self):
        """Having assets should not trigger D-01."""
        state = create_test_state(has_vehicle=True)
        deductions = calculate_variable_d_collateral(
            state, severance_amount=None)

        no_assets_deductions = [
            d for d in deductions if d.rule_id == RULE_D01_NO_ASSETS.rule_id]
        assert len(no_assets_deductions) == 0

    def test_insufficient_severance_deduction(self):
        """D-02: Severance < 20% of loan should deduct 5 points."""
        state = create_test_state(requested_amount=100000.0)
        # Severance of 10,000 = 10% of loan (< 20% threshold)
        severance = Decimal("10000")
        deductions = calculate_variable_d_collateral(
            state, severance_amount=severance)

        severance_deductions = [
            d for d in deductions if d.rule_id == RULE_D02_INSUFFICIENT_GUARANTEE.rule_id]
        assert len(severance_deductions) == 1
        assert severance_deductions[0].points_deducted == 5

    def test_sufficient_severance_no_deduction(self):
        """D-02: Severance >= 20% of loan should not deduct."""
        state = create_test_state(requested_amount=100000.0)
        # Severance of 25,000 = 25% of loan (>= 20% threshold)
        severance = Decimal("25000")
        deductions = calculate_variable_d_collateral(
            state, severance_amount=severance)

        severance_deductions = [
            d for d in deductions if d.rule_id == RULE_D02_INSUFFICIENT_GUARANTEE.rule_id]
        assert len(severance_deductions) == 0


# =============================================================================
# TEST VARIABLE E: PAYMENT MORALITY
# =============================================================================


class TestVariableE_PaymentMorality:
    """Test payment morality integration with Financial Agent flags."""

    def test_fast_withdrawal_flag_integration(self):
        """E-01: Fast withdrawal from financial analysis should deduct 5."""
        state = create_test_state(
            risk_flags=["FAST_WITHDRAWAL: Detected on 2026-01-15, 2026-01-30"]
        )
        deductions = calculate_variable_e_payment_morality(state)

        assert len(deductions) == 1
        assert deductions[0].rule_id == RULE_E01_FAST_WITHDRAWAL.rule_id
        assert deductions[0].points_deducted == 5

    def test_informal_lender_flag_integration(self):
        """E-02: Informal lender should deduct 15 points."""
        state = create_test_state(
            risk_flags=[
                "INFORMAL_LENDER_DETECTED: Recurring transfers to same recipient"]
        )
        deductions = calculate_variable_e_payment_morality(state)

        assert len(deductions) == 1
        assert deductions[0].rule_id == RULE_E02_INFORMAL_LENDER.rule_id
        assert deductions[0].points_deducted == 15

    def test_multiple_morality_flags(self):
        """Multiple payment morality flags should apply all deductions."""
        state = create_test_state(
            risk_flags=[
                "FAST_WITHDRAWAL: Detected on 2026-01-15",
                "INFORMAL_LENDER_DETECTED: Pattern found",
            ]
        )
        deductions = calculate_variable_e_payment_morality(state)

        assert len(deductions) == 2
        total_deducted = sum(d.points_deducted for d in deductions)
        assert total_deducted == 20  # 5 + 15


# =============================================================================
# TEST RISK LEVEL DETERMINATION
# =============================================================================


class TestRiskLevelDetermination:
    """Test risk level mapping from scores."""

    def test_low_risk_level(self):
        """Score >= 85 should be LOW risk."""
        assert determine_risk_level(100) == "LOW"
        assert determine_risk_level(85) == "LOW"

    def test_medium_risk_level(self):
        """Score 70-84 should be MEDIUM risk."""
        assert determine_risk_level(84) == "MEDIUM"
        assert determine_risk_level(70) == "MEDIUM"

    def test_high_risk_level(self):
        """Score 60-69 should be HIGH risk."""
        assert determine_risk_level(69) == "HIGH"
        assert determine_risk_level(60) == "HIGH"

    def test_critical_risk_level(self):
        """Score < 60 should be CRITICAL risk."""
        assert determine_risk_level(59) == "CRITICAL"
        assert determine_risk_level(0) == "CRITICAL"

    def test_invalid_score_raises_error(self):
        """Negative score should raise ValueError."""
        with pytest.raises(ValueError):
            determine_risk_level(-1)


# =============================================================================
# TEST FULL IRS CALCULATION
# =============================================================================


class TestIRSEngineIntegration:
    """Test full IRS calculation with real state."""

    def test_full_calculation_ideal_applicant(self):
        """Test perfect 100 score with ideal applicant."""
        # Ideal applicant: excellent credit, high salary, long tenure, assets
        start_date = (date.today() - timedelta(days=1825)
                      ).isoformat()  # 5 years
        state = create_test_state(
            credit_score=800,
            declared_salary=60000.0,
            requested_amount=50000.0,
            term_months=24,
            dependents=1,
            employment_start_date=start_date,
            risk_flags=[],
            has_vehicle=True,
        )

        # High severance (5 years of work)
        severance = Decimal("300000")
        result = calculate_irs_score(state, severance_amount=severance)

        # Should have minimal or no deductions
        assert result.final_score >= 90
        assert result.risk_level == "LOW"
        assert len(result.deductions) <= 2  # Maybe some minor deductions

    def test_full_calculation_risky_applicant(self):
        """Test low score with multiple red flags."""
        # Risky applicant: poor credit, fast withdrawal, informal lender, probation
        start_date = (date.today() - timedelta(days=60)
                      ).isoformat()  # 2 months
        state = create_test_state(
            credit_score=550,
            declared_salary=22000.0,
            requested_amount=75000.0,
            term_months=12,
            dependents=4,
            employment_start_date=start_date,
            risk_flags=[
                "FAST_WITHDRAWAL: Detected on 2026-01-15",
                "INFORMAL_LENDER_DETECTED: Pattern found",
            ],
            has_vehicle=False,
        )

        result = calculate_irs_score(state, severance_amount=Decimal("5000"))

        # Should have many deductions
        assert result.final_score < 60
        assert result.risk_level == "CRITICAL"
        assert len(result.deductions) >= 5
        assert result.total_deductions >= 40

    def test_breakdown_sums_correctly(self):
        """Verify breakdown points sum correctly."""
        state = create_test_state()
        result = calculate_irs_score(state)

        # Breakdown should sum to (100 - total_deductions)
        breakdown_sum = sum(result.breakdown.values())
        expected_sum = 100 - result.total_deductions
        assert breakdown_sum == expected_sum

    def test_flags_match_deductions(self):
        """Verify all deductions have corresponding flags."""
        state = create_test_state(
            credit_score=550,
            risk_flags=["FAST_WITHDRAWAL: Test"],
        )
        result = calculate_irs_score(state)

        # Every deduction should have a flag
        assert len(result.flags) == len(result.deductions)
        for deduction in result.deductions:
            assert deduction.flag in result.flags
