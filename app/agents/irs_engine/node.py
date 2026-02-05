"""
IRS Engine Agent Node - Internal Risk Score calculation.

Stub implementation for Phase 1.
"""

from app.core.state import AgentState, IRSScore


async def irs_engine_node(state: AgentState) -> dict:
    """
    IRS engine stub - calculates Internal Risk Score.

    Phase 1: Returns mock IRS score.
    Future: Implement scoring algorithm with all 5 variables (A-E) and deduction rules.

    Args:
        state: Current agent state

    Returns:
        State update with irs_score
    """
    # Stub implementation - mock IRS score
    irs_score = IRSScore(
        score=78,
        breakdown={
            "credit_history": 22,
            "payment_capacity": 18,
            "stability": 15,
            "collateral": 8,
            "payment_morality": 15,
        },
        flags=["STUB_FLAG"],
        deductions=[
            {
                "variable": "payment_capacity",
                "rule": "Stub deduction for testing",
                "points_deducted": 7,
            }
        ],
        narrative="Stub IRS calculation for Phase 1 testing. "
        "Real scoring algorithm will be implemented in Phase 6.",
    )

    return {
        "irs_score": irs_score,
        "current_step": "irs_completed",
        "agents_executed": state.agents_executed + ["irs_engine"],
    }
