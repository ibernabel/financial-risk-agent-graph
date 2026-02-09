"""
Unit tests for Triage Agent business rules.

Tests all validation rules (TR-01 through TR-05) from PRD Section 4.1.
"""

import pytest
from decimal import Decimal
from app.agents.triage.rules import TriageRules
from app.tools.minimum_wage import get_minimum_wage, classify_company_size


class TestAgeValidation:
    """Test age validation rules (TR-01)."""

    def test_age_too_young(self):
        """Test rejection for age < 18."""
        valid, reason = TriageRules.validate_age(17)
        assert not valid
        assert "Edad fuera de rango" in reason

    def test_age_too_old(self):
        """Test rejection for age > 65."""
        valid, reason = TriageRules.validate_age(66)
        assert not valid
        assert "Edad fuera de rango" in reason

    def test_age_minimum_boundary(self):
        """Test age = 18 (minimum boundary)."""
        valid, reason = TriageRules.validate_age(18)
        assert valid
        assert reason is None

    def test_age_maximum_boundary(self):
        """Test age = 65 (maximum boundary)."""
        valid, reason = TriageRules.validate_age(65)
        assert valid
        assert reason is None

    def test_age_valid_middle(self):
        """Test valid age in middle range."""
        valid, reason = TriageRules.validate_age(35)
        assert valid
        assert reason is None


class TestZoneValidation:
    """Test geographic zone validation rules (TR-02)."""

    def test_personal_loan_santo_domingo_allowed(self):
        """Test personal loan in Santo Domingo passes."""
        valid, reason = TriageRules.validate_zone(
            "Santo Domingo", "PERSONAL_LOAN")
        assert valid
        assert reason is None

    def test_personal_loan_distrito_nacional_allowed(self):
        """Test personal loan in Distrito Nacional passes."""
        valid, reason = TriageRules.validate_zone(
            "Distrito Nacional", "PERSONAL_LOAN")
        assert valid
        assert reason is None

    def test_personal_loan_other_province_rejected(self):
        """Test personal loan outside allowed zones rejected."""
        valid, reason = TriageRules.validate_zone("Santiago", "PERSONAL_LOAN")
        assert not valid
        assert "Zona geográfica no cubierta" in reason

    def test_savings_nationwide_coverage(self):
        """Test savings product allows any province."""
        valid, reason = TriageRules.validate_zone("Puerto Plata", "SAVINGS")
        assert valid
        assert reason is None

    def test_zone_case_insensitive(self):
        """Test zone validation is case-insensitive."""
        valid, reason = TriageRules.validate_zone(
            "santo domingo", "PERSONAL_LOAN")
        assert valid
        assert reason is None


class TestSalaryValidation:
    """Test salary validation rules (TR-03)."""

    def test_salary_below_minimum_wage_large(self):
        """Test rejection for salary < minimum wage (large company)."""
        minimum = get_minimum_wage("large")
        required = minimum * Decimal("1.10")  # 10% buffer

        valid, reason = TriageRules.validate_salary(
            required - Decimal("1"), "large")
        assert not valid
        assert "Ingreso insuficiente" in reason

    def test_salary_meets_minimum_with_buffer(self):
        """Test salary meeting minimum wage + 10% buffer."""
        minimum = get_minimum_wage("micro")
        required = minimum * Decimal("1.10")

        valid, reason = TriageRules.validate_salary(required, "micro")
        assert valid
        assert reason is None

    def test_salary_above_minimum(self):
        """Test salary well above minimum wage."""
        valid, reason = TriageRules.validate_salary(Decimal("50000"), "large")
        assert valid
        assert reason is None


class TestAmountValidation:
    """Test loan amount validation rules (TR-04)."""

    def test_amount_below_minimum(self):
        """Test rejection for amount < 5000 DOP."""
        valid, reason = TriageRules.validate_amount(
            Decimal("4999"), "PERSONAL_LOAN")
        assert not valid
        assert "Monto fuera de rango" in reason

    def test_amount_above_maximum(self):
        """Test rejection for amount > 100000 DOP."""
        valid, reason = TriageRules.validate_amount(
            Decimal("100001"), "PERSONAL_LOAN")
        assert not valid
        assert "Monto fuera de rango" in reason

    def test_amount_minimum_boundary(self):
        """Test amount = 5000 DOP (minimum boundary)."""
        valid, reason = TriageRules.validate_amount(
            Decimal("5000"), "PERSONAL_LOAN")
        assert valid
        assert reason is None

    def test_amount_maximum_boundary(self):
        """Test amount = 100000 DOP (maximum boundary)."""
        valid, reason = TriageRules.validate_amount(
            Decimal("100000"), "PERSONAL_LOAN")
        assert valid
        assert reason is None

    def test_amount_valid_middle(self):
        """Test valid amount in middle range."""
        valid, reason = TriageRules.validate_amount(
            Decimal("50000"), "PERSONAL_LOAN")
        assert valid
        assert reason is None


class TestAllRulesValidation:
    """Test combined validation (TR-05)."""

    def test_all_rules_pass(self):
        """Test applicant passing all rules."""
        all_valid, reasons = TriageRules.validate_all(
            age=30,
            province="Santo Domingo",
            salary=Decimal("30000"),
            amount=Decimal("50000"),
            product_type="PERSONAL_LOAN",
            company_size="medium",
        )
        assert all_valid
        assert len(reasons) == 0

    def test_multiple_failures(self):
        """Test applicant failing multiple rules."""
        all_valid, reasons = TriageRules.validate_all(
            age=17,  # Too young
            province="Santiago",  # Wrong zone
            salary=Decimal("10000"),  # Too low
            amount=Decimal("150000"),  # Too high
            product_type="PERSONAL_LOAN",
        )
        assert not all_valid
        assert len(reasons) == 4

    def test_single_failure_age(self):
        """Test single failure (age only)."""
        all_valid, reasons = TriageRules.validate_all(
            age=70,  # Too old
            province="Santo Domingo",
            salary=Decimal("30000"),
            amount=Decimal("50000"),
            product_type="PERSONAL_LOAN",
        )
        assert not all_valid
        assert len(reasons) == 1
        assert "Edad" in reasons[0]


class TestMinimumWageTools:
    """Test minimum wage helper functions."""

    def test_get_minimum_wage_large(self):
        """Test minimum wage for large company."""
        wage = get_minimum_wage("large")
        assert wage == Decimal("23000.00")

    def test_get_minimum_wage_micro(self):
        """Test minimum wage for micro company."""
        wage = get_minimum_wage("micro")
        assert wage == Decimal("16000.00")

    def test_classify_company_size_large(self):
        """Test company size classification for large company."""
        size = classify_company_size(600)
        assert size == "large"

    def test_classify_company_size_micro(self):
        """Test company size classification for micro company."""
        size = classify_company_size(5)
        assert size == "micro"

    def test_classify_company_size_none(self):
        """Test company size classification defaults to micro."""
        size = classify_company_size(None)
        assert size == "micro"
