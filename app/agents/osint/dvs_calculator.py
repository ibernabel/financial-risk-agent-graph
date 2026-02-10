"""
Digital Veracity Score (DVS) calculator for OSINT findings.

Calculates weighted score based on multiple online presence factors.
"""

from typing import Optional
from pydantic import BaseModel, Field
from difflib import SequenceMatcher

from app.tools.serpapi_client import GoogleMapsResult
from app.tools.instagram_scraper import InstagramResult
from app.tools.facebook_scraper import FacebookResult


class DVSResult(BaseModel):
    """Digital Veracity Score calculation result."""

    score: float = Field(
        ge=0.0, le=1.0, description="Overall DVS score (0.0-1.0)")
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence based on data completeness"
    )
    breakdown: dict[str, float] = Field(
        default_factory=dict, description="Score breakdown by factor"
    )
    evidence_count: int = Field(
        default=0, description="Number of evidence sources found"
    )
    sources_checked: list[str] = Field(
        default_factory=list, description="List of sources that were checked"
    )


class DVSCalculator:
    """Digital Veracity Score calculator with weighted factors."""

    # Weights from PRD Section 3 (Agent 3: OSINT Researcher)
    WEIGHTS = {
        "google_maps_presence": 0.30,  # 30%
        "reviews_count": 0.15,  # 15%
        "instagram_activity": 0.25,  # 25%
        "facebook_page": 0.15,  # 15%
        "name_consistency": 0.15,  # 15%
    }

    def calculate_dvs(
        self,
        google_maps: Optional[GoogleMapsResult],
        instagram: Optional[InstagramResult],
        facebook: Optional[FacebookResult],
        declared_name: str,
    ) -> DVSResult:
        """
        Calculate Digital Veracity Score (0.0-1.0).

        Args:
            google_maps: Google Maps search result
            instagram: Instagram search result
            facebook: Facebook search result
            declared_name: Declared business name for consistency check

        Returns:
            DVSResult with score, confidence, and breakdown
        """
        breakdown = {}
        sources_checked = []
        evidence_count = 0

        # Factor 1: Google Maps Presence (30%)
        if google_maps:
            sources_checked.append("google_maps")
            maps_score = 1.0 if google_maps.found else 0.0
            breakdown["google_maps_presence"] = maps_score
            if google_maps.found:
                evidence_count += 1

        # Factor 2: Reviews Count (15%)
        if google_maps and google_maps.found:
            reviews_score = self._calculate_reviews_score(
                google_maps.reviews_count
            )
            breakdown["reviews_count"] = reviews_score
        else:
            breakdown["reviews_count"] = 0.0

        # Factor 3: Instagram Activity (25%)
        if instagram:
            sources_checked.append("instagram")
            instagram_score = self._calculate_instagram_score(instagram)
            breakdown["instagram_activity"] = instagram_score
            if instagram.found:
                evidence_count += 1

        # Factor 4: Facebook Page (15%)
        if facebook:
            sources_checked.append("facebook")
            facebook_score = self._calculate_facebook_score(facebook)
            breakdown["facebook_page"] = facebook_score
            if facebook.found:
                evidence_count += 1

        # Factor 5: Name Consistency (15%)
        name_consistency = self._calculate_name_consistency(
            declared_name=declared_name,
            google_maps=google_maps,
            instagram=instagram,
            facebook=facebook,
        )
        breakdown["name_consistency"] = name_consistency

        # Calculate weighted DVS
        dvs_score = sum(
            breakdown.get(factor, 0.0) * weight
            for factor, weight in self.WEIGHTS.items()
        )

        # Calculate confidence based on data completeness
        total_sources = 3  # Google Maps, Instagram, Facebook
        sources_attempted = len(sources_checked)
        data_quality = evidence_count / total_sources if total_sources > 0 else 0.0

        confidence = (sources_attempted / total_sources) * \
            (0.5 + 0.5 * data_quality)

        return DVSResult(
            score=round(dvs_score, 2),
            confidence=round(confidence, 2),
            breakdown=breakdown,
            evidence_count=evidence_count,
            sources_checked=sources_checked,
        )

    def _calculate_reviews_score(self, reviews_count: int) -> float:
        """
        Calculate score based on Google Maps reviews count.

        Scoring:
            >10 reviews = 1.0
            5-10 reviews = 0.7
            1-4 reviews = 0.4
            0 reviews = 0.0

        Args:
            reviews_count: Number of reviews

        Returns:
            Score (0.0-1.0)
        """
        if reviews_count > 10:
            return 1.0
        elif reviews_count >= 5:
            return 0.7
        elif reviews_count >= 1:
            return 0.4
        else:
            return 0.0

    def _calculate_instagram_score(self, instagram: InstagramResult) -> float:
        """
        Calculate score based on Instagram activity.

        Scoring:
            Posts in last 30d = 1.0
            Posts in last 90d = 0.6
            No recent posts = 0.0

        Args:
            instagram: Instagram search result

        Returns:
            Score (0.0-1.0)
        """
        if not instagram.found:
            return 0.0

        # Note: Without authentication, we can't get exact post dates
        # We estimate activity based on post count and follower count
        if instagram.post_count > 0 and instagram.follower_count > 100:
            return 1.0  # Assume active if has posts and followers
        elif instagram.post_count > 0:
            return 0.6  # Has posts but low followers
        else:
            return 0.0

    def _calculate_facebook_score(self, facebook: FacebookResult) -> float:
        """
        Calculate score based on Facebook page activity.

        Scoring:
            Active page = 1.0
            Inactive page = 0.4
            Not found = 0.0

        Args:
            facebook: Facebook search result

        Returns:
            Score (0.0-1.0)
        """
        if not facebook.found:
            return 0.0

        # Note: Without authentication, we can't get exact post dates
        # We estimate activity based on likes count
        if facebook.likes_count > 100:
            return 1.0  # Assume active if has significant likes
        elif facebook.likes_count > 0:
            return 0.4  # Has some presence but low engagement
        else:
            return 0.0

    def _calculate_name_consistency(
        self,
        declared_name: str,
        google_maps: Optional[GoogleMapsResult],
        instagram: Optional[InstagramResult],
        facebook: Optional[FacebookResult],
    ) -> float:
        """
        Calculate name consistency score across platforms.

        Scoring:
            Exact match = 1.0
            Partial match = 0.5
            Mismatch = 0.0

        Args:
            declared_name: Declared business name
            google_maps: Google Maps result
            instagram: Instagram result
            facebook: Facebook result

        Returns:
            Average consistency score (0.0-1.0)
        """
        scores = []

        # Compare with Google Maps
        if google_maps and google_maps.found and google_maps.address:
            # Use address as proxy for name (Google Maps doesn't return business name directly)
            similarity = self._fuzzy_match(declared_name, google_maps.address)
            scores.append(similarity)

        # Compare with Instagram
        if instagram and instagram.found and instagram.username:
            similarity = self._fuzzy_match(declared_name, instagram.username)
            scores.append(similarity)

        # Compare with Facebook
        if facebook and facebook.found and facebook.about:
            similarity = self._fuzzy_match(declared_name, facebook.about)
            scores.append(similarity)

        if not scores:
            return 0.0

        # Return average consistency
        avg_similarity = sum(scores) / len(scores)

        # Convert to score buckets
        if avg_similarity >= 0.8:
            return 1.0  # Exact match
        elif avg_similarity >= 0.5:
            return 0.5  # Partial match
        else:
            return 0.0  # Mismatch

    def _fuzzy_match(self, str1: str, str2: str) -> float:
        """
        Calculate fuzzy string similarity using SequenceMatcher.

        Args:
            str1: First string
            str2: Second string

        Returns:
            Similarity score (0.0-1.0)
        """
        if not str1 or not str2:
            return 0.0

        # Normalize strings
        str1_norm = str1.lower().strip()
        str2_norm = str2.lower().strip()

        # Calculate similarity
        return SequenceMatcher(None, str1_norm, str2_norm).ratio()
