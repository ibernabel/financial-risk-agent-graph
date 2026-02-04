from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP, getcontext
from typing import Dict, Any, Optional

# Set precision high enough for intermediate calculations
getcontext().prec = 28


class LaborCalculator:
    """
    Calculates labor benefits (Prestaciones Laborales) according to the Dominican Republic Labor Code.

    Constants:
        DAILY_SALARY_DIVISOR (Decimal): 23.83 (Standard divisor for monthly to daily conversion)
    """

    DAILY_SALARY_DIVISOR = Decimal("23.83")

    def __init__(self):
        pass

    def _calculate_time_difference_inclusive(self, start_date: date, end_date: date) -> Dict[str, int]:
        """
        Calculates time difference treating the range as inclusive for labor rights.
        Example: 01/01/2020 to 31/12/2020 is exactly 1 year.
        """
        # Logic: Calculate difference to the day AFTER the end date to make it inclusive
        target_date = end_date + timedelta(days=1)

        years = target_date.year - start_date.year
        months = target_date.month - start_date.month
        days = target_date.day - start_date.day

        if days < 0:
            months -= 1
            # Standard labor month adjustment
            # Example: Feb 28 to Mar 28.
            # If Borrowing, we usually add 30 for standard labor calculations context
            days += 30
        if months < 0:
            years -= 1
            months += 12

        return {"years": years, "months": months, "days": days}

    def calculate(
        self,
        start_date: date,
        end_date: date,
        monthly_salary: Decimal,
        include_notice: bool = True,
        include_severance: bool = True,
        include_christmas_salary: bool = True,
        has_vacations: bool = False
    ) -> Dict[str, Any]:
        """
        Main calculation execution.
        """
        # 1. Base Calculations
        # Maintain high precision for the rate
        avg_daily_salary = monthly_salary / self.DAILY_SALARY_DIVISOR

        # 2. Time Logic
        time_diff = self._calculate_time_difference_inclusive(
            start_date, end_date)
        years = time_diff["years"]
        months = time_diff["months"]
        days = time_diff["days"]

        total_time_str = f"{years} años, {months} meses, {days} días"

        # 3. Notice (Preaviso) Rules - Art. 76
        notice_days = 0
        if include_notice:
            if years >= 1:
                notice_days = 28
            elif months >= 6:
                notice_days = 14
            elif months >= 3:
                notice_days = 7

        notice_amount = avg_daily_salary * Decimal(notice_days)

        # 4. Severance (Cesantía) Rules - Art. 80
        severance_days = 0
        if include_severance:
            # Base calculation on years
            if years >= 5:
                severance_days = years * 23
            elif years >= 1:
                severance_days = years * 21
            elif months >= 6:
                severance_days = 13
            elif months >= 3:
                severance_days = 6

            # Add fractional months logic if years >= 1
            if years >= 1:
                if months >= 6:
                    severance_days += 13
                elif months >= 3:
                    severance_days += 6

        severance_amount = avg_daily_salary * Decimal(severance_days)

        # 5. Christmas Salary (Salario de Navidad)
        christmas_salary_amount = Decimal("0.00")
        notes_christmas = "0 Días"

        if include_christmas_salary:
            # Calculate proportion of the LAST CALENDAR YEAR worked.
            # If the employee left in Dec 31, they worked the full year (assuming they started before Jan 1).

            start_of_end_year = date(end_date.year, 1, 1)
            effective_start = start_date if start_date > start_of_end_year else start_of_end_year

            # Days in the final year (Inclusive)
            days_in_year = (end_date - effective_start).days + 1

            # If > 360, consider it a full labor year
            if days_in_year >= 360:
                christmas_salary_amount = monthly_salary
                notes_christmas = "1 Año"
            else:
                christmas_salary_amount = (
                    # Approximation
                    monthly_salary * Decimal(days_in_year)) / Decimal("365")
                notes_christmas = f"{days_in_year} Días"

        # Final Rounding
        return {
            "avg_daily_salary": quantize(avg_daily_salary),
            "monthly_salary": monthly_salary,
            "time_worked_formatted": total_time_str,
            "notice": {
                "days": notice_days,
                "amount": quantize(notice_amount)
            },
            "severance": {
                "days": severance_days,
                "amount": quantize(severance_amount)
            },
            "christmas_salary": {
                "amount": quantize(christmas_salary_amount),
                "notes": notes_christmas
            },
            "total_received": quantize(quantize(notice_amount) + quantize(severance_amount) + quantize(christmas_salary_amount))
        }


def quantize(val: Decimal) -> Decimal:
    return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
