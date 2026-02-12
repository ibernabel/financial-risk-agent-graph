"""
Core IRS scoring algorithm with deduction-based model.

Implements the Internal Risk Score calculation using 5 variables (A-E)
with full traceability and explainability.
"""

from decimal import Decimal
from typing import Optional
from datetime import datetime, date
from pydantic import BaseModel, Field

from app.core.state import AgentState
from .rules import (
    DeductionRule,
    VARIABLE_WEIGHTS,
    # Variable A rules
    RULE_A01_POOR_CREDIT,
    RULE_A02_FAIR_CREDIT,
    RULE_A03_EXCESSIVE_INQUIRIES,
    RULE_A04_ACTIVE_DELINQUENCY,
    RULE_A05_RISING_DEBT,
    # Variable B rules
    RULE_B01_CRITICAL_CASH_FLOW,
    RULE_B02_TIGHT_CASH_FLOW,
    RULE_B03_LOW_INCOME,
    RULE_B04_HIGH_DEPENDENCY_RATIO,
    # Variable C rules
    RULE_C01_PROBATION_PERIOD,
    RULE_C02_SHORT_TENURE,
    RULE_C03_RECENT_MOVE,
    RULE_C04_ADDRESS_INCONSISTENCY,
    # Variable D rules
    RULE_D01_NO_ASSETS,
    RULE_D02_INSUFFICIENT_GUARANTEE,
    # Variable E rules
    RULE_E01_FAST_WITHDRAWAL,
    RULE_E02_INFORMAL_LENDER,
    RULE_E03_DATA_INCONSISTENCY,
    RULE_E04_LOCATION_MISMATCH,
    # Thresholds
    CREDIT_SCORE_POOR,
    CREDIT_SCORE_FAIR,
    EXCESSIVE_INQUIRIES_THRESHOLD,
    CASH_FLOW_CRITICAL_PCT,
    CASH_FLOW_TIGHT_PCT,
    MINIMUM_WAGE_BUFFER_PCT,
    HIGH_DEPENDENCY_THRESHOLD,
    HIGH_DEPENDENCY_SALARY_THRESHOLD,
    PROBATION_PERIOD_MONTHS,
    SHORT_TENURE_MONTHS,
    RECENT_MOVE_MONTHS,
    SEVERANCE_LOAN_RATIO_THRESHOLD,
    RISK_LEVEL_LOW_THRESHOLD,
    RISK_LEVEL_MEDIUM_THRESHOLD,
    RISK_LEVEL_HIGH_THRESHOLD,
)


class DeductionRecord(BaseModel):
    """Record of a single deduction applied."""

    variable: str = Field(
        description="Variable name (credit_history, payment_capacity, etc.)")
    rule_id: str = Field(description="Rule identifier (A-01, B-03, etc.)")
    rule_name: str = Field(description="Flag name (POOR_CREDIT_HISTORY, etc.)")
    points_deducted: int = Field(description="Points deducted", ge=0)
    evidence: str = Field(description="Citation with specific data points")
    flag: str = Field(description="Risk flag identifier")


class IRSCalculationResult(BaseModel):
    """Complete IRS calculation with breakdown."""

    final_score: int = Field(
        description="Final IRS score (0-100)", ge=0, le=100)
    base_score: int = Field(
        default=100, description="Starting score before deductions")
    total_deductions: int = Field(description="Total points deducted", ge=0)
    breakdown: dict[str, int] = Field(
        description="Points remaining per variable after deductions"
    )
    deductions: list[DeductionRecord] = Field(
        default_factory=list, description="All deductions applied"
    )
    flags: list[str] = Field(default_factory=list,
                             description="All risk flags")
    risk_level: str = Field(
        description="Risk level: LOW, MEDIUM, HIGH, or CRITICAL")


def determine_risk_level(score: int) -> str:
    """Determine risk level from IRS score with explicit bounds."""
    if score >= RISK_LEVEL_LOW_THRESHOLD:
        return "LOW"
    if score >= RISK_LEVEL_MEDIUM_THRESHOLD:
        return "MEDIUM"
    if score >= RISK_LEVEL_HIGH_THRESHOLD:
        return "HIGH"
    if score >= 0:
        return "CRITICAL"
    raise ValueError(f"Invalid score: {score}")


