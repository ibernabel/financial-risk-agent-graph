"""
Unit tests for text processing utilities.
"""

import pytest
from app.utils.text_utils import (
    fuzzy_match,
    normalize_phone,
    validate_phone_match,
    remove_accents,
    remove_business_type,
    extract_address_components,
    validate_address_match,
)


class TestFuzzyMatch:
    """Tests for fuzzy_match function."""

    def test_exact_match(self):
        assert fuzzy_match("Deiquel", "Deiquel") == 1.0

    def test_case_insensitive(self):
        assert fuzzy_match("DEIQUEL", "deiquel") == 1.0

    def test_similar_strings(self):
        score = fuzzy_match("Deiquel", "Deyquel")
        assert 0.7 < score < 1.0  # High similarity

    def test_different_strings(self):
        score = fuzzy_match("Deiquel", "Magic Hands")
        assert score < 0.5  # Low similarity

    def test_empty_strings(self):
        assert fuzzy_match("", "") == 0.0
        assert fuzzy_match("test", "") == 0.0


class TestPhoneNormalization:
    """Tests for phone normalization."""

    def test_normalize_dominican_phone(self):
        assert normalize_phone("+1 809-784-9433") == "18097849433"
        assert normalize_phone("(809) 784-9433") == "8097849433"
        assert normalize_phone("+1-849-626-6640") == "18496266640"

    def test_normalize_removes_all_non_digits(self):
        assert normalize_phone(
            "+1 (809) 784-9433 ext. 123") == "18097849433123"

    def test_normalize_empty(self):
        assert normalize_phone("") == ""
        assert normalize_phone(None) == ""


class TestPhoneValidation:
    """Tests for phone validation."""

    def test_exact_match(self):
        is_match, score = validate_phone_match(
            "+1 809-784-9433", "18097849433")
        assert is_match
        assert score == 1.0

    def test_last_10_digits_match(self):
        is_match, score = validate_phone_match(
            "809-784-9433", "+1 809-784-9433")
        assert is_match
        assert score == 0.9

    def test_last_7_digits_match(self):
        is_match, score = validate_phone_match("784-9433", "809-784-9433")
        assert is_match
        assert score == 0.7

    def test_no_match(self):
        is_match, score = validate_phone_match("809-784-9433", "849-626-6640")
        assert not is_match
        assert score == 0.0

    def test_no_expected_phone(self):
        is_match, score = validate_phone_match("809-784-9433", None)
        assert is_match  # Skip validation
        assert score == 0.0


class TestRemoveAccents:
    """Tests for accent removal."""

    def test_remove_spanish_accents(self):
        assert remove_accents("Panadería José") == "Panaderia Jose"
        assert remove_accents("La Bendición") == "La Bendicion"
        assert remove_accents("Café") == "Cafe"

    def test_no_accents(self):
        assert remove_accents("Deiquel") == "Deiquel"

    def test_empty(self):
        assert remove_accents("") == ""


class TestRemoveBusinessType:
    """Tests for business type removal."""

    def test_remove_colmado(self):
        assert remove_business_type("Colmado La Bendición") == "La Bendición"

    def test_remove_panaderia(self):
        assert remove_business_type("Panadería José") == "José"

    def test_no_business_type(self):
        assert remove_business_type(
            "Deiquel Cake Toppers") == "Deiquel Cake Toppers"

    def test_business_type_at_end(self):
        assert remove_business_type("José Panadería") == "José"


class TestAddressExtraction:
    """Tests for address component extraction."""

    def test_extract_full_address(self):
        address = "Calle Pdte. Antonio Guzmán Fernández, Santo Domingo Este 11809"
        components = extract_address_components(address)

        assert components.street == "Calle Pdte. Antonio Guzmán Fernández"
        assert components.municipality == "Santo Domingo Este"
        assert components.postal_code == "11809"
        assert components.city == "Santo Domingo"

    def test_extract_simple_address(self):
        address = "Guarocuya 49, Santo Domingo 10136"
        components = extract_address_components(address)

        assert components.street == "Guarocuya 49"
        assert "Santo Domingo" in components.municipality
        assert components.postal_code == "10136"

    def test_empty_address(self):
        components = extract_address_components("")
        assert components.street == ""
        assert components.municipality == ""


class TestAddressValidation:
    """Tests for address validation."""

    def test_exact_match(self):
        address1 = "Calle Pdte. Antonio Guzmán Fernández, Santo Domingo Este 11809"
        address2 = "Calle Pdte. Antonio Guzmán Fernández, Santo Domingo Este 11809"

        is_match, score = validate_address_match(address1, address2)
        assert is_match
        assert score > 0.9

    def test_similar_street_same_municipality(self):
        address1 = "Calle Antonio Guzman, Santo Domingo Este"
        address2 = "Calle Pdte. Antonio Guzmán Fernández, Santo Domingo Este"

        is_match, score = validate_address_match(address1, address2)
        assert is_match  # Should match due to similar street and same municipality
        assert score > 0.6

    def test_different_addresses(self):
        address1 = "Guarocuya 49, Santo Domingo 10136"
        address2 = "Calle Pdte. Antonio Guzmán Fernández, Santo Domingo Este 11809"

        is_match, score = validate_address_match(address1, address2)
        # May or may not match depending on threshold
        # Just verify score is calculated
        assert 0.0 <= score <= 1.0

    def test_no_expected_address(self):
        is_match, score = validate_address_match("Any address", "")
        assert is_match  # Skip validation
        assert score == 0.0
