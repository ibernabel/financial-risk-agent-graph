from app.tools.labor_calculator import LaborCalculator
import os
import sys
from datetime import date
from decimal import Decimal

# Add the project root to sys.path to import app
sys.path.append(os.getcwd())


def test_labor_calculator():
    calc = LaborCalculator()

    # Case 1: Exactly 1 year, $30,000 salary
    # Notice: 28 days
    # Severance: 21 days
    # Christmas: Full $30,000
    start = date(2023, 1, 1)
    end = date(2023, 12, 31)
    salary = Decimal("30000")

    result = calc.calculate(start, end, salary)

    print("--- Case 1: 1 Year ---")
    print(f"Time: {result['time_worked_formatted']}")
    print(f"Daily: {result['avg_daily_salary']}")
    print(f"Notice Days: {result['notice']['days']} (Exp: 28)")
    print(f"Severance Days: {result['severance']['days']} (Exp: 21)")
    print(f"Christmas: {result['christmas_salary']['amount']} (Exp: 30000)")
    print(f"Total: {result['total_received']}")

    assert result['notice']['days'] == 28
    assert result['severance']['days'] == 21
    assert result['christmas_salary']['amount'] == Decimal("30000")

    # Case 2: 6 months, $50,000 salary
    # Notice: 14 days
    # Severance: 13 days
    # Christmas: ~half
    start = date(2024, 1, 1)
    end = date(2024, 6, 30)
    salary = Decimal("50000")

    result = calc.calculate(start, end, salary)

    print("\n--- Case 2: 6 Months ---")
    print(f"Time: {result['time_worked_formatted']}")
    print(f"Notice Days: {result['notice']['days']} (Exp: 14)")
    print(f"Severance Days: {result['severance']['days']} (Exp: 13)")
    print(f"Christmas: {result['christmas_salary']['amount']}")

    assert result['notice']['days'] == 14
    assert result['severance']['days'] == 13

    # Case 3: Error Handling
    print("\n--- Case 3: Error Handling ---")
    try:
        calc.calculate(date(2024, 1, 1), date(2023, 1, 1), Decimal("100"))
    except ValueError as e:
        print(f"Caught expected error: {e}")
        assert "cannot be before start date" in str(e)

    try:
        calc.calculate(date(2023, 1, 1), date(2024, 1, 1), Decimal("-100"))
    except ValueError as e:
        print(f"Caught expected error: {e}")
        assert "cannot be negative" in str(e)

    print("\nAll basic tests passed!")


if __name__ == "__main__":
    test_labor_calculator()
