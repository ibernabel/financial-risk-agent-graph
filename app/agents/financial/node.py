"""
Financial Analyst Agent Node - Bank statement parsing and pattern detection.

Implements real document parsing, transaction analysis, and risk pattern detection.
"""

from decimal import Decimal
from typing import Optional

from app.core.state import AgentState, FinancialAnalysis
from app.agents.financial.parsers import (
    parse_bhd_statement,
    parse_popular_statement,
    parse_banreservas_statement,
    BankStatementData,
)
from app.agents.financial.pattern_detector import PatternDetector
from app.tools.credit_parser import credit_parser_client, CreditReport


async def financial_analyst_node(state: AgentState) -> dict:
    """
    Financial analyst agent - parses documents and detects risk patterns.

    Workflow:
    1. Parse bank statement using appropriate bank parser
    2. Run pattern detection (FIN-01 to FIN-05)
    3. Parse credit report (if available)
    4. Calculate financial behavior score
    5. Return comprehensive FinancialAnalysis

    Args:
        state: Current agent state with document paths

    Returns:
        State update with financial_analysis
    """
    # Get document paths from state (documents is a list of dicts)
    bank_statement_path = None
    credit_report_path = None

    for doc in state.documents:
        if doc.get("type") == "bank_statement":
            bank_statement_path = doc.get("path")
        elif doc.get("type") == "credit_report":
            credit_report_path = doc.get("path")

    # Initialize result variables
    bank_data: Optional[BankStatementData] = None
    credit_report: Optional[CreditReport] = None
    detected_patterns = {}
    errors = []

    # Parse bank statement
    if bank_statement_path:
        try:
            # Detect bank from metadata or filename
            bank_name = _detect_bank_from_path(bank_statement_path)

            # Route to appropriate parser
            if bank_name == "BHD":
                bank_data = await parse_bhd_statement(bank_statement_path)
            elif bank_name == "Popular":
                bank_data = await parse_popular_statement(bank_statement_path)
            elif bank_name == "Banreservas":
                bank_data = await parse_banreservas_statement(bank_statement_path)
            else:
                # Default to BHD parser (works for most formats)
                bank_data = await parse_bhd_statement(bank_statement_path)

            # Run pattern detection
            declared_salary = Decimal(
                str(state.applicant.get("declared_salary", 0)))
            detected_patterns = PatternDetector.detect_all_patterns(
                transactions=bank_data.transactions,
                declared_salary=declared_salary,
                detected_salary_deposits=bank_data.summary.salary_deposits,
            )

        except Exception as e:
            errors.append(
                {"agent": "financial", "error": f"Bank parsing failed: {str(e)}"})

    # Parse credit report (if available)
    if credit_report_path:
        try:
            # Check if service is available first
            is_available = await credit_parser_client.health_check()
            if is_available:
                credit_report = await credit_parser_client.parse_credit_report(
                    credit_report_path
                )
            else:
                errors.append({
                    "agent": "financial",
                    "error": "Credit parser service unavailable"
                })
        except Exception as e:
            errors.append({
                "agent": "financial",
                "error": f"Credit parsing failed: {str(e)}"
            })

    # Build FinancialAnalysis
    financial_analysis = FinancialAnalysis(
        bank_account_verified=bank_data is not None,
        salary_verified=bool(bank_data and bank_data.summary.salary_deposits),
        detected_salary_amount=(
            bank_data.summary.salary_deposits[0]
            if bank_data and bank_data.summary.salary_deposits
            else None
        ),
        total_monthly_credits=(
            bank_data.summary.total_credits if bank_data else Decimal("0")
        ),
        total_monthly_debits=(
            bank_data.summary.total_debits if bank_data else Decimal("0")
        ),
        average_balance=(
            bank_data.summary.average_balance if bank_data else Decimal("0")
        ),
        credit_score=credit_report.score.score if credit_report else None,
        risk_flags=detected_patterns.get("flags", []),
        financial_behavior_score=_calculate_behavior_score(
            bank_data, detected_patterns),
    )

    return {
        "financial_analysis": financial_analysis,
        "current_step": "financial_analysis_completed",
        "agents_executed": state.agents_executed + ["financial_analyst"],
        "errors": state.errors + errors,
    }


def _detect_bank_from_path(path: str) -> str:
    """
    Detect bank name from file path or metadata.

    Args:
        path: File path to bank statement

    Returns:
        Bank name (BHD, Popular, Banreservas, or Unknown)
    """
    path_lower = path.lower()
    if "bhd" in path_lower:
        return "BHD"
    elif "popular" in path_lower:
        return "Popular"
    elif "banreservas" in path_lower or "reservas" in path_lower:
        return "Banreservas"
    return "Unknown"


def _calculate_behavior_score(
    bank_data: Optional[BankStatementData],
    patterns: dict,
) -> int:
    """
    Calculate financial behavior score (0-100).

    Scoring criteria:
    - Base score: 70
    - Fast withdrawal: -20
    - Informal lender: -30
    - NSF flags: -10 each
    - Salary inconsistency: -15
    - Salary consistent: +10
    - No risk flags: +10

    Args:
        bank_data: Parsed bank statement data
        patterns: Detected risk patterns

    Returns:
        Behavior score (0-100)
    """
    if not bank_data:
        return 50  # Neutral score if no data

    score = 70  # Base score

    # Apply penalties
    if patterns.get("fast_withdrawal_dates"):
        score -= 20
    if patterns.get("informal_lender_detected"):
        score -= 30
    if patterns.get("nsf_count", 0) > 0:
        score -= patterns["nsf_count"] * 10
    if patterns.get("salary_inconsistent"):
        score -= 15

    # Apply bonuses
    if not patterns.get("salary_inconsistent"):
        score += 10
    if not patterns.get("flags"):
        score += 10

    # Clamp to 0-100
    return max(0, min(100, score))
