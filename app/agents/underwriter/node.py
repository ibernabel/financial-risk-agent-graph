"""
Underwriter Agent Node - Final decision making.

Production implementation integrating decision matrix, confidence scoring,
and narrative generation for final credit decisions.
"""

from decimal import Decimal
from app.core.state import AgentState, FinalDecision
from app.agents.underwriter.decision_matrix import (
    make_decision,
    get_risk_level,
    requires_human_review,
    calculate_suggested_amount,
    get_decision_flags,
)
from app.agents.underwriter.confidence import calculate_confidence
from app.agents.underwriter.narrative import generate_narrative


async def underwriter_node(state: AgentState) -> dict:
    """
    Underwriter agent - makes final credit decision.

    Process:
    1. Calculate confidence score from all agent outputs
    2. Apply decision matrix (IRS + confidence + loan amount)
    3. Calculate suggested amount/term for MEDIUM risk cases
    4. Generate detailed reasoning narrative
    5. Return final decision with full justification

    Business Rules (Stakeholder-Approved 2026-02-12):
    - IRS ≥85 + Confidence ≥85% → APPROVED
    - IRS ≥85 + Confidence <85% → APPROVED_PENDING_REVIEW
    - IRS 60-84 → MANUAL_REVIEW (always suggest reduced amount)
    - IRS <60 → REJECTED
    - Loan >50K DOP → MANUAL_REVIEW (override)

    Args:
        state: Current agent state with outputs from all previous agents

    Returns:
        State update with final_decision
    """
    # Extract required data
    irs_score_value = state.irs_score.score if state.irs_score else 0
    loan_amount = Decimal(str(state.loan["requested_amount"]))
    term_months = state.loan["term_months"]

    # Calculate confidence score
    confidence = calculate_confidence(state)

    # Make final decision using decision matrix
    decision = make_decision(irs_score_value, confidence, loan_amount)
    risk_level = get_risk_level(irs_score_value)

    # Calculate suggested amount for MEDIUM risk
    suggested_amount = None
    suggested_term = None

    if state.financial_analysis and state.financial_analysis.detected_salary_amount:
        # Calculate payment capacity (simplified - from Variable B logic)
        # TODO: Integrate full cash flow calculation from IRS engine
        monthly_salary = state.financial_analysis.detected_salary_amount
        dependents = state.applicant.get("dependents_count", 0)

        # Simple payment capacity: 30% of salary minus dependents adjustment
        payment_capacity = monthly_salary * Decimal("0.30")
        if dependents > 0:
            payment_capacity -= Decimal("2000") * \
                dependents  # DOP 2K per dependent

        # Calculate suggested amount for MEDIUM risk
        calculated_suggestion = calculate_suggested_amount(
            irs_score=irs_score_value,
            requested_amount=loan_amount,
            payment_capacity=max(payment_capacity, Decimal("0")),
            term_months=term_months,
        )

        if calculated_suggestion:
            suggested_amount = float(calculated_suggestion)
            # Never suggest longer terms (per stakeholder feedback)
            suggested_term = None

    # Get decision flags
    flags = get_decision_flags(
        decision, irs_score_value, confidence, loan_amount)

    # Merge with existing IRS flags
    all_flags = list(state.irs_score.flags) if state.irs_score else []
    all_flags.extend(flags)

    # Generate detailed reasoning narrative
    language = state.config.get("narrative_language", "es")
    reasoning = generate_narrative(
        state=state,
        decision=decision,
        risk_level=risk_level,
        confidence=confidence,
        suggested_amount=Decimal(str(suggested_amount)
                                 ) if suggested_amount else None,
        suggested_term=suggested_term,
        language=language,
    )

    # Build final decision
    final_decision = FinalDecision(
        decision=decision,
        confidence=confidence,
        risk_level=risk_level,
        suggested_amount=suggested_amount,
        suggested_term=suggested_term,
        reasoning=reasoning,
        requires_human_review=requires_human_review(decision),
    )

    return {
        "final_decision": final_decision,
        "current_step": "completed",
        "agents_executed": state.agents_executed + ["underwriter"],
    }
