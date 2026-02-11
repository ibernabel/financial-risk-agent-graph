"""
Text processing utilities for OSINT search accuracy.

Provides fuzzy matching, normalization, and text extraction functions.
"""

import re
import unicodedata
from typing import Optional
from pydantic import BaseModel, Field


class AddressComponents(BaseModel):
    """Extracted address components."""

    street: str = Field(default="", description="Street name and number")
    city: str = Field(default="", description="City name")
    municipality: str = Field(default="", description="Municipality/sector")
    postal_code: str = Field(default="", description="Postal code")
    country: str = Field(default="", description="Country")


def fuzzy_match(text1: str, text2: str) -> float:
    """
    Calculate fuzzy match score between two strings using Levenshtein distance.

    Args:
        text1: First string
        text2: Second string

    Returns:
        Similarity score (0.0-1.0)
    """
    if not text1 or not text2:
        return 0.0

    # Normalize
    text1 = text1.lower().strip()
    text2 = text2.lower().strip()

    if text1 == text2:
        return 1.0

    # Calculate Levenshtein distance
    distance = levenshtein_distance(text1, text2)
    max_len = max(len(text1), len(text2))

    # Convert to similarity score
    similarity = 1.0 - (distance / max_len)

    return max(0.0, min(1.0, similarity))


def levenshtein_distance(s1: str, s2: str) -> int:
    """
    Calculate Levenshtein distance between two strings.

    Args:
        s1: First string
        s2: Second string

    Returns:
        Edit distance
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            # Cost of insertions, deletions, or substitutions
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def normalize_phone(phone: str) -> str:
    """
    Normalize phone number to digits only.

    Args:
        phone: Phone number in any format

    Returns:
        Normalized phone (digits only)

    Examples:
        "+1 809-784-9433" → "18097849433"
        "(809) 784-9433" → "8097849433"
        "+1-849-626-6640" → "18496266640"
    """
    if not phone:
        return ""

    # Remove all non-digit characters
    digits = re.sub(r"\D", "", phone)

    return digits


def validate_phone_match(
    found_phone: Optional[str], expected_phone: Optional[str]
) -> tuple[bool, float]:
    """
    Validate phone number match.

    Args:
        found_phone: Phone found in search
        expected_phone: Expected phone number

    Returns:
        (is_match, confidence_score)
    """
    if not expected_phone:
        return True, 0.0  # No expected phone, skip validation

    if not found_phone:
        return False, 0.0  # Expected phone but not found

    # Normalize both
    normalized_found = normalize_phone(found_phone)
    normalized_expected = normalize_phone(expected_phone)

    # Exact match
    if normalized_found == normalized_expected:
        return True, 1.0

    # Match last 10 digits (handles country code variations)
    if len(normalized_found) >= 10 and len(normalized_expected) >= 10:
        if normalized_found[-10:] == normalized_expected[-10:]:
            return True, 0.9

    # Match last 7 digits (local number)
    if len(normalized_found) >= 7 and len(normalized_expected) >= 7:
        if normalized_found[-7:] == normalized_expected[-7:]:
            return True, 0.7

    return False, 0.0


def remove_accents(text: str) -> str:
    """
    Remove accents from text.

    Args:
        text: Text with accents

    Returns:
        Text without accents

    Examples:
        "Panadería José" → "Panaderia Jose"
        "La Bendición" → "La Bendicion"
    """
    if not text:
        return ""

    # Normalize to NFD (decomposed form)
    nfd = unicodedata.normalize("NFD", text)

    # Filter out combining characters (accents)
    without_accents = "".join(
        char for char in nfd if unicodedata.category(char) != "Mn")

    return without_accents


# Common Dominican business types
BUSINESS_TYPES = [
    "colmado",
    "panaderia",
    "panadería",
    "farmacia",
    "supermercado",
    "restaurante",
    "cafeteria",
    "cafetería",
    "salon",
    "salón",
    "barberia",
    "barbería",
    "tienda",
    "boutique",
    "ferreteria",
    "ferretería",
    "taller",
    "lavado",
    "car wash",
    "gym",
    "gimnasio",
]


def remove_business_type(name: str) -> str:
    """
    Remove common business type keywords from name.

    Args:
        name: Business name

    Returns:
        Name without business type

    Examples:
        "Colmado La Bendición" → "La Bendición"
        "Panadería José" → "José"
        "Deiquel Cake Toppers" → "Deiquel Cake Toppers" (no change)
    """
    if not name:
        return ""

    name_lower = name.lower()

    for business_type in BUSINESS_TYPES:
        # Remove at start
        if name_lower.startswith(business_type + " "):
            return name[len(business_type) + 1:].strip()

        # Remove at end
        if name_lower.endswith(" " + business_type):
            return name[: -(len(business_type) + 1)].strip()

    return name


def extract_address_components(address: str) -> AddressComponents:
    """
    Extract components from Dominican address.

    Args:
        address: Full address string

    Returns:
        AddressComponents with extracted parts

    Examples:
        "Calle Pdte. Antonio Guzmán Fernández, Santo Domingo Este 11809"
        → street="Calle Pdte. Antonio Guzmán Fernández",
           municipality="Santo Domingo Este",
           postal_code="11809"
    """
    if not address:
        return AddressComponents()

    components = AddressComponents()

    # Split by comma
    parts = [p.strip() for p in address.split(",")]

    if len(parts) >= 1:
        # First part is usually street
        components.street = parts[0]

    if len(parts) >= 2:
        # Second part may contain city/municipality and postal code
        second_part = parts[1]

        # Extract postal code (5 digits)
        postal_match = re.search(r"\b\d{5}\b", second_part)
        if postal_match:
            components.postal_code = postal_match.group()
            # Remove postal code from second part
            second_part = second_part.replace(
                components.postal_code, "").strip()

        # Remaining is municipality/city
        components.municipality = second_part

        # Common Dominican municipalities
        if "santo domingo" in second_part.lower():
            components.city = "Santo Domingo"
        elif "santiago" in second_part.lower():
            components.city = "Santiago"

    if len(parts) >= 3:
        # Third part might be country
        components.country = parts[2]

    return components


def validate_address_match(
    found_address: str, expected_address: str, threshold: float = 0.6
) -> tuple[bool, float]:
    """
    Validate address match using component-based scoring.

    Args:
        found_address: Address found in search
        expected_address: Expected address
        threshold: Minimum score for match (default: 0.6)

    Returns:
        (is_match, score)
    """
    if not expected_address:
        return True, 0.0  # No expected address, skip validation

    if not found_address:
        return False, 0.0  # Expected address but not found

    # Extract components
    found_parts = extract_address_components(found_address)
    expected_parts = extract_address_components(expected_address)

    scores = {}

    # Street match (most important)
    if found_parts.street and expected_parts.street:
        scores["street"] = fuzzy_match(
            found_parts.street, expected_parts.street)
    else:
        scores["street"] = 0.0

    # Municipality match
    if found_parts.municipality and expected_parts.municipality:
        scores["municipality"] = fuzzy_match(
            found_parts.municipality, expected_parts.municipality
        )
    else:
        scores["municipality"] = 0.0

    # Postal code match (exact)
    if found_parts.postal_code and expected_parts.postal_code:
        scores["postal_code"] = (
            1.0 if found_parts.postal_code == expected_parts.postal_code else 0.0
        )
    else:
        scores["postal_code"] = 0.0

    # Weighted average (street is most important)
    weights = {"street": 0.6, "municipality": 0.3, "postal_code": 0.1}

    final_score = sum(scores.get(k, 0.0) * weights[k] for k in weights)

    return final_score >= threshold, final_score
