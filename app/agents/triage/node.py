"""
Triage Agent Node - First-line eligibility filter.

Stub implementation that always passes for Phase 1.
"""

from app.core.state import AgentState, TriageResult


async def triage_node(state: AgentState) -> dict:
    """
    Triage agent stub - validates basic eligibility criteria.

    Phase 1: Always returns PASSED status with mock data.
    Future: Implement business rules from PRD Section 4.1 (TR-01 through TR-05).

    Args:
        state: Current agent state

    Returns:
        State update with triage_result
    """
    # Stub implementation - always pass
    triage_result = TriageResult(
        status="PASSED",
        rejection_reason=None,
        eligibility_flags=["STUB_IMPLEMENTATION"],
    )

    return {
        "triage_result": triage_result,
        "current_step": "triage_completed",
        "agents_executed": state.agents_executed + ["triage"],
    }