def _apply_deduction(
    rule: DeductionRule, evidence: str, deductions: list[DeductionRecord]
) -> None:
    """
    Apply a deduction and record it.

    Args:
        rule: Deduction rule to apply
        evidence: Evidence citation for this deduction
        deductions: List to append deduction record to
    """
    deduction = DeductionRecord(
        variable=rule.variable,
        rule_id=rule.rule_id,
        rule_name=rule.flag_name,
        points_deducted=rule.max_deduction,
        evidence=evidence,
        flag=rule.flag_name,
    )
    deductions.append(deduction)


def calculate_variable_a_credit_history(state: AgentState) -> list[DeductionRecord]:
    """
    Calculate Variable A: Credit History deductions (25 pts max).

    Rules:
    - A-01: Bureau score < 600 (-15 pts)
    - A-02: Bureau score 600-700 (-7 pts)
    - A-03: Recent inquiries > 5 in 6 months (-5 pts)
    - A-04: Active delinquencies (-10 pts)
    - A-05: Debt trend increasing (-3 pts)

    Args:
        state: Current agent state with financial analysis

    Returns:
        List of deduction records
    """
    deductions: list[DeductionRecord] = []

    if not state.financial_analysis or state.financial_analysis.credit_score is None:
        # No credit data available - skip Variable A
        return deductions

    credit_score = state.financial_analysis.credit_score

    # A-01: Poor credit score
    if credit_score < CREDIT_SCORE_POOR:
        _apply_deduction(
            RULE_A01_POOR_CREDIT,
            f"Score de buró {credit_score} (< {CREDIT_SCORE_POOR})",
            deductions,
        )
    # A-02: Fair credit score (mutually exclusive with A-01)
    elif credit_score < CREDIT_SCORE_FAIR:
        _apply_deduction(
            RULE_A02_FAIR_CREDIT,
            f"Score de buró {credit_score} ({CREDIT_SCORE_POOR}-{CREDIT_SCORE_FAIR})",
            deductions,
        )

    # TODO: A-03, A-04, A-05 require credit report details
    # These will be implemented when credit report parsing includes:
    # - Recent inquiries count
    # - Active delinquencies flag
    # - Debt trend analysis

    return deductions


def calculate_variable_b_payment_capacity(state: AgentState) -> list[DeductionRecord]:
    """
    Calculate Variable B: Payment Capacity deductions (25 pts max).

    Rules:
    - B-01: Cash flow ratio < 10% (-20 pts)
    - B-02: Cash flow ratio 10-20% (-10 pts)
    - B-03: Salary < min wage + 10% (-5 pts)
    - B-04: Dependents > 3 AND salary < 35K DOP (-10 pts)

    Cash Flow Ratio = (Net Income - Expenses - Bureau Debt - Proposed Payment) / Net Income

    Args:
        state: Current agent state

    Returns:
        List of deduction records
    """
    deductions: list[DeductionRecord] = []

    # Get salary from financial analysis or declared salary
    salary = Decimal("0")
    if state.financial_analysis and state.financial_analysis.detected_salary_amount:
        salary = state.financial_analysis.detected_salary_amount
    elif "declared_salary" in state.applicant:
        salary = Decimal(str(state.applicant["declared_salary"]))

    if salary == 0:
        # Cannot calculate payment capacity without salary
        return deductions

    # Calculate proposed monthly payment (simplified: loan / term)
    loan_amount = Decimal(str(state.loan["requested_amount"]))
    term_months = state.loan["term_months"]
    proposed_payment = loan_amount / Decimal(str(term_months))

    # Simplified cash flow calculation (without expenses and bureau debt for MVP)
    # TODO: Integrate actual expenses and bureau debt from credit report
    net_income = salary
    # Assume 40% for basic expenses
    estimated_expenses = salary * Decimal("0.40")
    bureau_debt = Decimal("0")  # TODO: Get from credit report

    disposable_income = net_income - estimated_expenses - bureau_debt - proposed_payment
    cash_flow_ratio = disposable_income / \
        net_income if net_income > 0 else Decimal("0")

    # B-01: Critical cash flow
    if cash_flow_ratio < CASH_FLOW_CRITICAL_PCT:
        _apply_deduction(
            RULE_B01_CRITICAL_CASH_FLOW,
            f"Flujo de caja {cash_flow_ratio:.1%} (< {CASH_FLOW_CRITICAL_PCT:.0%})",
            deductions,
        )
    # B-02: Tight cash flow (mutually exclusive with B-01)
    elif cash_flow_ratio < CASH_FLOW_TIGHT_PCT:
        _apply_deduction(
            RULE_B02_TIGHT_CASH_FLOW,
            f"Flujo de caja {cash_flow_ratio:.1%} ({CASH_FLOW_CRITICAL_PCT:.0%}-{CASH_FLOW_TIGHT_PCT:.0%})",
            deductions,
        )

    # B-03: Low income (salary < minimum wage + 10%)
    # TODO: Get actual minimum wage from tools/minimum_wage.py
    minimum_wage = Decimal("21000")  # Hardcoded for MVP
    minimum_threshold = minimum_wage * (Decimal("1") + MINIMUM_WAGE_BUFFER_PCT)
    if salary < minimum_threshold:
        _apply_deduction(
            RULE_B03_LOW_INCOME,
            f"Salario RD${salary:,.2f} (< salario mínimo + 10%: RD${minimum_threshold:,.2f})",
            deductions,
        )

    # B-04: High dependency ratio
    dependents = state.applicant.get("dependents_count", 0)
    if dependents > HIGH_DEPENDENCY_THRESHOLD and salary < HIGH_DEPENDENCY_SALARY_THRESHOLD:
        _apply_deduction(
            RULE_B04_HIGH_DEPENDENCY_RATIO,
            f"{dependents} dependientes con salario RD${salary:,.2f} (< RD${HIGH_DEPENDENCY_SALARY_THRESHOLD:,.2f})",
            deductions,
        )

    return deductions


