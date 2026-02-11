"""
SerpAPI client for Google Maps and web search.

Provides OSINT capabilities for business verification using SerpAPI.
"""

import asyncio
from typing import Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from serpapi import GoogleSearch
import httpx

from app.core.config import settings


class GoogleMapsResult(BaseModel):
    """Result from Google Maps search."""

    found: bool = Field(description="Whether business was found")
    place_id: Optional[str] = Field(
        default=None, description="Google Maps place ID"
    )
    rating: Optional[float] = Field(default=None, description="Average rating")
    reviews_count: int = Field(default=0, description="Number of reviews")
    address: Optional[str] = Field(
        default=None, description="Business address")
    address_match_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Address fuzzy match score"
    )
    phone: Optional[str] = Field(default=None, description="Business phone")
    website: Optional[str] = Field(
        default=None, description="Business website")
    business_type: Optional[str] = Field(
        default=None, description="Type of business"
    )


class WebSearchResult(BaseModel):
    """Result from general web search."""

    title: str = Field(description="Result title")
    link: str = Field(description="Result URL")
    snippet: str = Field(description="Result snippet")
    position: int = Field(description="Result position")


class RateLimiter:
    """Token bucket rate limiter for API calls."""

    def __init__(self, rate_per_minute: int):
        """
        Initialize rate limiter.

        Args:
            rate_per_minute: Maximum requests per minute
        """
        self.rate_per_minute = rate_per_minute
        self.tokens = rate_per_minute
        self.last_update = datetime.now()
        self.lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until rate limit allows next call."""
        async with self.lock:
            now = datetime.now()
            time_passed = (now - self.last_update).total_seconds()

            # Refill tokens based on time passed
            self.tokens = min(
                self.rate_per_minute,
                self.tokens + (time_passed * self.rate_per_minute / 60),
            )
            self.last_update = now

            # Wait if no tokens available
            if self.tokens < 1:
                wait_time = (1 - self.tokens) * 60 / self.rate_per_minute
                await asyncio.sleep(wait_time)
                self.tokens = 1

            self.tokens -= 1


class SerpAPIClient:
    """Client for SerpAPI Google Maps and general search."""

    def __init__(self):
        """Initialize SerpAPI client with configuration."""
        self.api_key = settings.external.serpapi_key
        self.timeout = settings.external.serpapi_timeout
        self.rate_limiter = RateLimiter(settings.external.serpapi_rate_limit)

        if not self.api_key:
            raise ValueError(
                "SERPAPI_KEY not configured. Please set it in .env file."
            )

    async def search_google_maps(
        self,
        business_name: str,
        address: str,
        expected_phone: Optional[str] = None,
    ) -> GoogleMapsResult:
        """
        Search Google Maps for business location with multi-signal validation.

        Uses smart query strategy:
        1. Try business_name + city (extracted from address)
        2. Try business_name + full address
        3. Try business_name only

        Then rank results by relevance.

        Args:
            business_name: Name of the business to search
            address: Business address for context
            expected_phone: Optional phone number for validation

        Returns:
            GoogleMapsResult with best matching business

        Raises:
            Exception: If API call fails
        """
        await self.rate_limiter.acquire()

        try:
            # Import text utils
            from app.utils.text_utils import extract_address_components

            # Extract city/municipality from address for better query
            address_parts = extract_address_components(address)
            city_query = address_parts.municipality or address_parts.city

            # Dominican Republic coordinates (Santo Domingo center)
            # This helps SerpAPI prioritize Dominican businesses
            dr_location = "@18.4861,-69.9312,14z"

            # Build query variations:
            # 1. Exact match with quotes (most precise)
            # 2. Fuzzy match with city
            # 3. Fuzzy match with full address
            query_variations = [
                # Exact match + DR location
                (f'"{business_name}"', dr_location),
            ]

            if city_query:
                query_variations.append(
                    (f"{business_name} {city_query}", dr_location))

            query_variations.append((f"{business_name} {address}", None))
            query_variations.append((business_name, dr_location))

            # Try each query until we get results
            all_results = []
            for query, location in query_variations:
                # Build search params
                # Use Google Maps engine with type=search
                # This returns place_results for exact matches
                search_params = {
                    "q": query,
                    "engine": "google_maps",
                    "type": "search",
                    "api_key": self.api_key,
                }

                # Add location if specified (coordinates work better than text)
                if location:
                    search_params["ll"] = location

                # Execute search using SerpAPI
                search = GoogleSearch(search_params)

                # Get results (synchronous call, run in executor)
                loop = asyncio.get_event_loop()
                results = await loop.run_in_executor(None, search.get_dict)

                # Check place_results first (exact match from type=search)
                place_result = results.get("place_results", {})
                if place_result and place_result.get("title"):
                    # Extract type (can be a list)
                    business_type = place_result.get("type")
                    if isinstance(business_type, list) and business_type:
                        business_type = business_type[0]

                    all_results.append({
                        "title": place_result.get("title"),
                        "address": place_result.get("address"),
                        "phone": place_result.get("phone"),
                        "rating": place_result.get("rating"),
                        "reviews": place_result.get("reviews"),
                        "website": place_result.get("website"),
                        "place_id": place_result.get("place_id"),
                        "type": business_type,
                    })
                    break  # Found exact match, stop searching

                # Fallback to local_results
                local_results = results.get("local_results", [])
                if local_results:
                    all_results.extend(local_results[:3])
                    break  # Found results, stop searching

            if not all_results:
                return GoogleMapsResult(found=False)

            # Remove duplicates (by place_id)
            seen_place_ids = set()
            unique_results = []
            for result in all_results:
                place_id = result.get("place_id")
                if place_id and place_id not in seen_place_ids:
                    seen_place_ids.add(place_id)
                    unique_results.append(result)
                elif not place_id:  # No place_id, keep it
                    unique_results.append(result)

            # Rank results by relevance
            ranked_results = self._rank_google_maps_results(
                unique_results,
                business_name,
                address,
                expected_phone,
            )

            if not ranked_results:
                return GoogleMapsResult(found=False)

            # Get best match
            best_result, relevance_score = ranked_results[0]

            # Calculate address match score
            from app.utils.text_utils import validate_address_match

            _, address_score = validate_address_match(
                best_result.get("address", ""), address
            )

            return GoogleMapsResult(
                found=True,
                place_id=best_result.get("place_id"),
                rating=best_result.get("rating"),
                reviews_count=best_result.get("reviews", 0),
                address=best_result.get("address"),
                address_match_score=address_score,
                phone=best_result.get("phone"),
                website=best_result.get("website"),
                business_type=best_result.get("type"),
            )

        except Exception as e:
            # Log error and return not found
            print(f"SerpAPI Google Maps search failed: {e}")
            return GoogleMapsResult(found=False)

    def _rank_google_maps_results(
        self,
        results: list[dict],
        business_name: str,
        business_address: str,
        expected_phone: Optional[str] = None,
    ) -> list[tuple[dict, float]]:
        """
        Rank Google Maps results by relevance.

        Scoring factors:
        - Name similarity (40%)
        - Address match (40%)
        - Phone match (20%) if available

        Args:
            results: List of Google Maps results
            business_name: Expected business name
            business_address: Expected business address
            expected_phone: Optional expected phone number

        Returns:
            List of (result, score) tuples sorted by score descending
        """
        from app.utils.text_utils import (
            fuzzy_match,
            validate_address_match,
            validate_phone_match,
        )

        ranked = []

        for result in results:
            scores = {}

            # Name similarity (40%)
            result_title = result.get("title", "")
            scores["name"] = fuzzy_match(result_title, business_name)

            # Address match (40%)
            result_address = result.get("address", "")
            _, scores["address"] = validate_address_match(
                result_address, business_address
            )

            # Phone match (20%) if available
            if expected_phone:
                result_phone = result.get("phone")
                _, scores["phone"] = validate_phone_match(
                    result_phone, expected_phone
                )
            else:
                scores["phone"] = 0.0

            # Calculate weighted score
            total_score = (
                scores["name"] * 0.4
                + scores["address"] * 0.4
                + scores["phone"] * 0.2
            )

            ranked.append((result, total_score))

        # Sort by score descending
        return sorted(ranked, key=lambda x: x[1], reverse=True)

    async def search_web(
        self, query: str, num_results: int = 10
    ) -> list[WebSearchResult]:
        """
        Fallback general web search for business validation.

        Args:
            query: Search query
            num_results: Number of results to return

        Returns:
            List of web search results

        Raises:
            Exception: If API call fails
        """
        await self.rate_limiter.acquire()

        try:
            search = GoogleSearch(
                {
                    "q": query,
                    "api_key": self.api_key,
                    "num": num_results,
                }
            )

            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(None, search.get_dict)

            organic_results = results.get("organic_results", [])

            return [
                WebSearchResult(
                    title=result.get("title", ""),
                    link=result.get("link", ""),
                    snippet=result.get("snippet", ""),
                    position=result.get("position", 0),
                )
                for result in organic_results
            ]

        except Exception as e:
            print(f"SerpAPI web search failed: {e}")
            return []

    def _calculate_address_match(
        self, result_address: str, query_address: str
    ) -> float:
        """
        Calculate fuzzy match score between addresses.

        Args:
            result_address: Address from search result
            query_address: Query address

        Returns:
            Match score (0.0-1.0)
        """
        if not result_address or not query_address:
            return 0.0

        # Simple token-based matching
        result_tokens = set(result_address.split())
        query_tokens = set(query_address.split())

        if not query_tokens:
            return 0.0

        # Calculate Jaccard similarity
        intersection = result_tokens & query_tokens
        union = result_tokens | query_tokens

        return len(intersection) / len(union) if union else 0.0
