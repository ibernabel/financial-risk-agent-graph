from app.tools.labor_calculator import LaborCalculator
import unittest
from datetime import date
from decimal import Decimal
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestLaborCalculator(unittest.TestCase):
    def setUp(self):
        self.calc = LaborCalculator()

    def test_user_example_case(self):
        """
        Validates the exact case provided by the user.
        Ingreso: 01/01/2020
        Salida: 31/12/2025
        Salario: 29,988.00

        Expected:
        - Daily: 1,258.41
        - Preaviso: 35,235.59 (28 days)
        - Cesantía: 173,661.10 (138 days)
        - Navidad: 29,988.00
        - Total: 238,884.69
        """
        start = date(2020, 1, 1)
        end = date(2025, 12, 31)
        salary = Decimal("29988.00")

        result = self.calc.calculate(start, end, salary)

        print("\n--- User Case Results ---")
        print(f"Daily: {result['avg_daily_salary']}")
        print(
            f"Notice: {result['notice']['amount']} ({result['notice']['days']} days)")
        print(
            f"Severance: {result['severance']['amount']} ({result['severance']['days']} days)")
        print(f"Christmas Salary: {result['christmas_salary']['amount']}")
        print(f"Total: {result['total_received']}")

        self.assertEqual(result['avg_daily_salary'], Decimal("1258.41"))
        self.assertEqual(result['notice']['amount'], Decimal("35235.59"))
        self.assertEqual(result['severance']['amount'], Decimal("173661.10"))
        self.assertEqual(result['christmas_salary']
                         ['amount'], Decimal("29988.00"))
        self.assertEqual(result['total_received'], Decimal("238884.69"))


if __name__ == '__main__':
    unittest.main()
