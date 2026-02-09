"""
Minimum wage lookup tool for Dominican Republic.

Provides current minimum wage rates by company size classification
as defined by Ministerio de Trabajo RD (Law 16-92, updated 2026).
"""

from decimal import Decimal
from typing import Literal

CompanySize = Literal["large", "medium", "small", "micro"]

# Minimum wage rates (DOP/month) - Updated Feb 2026
# Source: Ministerio de Trabajo RD (Law 16-92)
MINIMUM_WAGE_TABLE: dict[CompanySize, Decimal] = {
    "large": Decimal("23000.00"),  # 500+ employees
    "medium": Decimal("20500.00"),  # 51-500 employees
    "small": Decimal("18500.00"),  # 11-50 employees
    "micro": Decimal("16000.00"),  # 1-10 employees
}


def get_minimum_wage(company_size: CompanySize) -> Decimal:
    """
    Get minimum monthly wage by company size.

    Args:
        company_size: Company size classification
            - "large": 500+ employees
            - "medium": 51-500 employees
            - "small": 11-50 employees
            - "micro": 1-10 employees

    Returns:
        Minimum monthly wage in Dominican Pesos (DOP)

    Examples:
        >>> get_minimum_wage("large")
        Decimal('23000.00')
        >>> get_minimum_wage("micro")
        Decimal('16000.00')

    Note:
        TODO: For production, fetch from official API or database.
        Current implementation uses hardcoded values for Phase 2.
    """
    return MINIMUM_WAGE_TABLE.get(company_size, MINIMUM_WAGE_TABLE["micro"])


def classify_company_size(employee_count: int | None) -> CompanySize:
    """
    Classify company size based on employee count.

    Args:
        employee_count: Number of employees (None defaults to micro)

    Returns:
        Company size classification

    Examples:
        >>> classify_company_size(600)
        'large'
        >>> classify_company_size(25)
        'small'
        >>> classify_company_size(None)
        'micro'
    """
    if employee_count is None:
        return "micro"

    if employee_count >= 500:
        return "large"
    elif employee_count >= 51:
        return "medium"
    elif employee_count >= 11:
        return "small"
    else:
        return "micro"
