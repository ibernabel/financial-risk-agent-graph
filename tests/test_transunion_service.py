"""
Test script for TransUnion Credit Report Parser service.

Tests the /parse-credit-report endpoint with the test PDF file.
"""

import asyncio
from pathlib import Path
from app.tools.credit_parser import CreditParserClient


async def test_transunion_service():
    """Test TransUnion service with test_credit_report.pdf."""
    # Initialize client
    client = CreditParserClient(
        api_url="http://127.0.0.1:8000",
        api_key="test-api-key"
    )

    # Test health check
    print("Testing health check...")
    try:
        is_healthy = await client.health_check()
        print(f"✅ Health check: {'PASS' if is_healthy else 'FAIL'}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return

    # Test credit report parsing
    print("\nTesting credit report parsing...")
    test_file = Path(
        "creditflow_context/credit_report_parser_context/test_credit_report.pdf")

    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return

    try:
        credit_report = await client.parse_credit_report(str(test_file))

        print(f"✅ Credit report parsed successfully!")
        print(f"\n📊 Credit Report Summary:")
        print(f"  - Name: {credit_report.personal_data.full_name}")
        print(f"  - Credit Score: {credit_report.credit_score.score}")
        print(f"  - Score Factors: {len(credit_report.credit_score.factors)}")
        print(
            f"  - Open Accounts: {credit_report.account_summary.total_open_accounts}")
        print(
            f"  - Total Balance: ${credit_report.account_summary.total_balance:,.2f}")
        print(f"  - Payment Records: {len(credit_report.payment_records)}")
        print(f"  - Account Details: {len(credit_report.account_details)}")

        # Print first few factors
        if credit_report.credit_score.factors:
            print(f"\n📋 Top Score Factors:")
            for i, factor in enumerate(credit_report.credit_score.factors[:3], 1):
                print(f"  {i}. {factor}")

        return credit_report

    except Exception as e:
        print(f"❌ Credit report parsing failed: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    asyncio.run(test_transunion_service())
