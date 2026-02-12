"""
IRS Engine Agent Node - Internal Risk Score calculation.

Implements the complete IRS scoring algorithm using 5 variables (A-E)
with deduction-based model and narrative generation.
"""

from decimal import Decimal
from typing import Optional

from app.core.state import AgentState, IRSScore
from .scoring import calculate_irs_score
from .narrative import NarrativeGenerator
from .labor_integration import LaborCalculatorClient


async def irs_engine_node(state: AgentState) -> dict:
    """
    IRS Engine - Calculates Internal Risk Score using 5 variables.

    Variables:
    - A: Credit History (25 pts)
    - B: Payment Capacity (25 pts)
    - C: Stability (15 pts)
    - D: Collateral (15 pts)
    - E: Payment Morality (20 pts)

    Args:
        state: Current agent state with financial analysis and applicant data

    Returns:
        State update with complete IRS score and narrative
    """
    # Calculate severance (prestaciones) for Variable D if employment data available
    severance_amount: Optional[Decimal] = None
    employment_start = state.applicant.get("employment_start_date")

    if employment_start:
        try:
            # Get salary from financial analysis or declared salary
            salary = Decimal("0")
            if (
                state.financial_analysis
                and state.financial_analysis.detected_salary_amount
            ):
                salary = state.financial_analysis.detected_salary_amount
            elif "declared_salary" in state.applicant:
                salary = Decimal(str(state.applicant["declared_salary"]))

            if salary > 0:
                labor_client = LaborCalculatorClient()
                severance_amount = labor_client.calculate_severance_from_state(
                    start_date_str=employment_start, monthly_salary=salary
                )
        except (ValueError, KeyError) as e:
            # Log error but continue without severance calculation
            print(f"Warning: Could not calculate severance: {e}")

    # Calculate IRS using scoring engine
    irs_result = calculate_irs_score(state, severance_amount=severance_amount)

    # Generate narrative (default Spanish, configurable)
    language = state.config.get("narrative_language", "es")
    narrative_gen = NarrativeGenerator(language=language)
    narrative = narrative_gen.generate_narrative(irs_result, state)

    # Convert to state schema
    irs_score = IRSScore(
        score=irs_result.final_score,
        breakdown={
            "credit_history": irs_result.breakdown["credit_history"],
            "payment_capacity": irs_result.breakdown["payment_capacity"],
            "stability": irs_result.breakdown["stability"],
            "collateral": irs_result.breakdown["collateral"],
            "payment_morality": irs_result.breakdown["payment_morality"],
        },
        flags=irs_result.flags,
        deductions=[
            {
                "variable": d.variable,
                "rule": f"{d.rule_id} - {d.evidence}",
                "points_deducted": d.points_deducted,
            }
            for d in irs_result.deductions
        ],
        narrative=narrative,
    )

    return {
        "irs_score": irs_score,
        "current_step": "irs_completed",
        "agents_executed": state.agents_executed + ["irs_engine"],
    }
