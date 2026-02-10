"""
Manual test script for OSINT agent with real Dominican businesses.

Tests the OSINT workflow with actual business data to validate:
- Google Maps search accuracy
- Instagram/Facebook scraper functionality
- DVS calculation correctness
"""

import asyncio
from app.core.state import AgentState, TriageResult
from app.agents.osint.node import osint_researcher_node


async def test_real_business():
    """Test with a real Dominican informal business."""
    print("=" * 60)
    print("OSINT Manual Test - Real Dominican Business")
    print("=" * 60)

    # Test case: Popular colmado in Santo Domingo
    state = AgentState(
        case_id="TEST-001",
        applicant={
            "id": "001-0000000-0",
            "full_name": "Test Owner",
            "date_of_birth": "1985-01-01",
            "declared_salary": 50000.0,
            "declared_employer": "Colmado La Bendición",  # Business name
            "declared_address": "Los Mina, Santo Domingo Este",  # Business address
            "dependents_count": 2,
        },
        loan={
            "requested_amount": 75000.0,
            "term_months": 24,
            "product_type": "PERSONAL_LOAN",
        },
        documents=[],
        triage_result=TriageResult(
            status="PASSED",
            applicant_type="informal_business",
            required_documents=["bank_statement"],
            estimated_income=50000.0,
        ),
    )

    print(f"\nBusiness: {state.applicant['declared_employer']}")
    print(f"Address: {state.applicant['declared_address']}")
    print("\nRunning OSINT searches...")
    print("-" * 60)

    # Execute OSINT agent
    result = await osint_researcher_node(state)
    osint_findings = result["osint_findings"]

    # Display results
    print("\n📊 OSINT FINDINGS:")
    print(f"  Business Found: {osint_findings.business_found}")
    print(f"  DVS Score: {osint_findings.digital_veracity_score:.2f}")
    print(f"  Sources Checked: {', '.join(osint_findings.sources_checked)}")

    print("\n🔍 EVIDENCE:")
    for source, data in osint_findings.evidence.items():
        print(f"\n  {source.upper()}:")
        if isinstance(data, dict):
            for key, value in data.items():
                print(f"    {key}: {value}")
        else:
            print(f"    {data}")

    print("\n" + "=" * 60)

    # Interpretation
    if osint_findings.digital_veracity_score >= 0.7:
        print("✅ PASS: Business has strong online presence (DVS >= 70%)")
    elif osint_findings.digital_veracity_score >= 0.5:
        print("⚠️  REVIEW: Moderate online presence (50% <= DVS < 70%)")
    else:
        print("❌ FAIL: Weak or no online presence (DVS < 50%)")

    print("=" * 60)


async def test_nonexistent_business():
    """Test with a fake business (should return low DVS)."""
    print("\n\n" + "=" * 60)
    print("OSINT Manual Test - Nonexistent Business")
    print("=" * 60)

    state = AgentState(
        case_id="TEST-002",
        applicant={
            "id": "002-0000000-0",
            "full_name": "Fake Owner",
            "date_of_birth": "1990-01-01",
            "declared_salary": 30000.0,
            "declared_employer": "Fake Business XYZ 123456",
            "declared_address": "Nowhere Street, Fake City",
            "dependents_count": 0,
        },
        loan={
            "requested_amount": 50000.0,
            "term_months": 12,
            "product_type": "PERSONAL_LOAN",
        },
        documents=[],
        triage_result=TriageResult(
            status="PASSED",
            applicant_type="informal_business",
            required_documents=["bank_statement"],
            estimated_income=30000.0,
        ),
    )

    print(f"\nBusiness: {state.applicant['declared_employer']}")
    print(f"Address: {state.applicant['declared_address']}")
    print("\nRunning OSINT searches...")
    print("-" * 60)

    result = await osint_researcher_node(state)
    osint_findings = result["osint_findings"]

    print("\n📊 OSINT FINDINGS:")
    print(f"  Business Found: {osint_findings.business_found}")
    print(f"  DVS Score: {osint_findings.digital_veracity_score:.2f}")
    print(f"  Sources Checked: {', '.join(osint_findings.sources_checked)}")

    print("\n" + "=" * 60)

    if osint_findings.digital_veracity_score < 0.3:
        print("✅ EXPECTED: Fake business correctly identified (DVS < 30%)")
    else:
        print("⚠️  UNEXPECTED: Fake business has DVS >= 30%")

    print("=" * 60)


async def main():
    """Run all manual tests."""
    print("\n🧪 OSINT Agent Manual Testing Suite")
    print("Testing with real Dominican business data\n")

    try:
        # Test 1: Real business (should have high DVS)
        await test_real_business()

        # Test 2: Fake business (should have low DVS)
        await test_nonexistent_business()

        print("\n\n✅ Manual testing complete!")
        print("\nNext steps:")
        print("1. Review DVS scores and evidence")
        print("2. Test with more real businesses from different sectors")
        print("3. Validate 70% success rate threshold")

    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
