from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP, getcontext
from typing import Dict, Any, Optional, TypedDict, Final

# Set precision high enough for intermediate calculations
getcontext().prec = 28


class CalculationBreakdown(TypedDict):
    """Represents a specific benefit calculation breakdown."""
    days: int
    amount: Decimal


class ChristmasSalaryBreakdown(TypedDict):
    """Represents the christmas salary calculation breakdown."""
    amount: Decimal
    notes: str


class LaborBenefitResult(TypedDict):
    """Complete result of labor benefits calculation."""
    avg_daily_salary: Decimal
    monthly_salary: Decimal
    time_worked_formatted: str
    notice: CalculationBreakdown
    severance: CalculationBreakdown
    christmas_salary: ChristmasSalaryBreakdown
    total_received: Decimal


class LaborCalculator:
    """
    Calculates labor benefits (Prestaciones Laborales) according to the Dominican Republic Labor Code.

    Attributes:
        DAILY_SALARY_DIVISOR (Decimal): 23.83 (Standard divisor for monthly to daily conversion).
    """

    DAILY_SALARY_DIVISOR: Final[Decimal] = Decimal("23.83")

    def __init__(self) -> None:
        """Initializes the calculator."""
        pass

    def _quantize(self, val: Decimal) -> Decimal:
        """Rounds a decimal to two decimal places using ROUND_HALF_UP."""
        return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _validate_inputs(self, start_date: date, end_date: date, monthly_salary: Decimal) -> None:
        """
        Validates the input parameters for the calculation.

        Args:
            start_date: The date the employment started.
            end_date: The date the employment ended.
            monthly_salary: The last monthly salary.

        Raises:
            ValueError: If end_date is before start_date or monthly_salary is negative.
        """
        if end_date < start_date:
            raise ValueError(
                f"End date ({end_date}) cannot be before start date ({start_date})")
        if monthly_salary < 0:
            raise ValueError(
                f"Monthly salary ({monthly_salary}) cannot be negative")

    def _calculate_time_difference_inclusive(self, start_date: date, end_date: date) -> Dict[str, int]:
        """
        Calculates time difference treating the range as inclusive for labor rights.
        Example: 01/01/2020 to 31/12/2020 is exactly 1 year.

        Args:
            start_date: Start date of employment.
            end_date: End date of employment.

        Returns:
            A dictionary with 'years', 'months', and 'days'.
        """
        # Logic: Calculate difference to the day AFTER the end date to make it inclusive
        target_date = end_date + timedelta(days=1)

        years = target_date.year - start_date.year
        months = target_date.month - start_date.month
        days = target_date.day - start_date.day

        if days < 0:
            months -= 1
            # Standard labor month adjustment (borrowing 30 days)
            days += 30
        if months < 0:
            years -= 1
            months += 12

        return {"years": years, "months": months, "days": days}

    def _calculate_notice_pay(self, years: int, months: int) -> int:
        """
        Calculates the number of notice days (Preaviso) based on Art. 76.

        Args:
            years: Full years worked.
            months: Extra months worked.

        Returns:
            Number of days for notice pay.
        """
        if years >= 1:
            return 28
        if months >= 6:
            return 14
        if months >= 3:
            return 7
        return 0

    def _calculate_severance_pay(self, years: int, months: int) -> int:
        """
        Calculates the number of severance days (Cesantía) based on Art. 80.

        Args:
            years: Full years worked.
            months: Extra months worked.

        Returns:
            Number of days for severance pay.
        """
        severance_days = 0
        # Base calculation on full years
        if years >= 5:
            severance_days = years * 23
        elif years >= 1:
            severance_days = years * 21
        elif months >= 6:
            severance_days = 13
        elif months >= 3:
            severance_days = 6

        # Add fractional months logic if worked for more than a year
        if years >= 1:
            if months >= 6:
                severance_days += 13
            elif months >= 3:
                severance_days += 6

        return severance_days

    def _calculate_christmas_salary(self, start_date: date, end_date: date, monthly_salary: Decimal) -> ChristmasSalaryBreakdown:
        """
        Calculates the Christmas Salary (Salario de Navidad) proportion for the current year.

        Args:
            start_date: Employment start date.
            end_date: Employment end date.
            monthly_salary: Last monthly salary.

        Returns:
            A breakdown containing the amount and notes.
        """
        start_of_end_year = date(end_date.year, 1, 1)
        effective_start = max(start_date, start_of_end_year)

        # Days in the final year (Inclusive)
        days_in_year = (end_date - effective_start).days + 1

        # If >= 360, consider it a full labor year (approximate)
        if days_in_year >= 360:
            amount = monthly_salary
            notes = "1 Año"
        else:
            # Proportion based on 365 days for precision in calculation
            amount = (monthly_salary * Decimal(days_in_year)) / Decimal("365")
            notes = f"{days_in_year} Días"

        return {
            "amount": self._quantize(amount),
            "notes": notes
        }

    def calculate(
        self,
        start_date: date,
        end_date: date,
        monthly_salary: Decimal,
        include_notice: bool = True,
        include_severance: bool = True,
        include_christmas_salary: bool = True,
        has_vacations: bool = False
    ) -> LaborBenefitResult:
        """
        Executes the full labor benefit calculation.

        Args:
            start_date: Employment start date.
            end_date: Employment end date.
            monthly_salary: Last monthly salary.
            include_notice: Whether to include 'Preaviso'. Defaults to True.
            include_severance: Whether to include 'Cesantía'. Defaults to True.
            include_christmas_salary: Whether to include 'Salario de Navidad'. Defaults to True.
            has_vacations: Unused in current version, but kept for signature compatibility.

        Returns:
            LaborBenefitResult dictionary with all calculations and breakdowns.
        """
        self._validate_inputs(start_date, end_date, monthly_salary)

        # 1. Base Rates
        avg_daily_salary = monthly_salary / self.DAILY_SALARY_DIVISOR

        # 2. Time Logic
        time_diff = self._calculate_time_difference_inclusive(
            start_date, end_date)
        years, months, days = time_diff["years"], time_diff["months"], time_diff["days"]
        total_time_str = f"{years} años, {months} meses, {days} días"

        # 3. Notice Pay
        notice_days = self._calculate_notice_pay(
            years, months) if include_notice else 0
        notice_amount = self._quantize(avg_daily_salary * Decimal(notice_days))

        # 4. Severance Pay
        severance_days = self._calculate_severance_pay(
            years, months) if include_severance else 0
        severance_amount = self._quantize(
            avg_daily_salary * Decimal(severance_days))

        # 5. Christmas Salary
        christmas = {"amount": Decimal("0.00"), "notes": "0 Días"}
        if include_christmas_salary:
            christmas = self._calculate_christmas_salary(
                start_date, end_date, monthly_salary)

        # 6. Totals
        total_received = self._quantize(
            notice_amount + severance_amount + christmas["amount"])

        return {
            "avg_daily_salary": self._quantize(avg_daily_salary),
            "monthly_salary": monthly_salary,
            "time_worked_formatted": total_time_str,
            "notice": {
                "days": notice_days,
                "amount": notice_amount
            },
            "severance": {
                "days": severance_days,
                "amount": severance_amount
            },
            "christmas_salary": christmas,
            "total_received": total_received
        }