def calculate_variable_c_stability(state: AgentState) -> list[DeductionRecord]:
    """
    Calculate Variable C: Stability deductions (15 pts max).

    Rules:
    - C-01: Employment < 3 months (-10 pts)
    - C-02: Employment 3-12 months (-5 pts)
    - C-03: Residence < 6 months (-5 pts)
    - C-04: Address mismatch (-5 pts)

    Args:
        state: Current agent state

    Returns:
        List of deduction records
    """
    deductions: list[DeductionRecord] = []

    # C-01 & C-02: Employment tenure
    employment_start = state.applicant.get("employment_start_date")
    if employment_start:
        try:
            start_date = datetime.fromisoformat(employment_start).date()
            today = date.today()
            # Calculate months employed using year and month difference
            months_employed = (today.year - start_date.year) * 12 + (
                today.month - start_date.month
            )

            if months_employed < PROBATION_PERIOD_MONTHS:
                _apply_deduction(
                    RULE_C01_PROBATION_PERIOD,
                    f"Antigüedad laboral: {months_employed} meses (< {PROBATION_PERIOD_MONTHS} meses)",
                    deductions,
                )
            elif months_employed < SHORT_TENURE_MONTHS:
                _apply_deduction(
                    RULE_C02_SHORT_TENURE,
                    f"Antigüedad laboral: {months_employed} meses ({PROBATION_PERIOD_MONTHS}-{SHORT_TENURE_MONTHS} meses)",
                    deductions,
                )
        except (ValueError, TypeError):
            # Invalid date format - apply penalty for unknown tenure
            _apply_deduction(
                RULE_C02_SHORT_TENURE,
                "Fecha de inicio de empleo no proporcionada o inválida",
                deductions,
            )

    # C-03: Residence tenure
    # TODO: Implement when residence start date is available in state

    # C-04: Address inconsistency
    # TODO: Implement when address validation is available

    return deductions


