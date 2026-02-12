"""
Labor Calculator integration for IRS collateral scoring.

Wraps the LaborCalculator tool to calculate severance (prestaciones)
for Variable D: Collateral evaluation.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from app.tools.labor_calculator import LaborCalculator, LaborBenefitResult


class LaborCalculatorClient:
    """Client for calculating labor benefits for IRS collateral scoring."""

    def __init__(self):
        self.calculator = LaborCalculator()

    def calculate_severance_from_state(
        self,
        start_date_str: str,
        monthly_salary: Decimal,
        end_date_str: Optional[str] = None,
    ) -> Decimal:
        """
        Calculate total severance (prestaciones) for collateral evaluation.

        Only counts notice (preaviso) + severance (cesantía) as collateral.
        Christmas salary is excluded as it's not considered collateral.

        Args:
            start_date_str: Employment start date (ISO format "YYYY-MM-DD")
            monthly_salary: Current monthly salary
            end_date_str: Optional end date (defaults to today)

        Returns:
            Total severance amount (preaviso + cesantía)

        Raises:
            ValueError: If date format is invalid or dates are inconsistent
        """
        try:
            start = datetime.fromisoformat(start_date_str).date()
            end = (
                datetime.fromisoformat(end_date_str).date()
                if end_date_str
                else date.today()
            )
        except ValueError as e:
            raise ValueError(f"Invalid date format: {e}") from e

        result: LaborBenefitResult = self.calculator.calculate(
            start_date=start,
            end_date=end,
            monthly_salary=monthly_salary,
            include_notice=True,
            include_severance=True,
            include_christmas_salary=False,  # Not counted as collateral
            has_vacations=False,
        )

        # Only count notice + severance for collateral
        total_severance = result.notice.amount + result.severance.amount
        return total_severance

    def severance_as_loan_percentage(
        self, severance: Decimal, loan_amount: Decimal
    ) -> Decimal:
        """
        Calculate severance as percentage of requested loan.

        Args:
            severance: Total severance amount
            loan_amount: Requested loan amount

        Returns:
            Percentage (0.0 to 1.0+)
        """
        if loan_amount == 0:
            return Decimal("0")
        return severance / loan_amount

    def get_severance_breakdown(
        self,
        start_date_str: str,
        monthly_salary: Decimal,
        end_date_str: Optional[str] = None,
    ) -> dict:
        """
        Get detailed severance breakdown for narrative generation.

        Args:
            start_date_str: Employment start date
            monthly_salary: Current monthly salary
            end_date_str: Optional end date

        Returns:
            Dictionary with notice, severance, total, and time worked
        """
        start = datetime.fromisoformat(start_date_str).date()
        end = (
            datetime.fromisoformat(end_date_str).date()
            if end_date_str
            else date.today()
        )

        result: LaborBenefitResult = self.calculator.calculate(
            start_date=start,
            end_date=end,
            monthly_salary=monthly_salary,
            include_notice=True,
            include_severance=True,
            include_christmas_salary=False,
            has_vacations=False,
        )

        return {
            "notice_days": result.notice.days,
            "notice_amount": result.notice.amount,
            "severance_days": result.severance.days,
            "severance_amount": result.severance.amount,
            "total_severance": result.notice.amount + result.severance.amount,
            "time_worked": result.time_worked_formatted,
            "monthly_salary": result.monthly_salary,
        }
