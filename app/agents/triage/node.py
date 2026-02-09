"""
Triage Agent Node - First-line eligibility filter.

Validates basic eligibility criteria before consuming compute resources.
Implements business rules TR-01 through TR-05 from PRD Section 4.1.
"""

from datetime import datetime
from decimal import Decimal

from app.core.state import AgentState, TriageResult
from app.agents.triage.rules import TriageRules, ProductType
from app.tools.minimum_wage import classify_company_size


async def triage_node(state: AgentState) -> dict:
    """
    Triage agent - validates basic eligibility criteria.

    Implements business rules:
    - TR-01: Age validation (18-65 years)
    - TR-02: Geographic zone filtering (configurable by product)
    - TR-03: Salary validation against minimum wage
    - TR-04: Loan amount range validation (5K-100K DOP)
    - TR-05: All rules pass → CONTINUE

    Args:
        state: Current agent state with applicant and loan data

    Returns:
        State update with triage_result
    """
    applicant = state.applicant
    loan = state.loan

    # Extract required fields
    try:
        # Calculate age from date of birth
        dob_str = applicant.get("date_of_birth")
        if dob_str:
            dob = datetime.strptime(dob_str, "%Y-%m-%d")
            age = (datetime.now() - dob).days // 365
        else:
            age = applicant.get("age", 0)

        province = applicant.get("declared_address", "").split(",")[-1].strip()
        salary = Decimal(str(applicant.get("declared_salary", 0)))
        amount = Decimal(str(loan.get("requested_amount", 0)))
        product_type: ProductType = loan.get("product_type", "PERSONAL_LOAN")

        # Classify company size (default to micro if not provided)
        employee_count = applicant.get("employer_employee_count")
        company_size = classify_company_size(employee_count)

    except (ValueError, KeyError) as e:
        # Handle missing or invalid data
        return {
            "triage_result": TriageResult(
                status="REJECTED",
                rejection_reason=f"Datos incompletos o inválidos: {str(e)}",
                eligibility_flags=["DATA_ERROR"],
            ),
            "current_step": "triage_rejected",
            "agents_executed": state.agents_executed + ["triage"],
            "errors": state.errors + [{"agent": "triage", "error": str(e)}],
        }

    # Run all validation rules
    all_valid, rejection_reasons = TriageRules.validate_all(
        age=age,
        province=province,
        salary=salary,
        amount=amount,
        product_type=product_type,
        company_size=company_size,
    )

    # Build triage result
    if all_valid:
        triage_result = TriageResult(
            status="PASSED",
            rejection_reason=None,
            eligibility_flags=[],
        )
        current_step = "triage_passed"
    else:
        triage_result = TriageResult(
            status="REJECTED",
            rejection_reason="; ".join(rejection_reasons),
            eligibility_flags=["ELIGIBILITY_FAILED"],
        )
        current_step = "triage_rejected"

    return {
        "triage_result": triage_result,
        "current_step": current_step,
        "agents_executed": state.agents_executed + ["triage"],
    }