def calculate_variable_d_collateral(
    state: AgentState, severance_amount: Optional[Decimal] = None
) -> list[DeductionRecord]:
    """
    Calculate Variable D: Collateral deductions (15 pts max).

    Rules:
    - D-01: No assets (-3 pts)
    - D-02: Severance < 20% of loan (-5 pts)

    Args:
        state: Current agent state
        severance_amount: Optional pre-calculated severance (prestaciones)

    Returns:
        List of deduction records
    """
    deductions: list[DeductionRecord] = []

    # D-01: No assets
    has_assets = state.applicant.get(
        "has_vehicle") or state.applicant.get("has_property")
    if not has_assets:
        _apply_deduction(
            RULE_D01_NO_ASSETS,
            "No se declararon activos (vehículo/propiedad)",
            deductions,
        )

    # D-02: Insufficient severance guarantee
    if severance_amount is not None:
        loan_amount = Decimal(str(state.loan["requested_amount"]))
        severance_ratio = severance_amount / \
            loan_amount if loan_amount > 0 else Decimal("0")

        if severance_ratio < SEVERANCE_LOAN_RATIO_THRESHOLD:
            _apply_deduction(
                RULE_D02_INSUFFICIENT_GUARANTEE,
                f"Prestaciones RD${severance_amount:,.2f} = {severance_ratio:.1%} del préstamo (< {SEVERANCE_LOAN_RATIO_THRESHOLD:.0%})",
                deductions,
            )

    return deductions


def calculate_variable_e_payment_morality(state: AgentState) -> list[DeductionRecord]:
    """
    Calculate Variable E: Payment Morality deductions (20 pts max).

    Rules:
    - E-01: Fast withdrawal pattern (-5 pts)
    - E-02: Informal lender pattern (-15 pts)
    - E-03: Interview data inconsistency (-10 pts)
    - E-04: Location mismatch (-10 pts)

    Args:
        state: Current agent state with financial analysis

    Returns:
        List of deduction records
    """
    deductions: list[DeductionRecord] = []

    if not state.financial_analysis:
        return deductions

    risk_flags = state.financial_analysis.risk_flags

    # E-01: Fast withdrawal pattern (from Financial Agent)
    fast_withdrawal_flags = [f for f in risk_flags if "FAST_WITHDRAWAL" in f]
    if fast_withdrawal_flags:
        # Extract dates from flag if available
        evidence = fast_withdrawal_flags[0]  # Use first flag as evidence
        _apply_deduction(RULE_E01_FAST_WITHDRAWAL, evidence, deductions)

    # E-02: Informal lender pattern (from Financial Agent)
    informal_lender_flags = [f for f in risk_flags if "INFORMAL_LENDER" in f]
    if informal_lender_flags:
        evidence = informal_lender_flags[0]
        _apply_deduction(RULE_E02_INFORMAL_LENDER, evidence, deductions)

    # E-03: Interview data inconsistency
    # TODO: Implement when interview data is integrated

    # E-04: Location mismatch
    # TODO: Implement when OSINT location validation is available

    return deductions


def calculate_irs_score(
    state: AgentState, severance_amount: Optional[Decimal] = None
) -> IRSCalculationResult:
    """
    Execute full IRS calculation using all 5 variables.

    Variables:
    - A: Credit History (25 pts)
    - B: Payment Capacity (25 pts)
    - C: Stability (15 pts)
    - D: Collateral (15 pts)
    - E: Payment Morality (20 pts)

    Args:
        state: Current agent state
        severance_amount: Optional pre-calculated severance

    Returns:
        Complete IRS calculation result
    """
    base_score = 100
    all_deductions: list[DeductionRecord] = []

    # Calculate deductions for each variable
    all_deductions.extend(calculate_variable_a_credit_history(state))
    all_deductions.extend(calculate_variable_b_payment_capacity(state))
    all_deductions.extend(calculate_variable_c_stability(state))
    all_deductions.extend(
        calculate_variable_d_collateral(state, severance_amount))
    all_deductions.extend(calculate_variable_e_payment_morality(state))

    # Calculate total deductions
    total_deductions = sum(d.points_deducted for d in all_deductions)
    final_score = max(0, base_score - total_deductions)  # Floor at 0

    # Calculate breakdown by variable
    breakdown = {}
    for var_name, max_points in VARIABLE_WEIGHTS.items():
        var_deductions = sum(
            d.points_deducted for d in all_deductions if d.variable == var_name
        )
        breakdown[var_name] = max(0, max_points - var_deductions)

    # Extract all flags
    flags = [d.flag for d in all_deductions]

    # Determine risk level
    risk_level = determine_risk_level(final_score)

    return IRSCalculationResult(
        final_score=final_score,
        base_score=base_score,
        total_deductions=total_deductions,
        breakdown=breakdown,
        deductions=all_deductions,
        flags=flags,
        risk_level=risk_level,
    )
