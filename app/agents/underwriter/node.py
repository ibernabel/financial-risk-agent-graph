"""
Underwriter Agent Node - Final decision making.

Stub implementation for Phase 1.
"""

from app.core.state import AgentState, FinalDecision


async def underwriter_node(state: AgentState) -> dict:
    """
    Underwriter stub - makes final credit decision.

    Phase 1: Returns mock decision based on stub IRS score.
    Future: Implement decision matrix and confidence scoring.

    Args:
        state: Current agent state

    Returns:
        State update with final_decision
    """
    # Stub implementation - mock decision
    # Use IRS score from state if available
    irs_score_value = state.irs_score.score if state.irs_score else 78

    # Simple decision logic for stub
    if irs_score_value >= 85:
        decision = "APPROVED"
        risk_level = "LOW"
    elif irs_score_value >= 60:
        decision = "MANUAL_REVIEW"
        risk_level = "MEDIUM"
    else:
        decision = "REJECTED"
        risk_level = "HIGH"

    final_decision = FinalDecision(
        decision=decision,
        confidence=0.82,
        risk_level=risk_level,
        suggested_amount=None,
        suggested_term=None,
        reasoning="Stub decision for Phase 1 testing. "
        f"IRS score of {irs_score_value} falls into {risk_level} risk category. "
        "Real decision matrix will be implemented in Phase 7.",
        requires_human_review=(decision == "MANUAL_REVIEW"),
    )

    return {
        "final_decision": final_decision,
        "current_step": "completed",
        "agents_executed": state.agents_executed + ["underwriter"],
    }
