"""
Financial Analyst Agent Node - Bank statement parsing and pattern detection.

Stub implementation for Phase 1.
"""

from app.core.state import AgentState, FinancialAnalysis


async def financial_analyst_node(state: AgentState) -> dict:
    """
    Financial analyst stub - analyzes bank statements and detects patterns.

    Phase 1: Returns mock financial analysis.
    Future: Implement bank parsers and pattern detection (FIN-01 through FIN-05).

    Args:
        state: Current agent state

    Returns:
        State update with financial_analysis
    """
    # Stub implementation - mock financial analysis
    financial_analysis = FinancialAnalysis(
        total_credits=105000.0,
        total_debits=98000.0,
        average_balance=15000.0,
        salary_deposits=[35000.0, 35000.0, 35000.0],
        detected_payroll_day=15,
        detected_patterns=["STUB_PATTERN"],
    )

    return {
        "financial_analysis": financial_analysis,
        "current_step": "financial_analysis_completed",
        "agents_executed": state.agents_executed + ["financial_analyst"],
    }
