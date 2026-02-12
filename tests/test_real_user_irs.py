"""
Test IRS Engine with realistic test data.

This script tests the IRS scoring engine with realistic applicant data
to demonstrate the engine's functionality with a high-quality profile.
"""

from datetime import date

from app.core.state import AgentState, FinancialAnalysis
from app.agents.irs_engine.scoring import calculate_irs_score
from app.agents.irs_engine.narrative import NarrativeGenerator


def test_high_quality_profile():
    """Test IRS calculation with realistic high-quality applicant data."""

    # Create state with realistic test data (anonymized)
    state = AgentState(
        case_id="TEST-HIGH-QUALITY-PROFILE-001",
        applicant={
            # Anonymized applicant data
            "nid": "001-XXXXXXX-X",
            "first_name": "Juan",
            "last_name": "Pérez",
            "email": "juan.perez@example.com",
            "birthday": "1988-01-15",

            # Financial data
            "declared_salary": 120000.0,  # RD$120,000/month - high income
            "dependents_count": 3,
            "employment_start_date": "2020-01-15",  # 4+ years employment

            # Assets
            "has_vehicle": True,  # Owns vehicle
            "has_property": False,  # Rented housing

            # Additional info
            "marital_status": "married",
            "education_level": "secondary",
            "housing_type": "rented",
            "residence_start_date": "2020-01-15",
        },
        loan={
            # Loan request
            "requested_amount": 59750.0,  # RD$59,750
            "term_months": 36,
            "purpose": "Capital de Negocio",
        },
        documents=[],
        financial_analysis=FinancialAnalysis(
            # Credit report data
            credit_score=770,  # Excellent score

            # No risk flags
            risk_flags=[],

            # No detected salary from bank statements
            detected_salary_amount=None,
        ),
    )

    # Calculate IRS score
    print("=" * 80)
    print("IRS ENGINE TEST - HIGH-QUALITY PROFILE")
    print("=" * 80)
    print(
        f"\n📋 Applicant: {state.applicant['first_name']} {state.applicant['last_name']}")
    print(
        f"💰 Loan Request: RD${state.loan['requested_amount']:,.2f} for {state.loan['term_months']} months")
    print(f"📊 Credit Score: {state.financial_analysis.credit_score}")
    print(f"💵 Monthly Income: RD${state.applicant['declared_salary']:,.2f}")
    print(f"👨‍👩‍👧‍👦 Dependents: {state.applicant['dependents_count']}")
    print(f"🏢 Employment Since: {state.applicant['employment_start_date']}")
    print(f"🚗 Assets: Vehicle owned")
    print("\n" + "=" * 80)

    # Run IRS calculation
    result = calculate_irs_score(state)

    # Display results
    print(f"\n🎯 FINAL IRS SCORE: {result.final_score}/100")
    print(f"⚠️  RISK LEVEL: {result.risk_level}")
    print("\n📊 SCORE BREAKDOWN BY VARIABLE:")
    print(f"   A - Credit History:    {result.breakdown['credit_history']}/25")
    print(
        f"   B - Payment Capacity:  {result.breakdown['payment_capacity']}/25")
    print(f"   C - Stability:         {result.breakdown['stability']}/15")
    print(f"   D - Collateral:        {result.breakdown['collateral']}/15")
    print(
        f"   E - Payment Morality:  {result.breakdown['payment_morality']}/20")

    # Display deductions
    if result.deductions:
        print(f"\n⚠️  DEDUCTIONS APPLIED ({len(result.deductions)} total):")
        for deduction in result.deductions:
            print(
                f"   • [{deduction.rule_id}] -{deduction.points_deducted} pts: {deduction.reason}")
            print(f"     Evidence: {deduction.evidence}")
    else:
        print("\n✅ NO DEDUCTIONS - Perfect score!")

    # Generate Spanish narrative
    print("\n" + "=" * 80)
    print("NARRATIVE (SPANISH)")
    print("=" * 80)
    generator = NarrativeGenerator(language="es")
    narrative = generator.generate_narrative(result, state)
    print(narrative)

    # Generate English narrative
    print("\n" + "=" * 80)
    print("NARRATIVE (ENGLISH)")
    print("=" * 80)
    generator_en = NarrativeGenerator(language="en")
    narrative_en = generator_en.generate_narrative(result, state)
    print(narrative_en)

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

    return result


if __name__ == "__main__":
    result = test_high_quality_profile()
