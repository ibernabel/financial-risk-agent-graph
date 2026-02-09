"""
Business rules for Triage Agent eligibility validation.

Implements validation logic for applicant eligibility based on:
- Age requirements (18-65 years)
- Geographic zone coverage (configurable by product)
- Salary validation against minimum wage
- Loan amount range validation
"""

from decimal import Decimal
from typing import Literal

from app.tools.minimum_wage import CompanySize, get_minimum_wage

ProductType = Literal["PERSONAL_LOAN", "SAVINGS", "BUSINESS_LOAN"]


class TriageRules:
    """Business rules for applicant eligibility validation."""

    # Age constraints
    MIN_AGE = 18
    MAX_AGE = 65

    # Loan amount constraints (DOP)
    MIN_AMOUNT_DOP = Decimal("5000.00")
    MAX_AMOUNT_DOP = Decimal("100000.00")

    # Zone configuration by product type
    # For PERSONAL_LOAN: Only Santo Domingo province
    # For SAVINGS: Nationwide coverage
    ALLOWED_ZONES: dict[ProductType, list[str]] = {
        "PERSONAL_LOAN": ["Santo Domingo", "Distrito Nacional"],
        "SAVINGS": ["nationwide"],  # Special marker for all provinces
        "BUSINESS_LOAN": ["Santo Domingo", "Distrito Nacional", "Santiago"],
    }

    # Minimum salary buffer (10% above minimum wage)
    SALARY_BUFFER_PERCENTAGE = Decimal("0.10")

    @staticmethod
    def validate_age(age: int) -> tuple[bool, str | None]:
        """
        Validate applicant age is within allowed range.

        Args:
            age: Applicant age in years

        Returns:
            Tuple of (is_valid, rejection_reason)
            - (True, None) if age is valid
            - (False, reason) if age is invalid

        Examples:
            >>> TriageRules.validate_age(25)
            (True, None)
            >>> TriageRules.validate_age(17)
            (False, 'Edad fuera de rango permitido (18-65)')
        """
        if age < TriageRules.MIN_AGE or age > TriageRules.MAX_AGE:
            return (
                False,
                f"Edad fuera de rango permitido ({TriageRules.MIN_AGE}-{TriageRules.MAX_AGE})",
            )
        return (True, None)

    @staticmethod
    def validate_zone(province: str, product_type: ProductType) -> tuple[bool, str | None]:
        """
        Validate geographic coverage for product type.

        Args:
            province: Applicant's province/municipality
            product_type: Type of financial product

        Returns:
            Tuple of (is_valid, rejection_reason)

        Examples:
            >>> TriageRules.validate_zone("Santo Domingo", "PERSONAL_LOAN")
            (True, None)
            >>> TriageRules.validate_zone("Santiago", "PERSONAL_LOAN")
            (False, 'Zona geográfica no cubierta')
        """
        allowed_zones = TriageRules.ALLOWED_ZONES.get(product_type, [])

        # Check for nationwide coverage
        if "nationwide" in allowed_zones:
            return (True, None)

        # Normalize province name for comparison (case-insensitive)
        province_normalized = province.strip().lower()
        allowed_normalized = [zone.lower() for zone in allowed_zones]

        if province_normalized not in allowed_normalized:
            return (False, "Zona geográfica no cubierta")

        return (True, None)

    @staticmethod
    def validate_salary(
        salary: Decimal, company_size: CompanySize = "micro"
    ) -> tuple[bool, str | None]:
        """
        Validate salary meets minimum wage requirement with buffer.

        Args:
            salary: Declared monthly salary in DOP
            company_size: Company size classification (defaults to micro)

        Returns:
            Tuple of (is_valid, rejection_reason)

        Examples:
            >>> TriageRules.validate_salary(Decimal("25000"), "large")
            (True, None)
            >>> TriageRules.validate_salary(Decimal("15000"), "large")
            (False, 'Ingreso insuficiente (mínimo: DOP 25,300.00)')
        """
        minimum_wage = get_minimum_wage(company_size)
        required_salary = minimum_wage * \
            (1 + TriageRules.SALARY_BUFFER_PERCENTAGE)

        if salary < required_salary:
            return (
                False,
                f"Ingreso insuficiente (mínimo: DOP {required_salary:,.2f})",
            )

        return (True, None)

    @staticmethod
    def validate_amount(amount: Decimal, product_type: ProductType) -> tuple[bool, str | None]:
        """
        Validate loan amount is within allowed range.

        Args:
            amount: Requested loan amount in DOP
            product_type: Type of financial product

        Returns:
            Tuple of (is_valid, rejection_reason)

        Examples:
            >>> TriageRules.validate_amount(Decimal("50000"), "PERSONAL_LOAN")
            (True, None)
            >>> TriageRules.validate_amount(Decimal("150000"), "PERSONAL_LOAN")
            (False, 'Monto fuera de rango (DOP 5,000 - 100,000)')
        """
        # For now, all products use same range
        # TODO: Make configurable per product type
        if amount < TriageRules.MIN_AMOUNT_DOP or amount > TriageRules.MAX_AMOUNT_DOP:
            return (
                False,
                f"Monto fuera de rango (DOP {TriageRules.MIN_AMOUNT_DOP:,.0f} - {TriageRules.MAX_AMOUNT_DOP:,.0f})",
            )

        return (True, None)

    @staticmethod
    def validate_all(
        age: int,
        province: str,
        salary: Decimal,
        amount: Decimal,
        product_type: ProductType,
        company_size: CompanySize = "micro",
    ) -> tuple[bool, list[str]]:
        """
        Run all validation rules and collect rejection reasons.

        Args:
            age: Applicant age
            province: Applicant province
            salary: Declared monthly salary
            amount: Requested loan amount
            product_type: Financial product type
            company_size: Company size classification

        Returns:
            Tuple of (all_valid, rejection_reasons)
            - (True, []) if all rules pass
            - (False, [reasons]) if any rule fails

        Examples:
            >>> TriageRules.validate_all(
            ...     age=30,
            ...     province="Santo Domingo",
            ...     salary=Decimal("30000"),
            ...     amount=Decimal("50000"),
            ...     product_type="PERSONAL_LOAN"
            ... )
            (True, [])
        """
        rejection_reasons: list[str] = []

        # Validate age
        age_valid, age_reason = TriageRules.validate_age(age)
        if not age_valid and age_reason:
            rejection_reasons.append(age_reason)

        # Validate zone
        zone_valid, zone_reason = TriageRules.validate_zone(
            province, product_type)
        if not zone_valid and zone_reason:
            rejection_reasons.append(zone_reason)

        # Validate salary
        salary_valid, salary_reason = TriageRules.validate_salary(
            salary, company_size)
        if not salary_valid and salary_reason:
            rejection_reasons.append(salary_reason)

        # Validate amount
        amount_valid, amount_reason = TriageRules.validate_amount(
            amount, product_type)
        if not amount_valid and amount_reason:
            rejection_reasons.append(amount_reason)

        all_valid = len(rejection_reasons) == 0
        return (all_valid, rejection_reasons)
