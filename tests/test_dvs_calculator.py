"""
Unit tests for Digital Veracity Score (DVS) calculator.

Tests weighted scoring algorithm and edge cases.
"""

import pytest
from app.agents.osint.dvs_calculator import DVSCalculator, DVSResult
from app.tools.serpapi_client import GoogleMapsResult
from app.tools.instagram_scraper import InstagramResult
from app.tools.facebook_scraper import FacebookResult


class TestDVSCalculator:
    """Test DVS calculator functionality."""

    def test_perfect_score(self):
        """Test DVS calculation with all sources found and active."""
        calculator = DVSCalculator()

        google_maps = GoogleMapsResult(
            found=True,
            place_id="ChIJ123",
            rating=4.5,
            reviews_count=25,
            address="Calle Principal, Santo Domingo",
            address_match_score=0.9,
        )

        instagram = InstagramResult(
            found=True,
            username="colmado_bendicion",
            follower_count=500,
            post_count=50,
        )

        facebook = FacebookResult(
            found=True,
            page_url="https://facebook.com/colmadobendicion",
            likes_count=300,
        )

        result = calculator.calculate_dvs(
            google_maps=google_maps,
            instagram=instagram,
            facebook=facebook,
            declared_name="Colmado La Bendición",
        )

        # Should have high score (all sources found)
        assert result.score >= 0.7
        assert result.evidence_count == 3
        assert len(result.sources_checked) == 3
        assert result.confidence > 0.8

    def test_no_sources_found(self):
        """Test DVS calculation with no sources found."""
        calculator = DVSCalculator()

        google_maps = GoogleMapsResult(found=False)
        instagram = InstagramResult(found=False)
        facebook = FacebookResult(found=False)

        result = calculator.calculate_dvs(
            google_maps=google_maps,
            instagram=instagram,
            facebook=facebook,
            declared_name="Fake Business XYZ",
        )

        # Should have zero score
        assert result.score == 0.0
        assert result.evidence_count == 0
        assert len(result.sources_checked) == 3

    def test_partial_presence(self):
        """Test DVS calculation with partial online presence."""
        calculator = DVSCalculator()

        google_maps = GoogleMapsResult(
            found=True,
            reviews_count=3,  # Low reviews
            address="Los Mina",
            address_match_score=0.8,
        )

        instagram = InstagramResult(found=False)
        facebook = FacebookResult(found=False)

        result = calculator.calculate_dvs(
            google_maps=google_maps,
            instagram=instagram,
            facebook=facebook,
            declared_name="Colmado Los Mina",
        )

        # Should have moderate score (only Google Maps)
        assert 0.3 <= result.score <= 0.6
        assert result.evidence_count == 1

    def test_reviews_score_calculation(self):
        """Test reviews count scoring."""
        calculator = DVSCalculator()

        # >10 reviews = 1.0
        assert calculator._calculate_reviews_score(15) == 1.0

        # 5-10 reviews = 0.7
        assert calculator._calculate_reviews_score(7) == 0.7

        # 1-4 reviews = 0.4
        assert calculator._calculate_reviews_score(2) == 0.4

        # 0 reviews = 0.0
        assert calculator._calculate_reviews_score(0) == 0.0

    def test_instagram_score_calculation(self):
        """Test Instagram activity scoring."""
        calculator = DVSCalculator()

        # Active account (posts + followers)
        instagram_active = InstagramResult(
            found=True, post_count=50, follower_count=500
        )
        assert calculator._calculate_instagram_score(instagram_active) == 1.0

        # Low engagement
        instagram_low = InstagramResult(
            found=True, post_count=10, follower_count=50
        )
        assert calculator._calculate_instagram_score(instagram_low) == 0.6

        # Not found
        instagram_none = InstagramResult(found=False)
        assert calculator._calculate_instagram_score(instagram_none) == 0.0

    def test_facebook_score_calculation(self):
        """Test Facebook page scoring."""
        calculator = DVSCalculator()

        # Active page
        facebook_active = FacebookResult(found=True, likes_count=200)
        assert calculator._calculate_facebook_score(facebook_active) == 1.0

        # Low engagement
        facebook_low = FacebookResult(found=True, likes_count=50)
        assert calculator._calculate_facebook_score(facebook_low) == 0.4

        # Not found
        facebook_none = FacebookResult(found=False)
        assert calculator._calculate_facebook_score(facebook_none) == 0.0

    def test_fuzzy_match(self):
        """Test fuzzy string matching."""
        calculator = DVSCalculator()

        # Exact match
        assert calculator._fuzzy_match(
            "Colmado La Bendición", "colmado la bendición") == 1.0

        # Partial match
        similarity = calculator._fuzzy_match(
            "Colmado La Bendición", "Colmado Bendición")
        assert 0.7 <= similarity < 1.0

        # No match
        similarity = calculator._fuzzy_match("Colmado", "Restaurant")
        assert similarity < 0.5

    def test_confidence_calculation(self):
        """Test confidence score based on data completeness."""
        calculator = DVSCalculator()

        # All sources checked and found
        google_maps = GoogleMapsResult(found=True, reviews_count=10)
        instagram = InstagramResult(
            found=True, post_count=20, follower_count=200)
        facebook = FacebookResult(found=True, likes_count=150)

        result = calculator.calculate_dvs(
            google_maps=google_maps,
            instagram=instagram,
            facebook=facebook,
            declared_name="Test Business",
        )

        # High confidence (all sources checked and found)
        assert result.confidence >= 0.9

    def test_weight_distribution(self):
        """Test that weights sum to 1.0."""
        calculator = DVSCalculator()

        total_weight = sum(calculator.WEIGHTS.values())
        # Allow small floating point error
        assert abs(total_weight - 1.0) < 0.01
