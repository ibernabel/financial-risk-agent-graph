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
        self, business_name: str, address: str
    ) -> GoogleMapsResult:
        """
        Search Google Maps for business location.

        Args:
            business_name: Name of the business to search
            address: Business address for context

        Returns:
            GoogleMapsResult with business information

        Raises:
            Exception: If API call fails
        """
        await self.rate_limiter.acquire()

        try:
            # Build search query
            query = f"{business_name} {address}"

            # Execute search using SerpAPI
            search = GoogleSearch(
                {
                    "q": query,
                    "engine": "google_maps",
                    "api_key": self.api_key,
                    "type": "search",
                }
            )

            # Get results (synchronous call, run in executor)
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(None, search.get_dict)

            # Parse local results
            local_results = results.get("local_results", [])

            if not local_results:
                return GoogleMapsResult(found=False)

            # Get first result (most relevant)
            first_result = local_results[0]

            # Calculate address match score (simple fuzzy match)
            result_address = first_result.get("address", "").lower()
            query_address = address.lower()
            address_match = self._calculate_address_match(
                result_address, query_address
            )

            return GoogleMapsResult(
                found=True,
                place_id=first_result.get("place_id"),
                rating=first_result.get("rating"),
                reviews_count=first_result.get("reviews", 0),
                address=first_result.get("address"),
                address_match_score=address_match,
                phone=first_result.get("phone"),
                website=first_result.get("website"),
                business_type=first_result.get("type"),
            )

        except Exception as e:
            # Log error and return not found
            print(f"SerpAPI Google Maps search failed: {e}")
            return GoogleMapsResult(found=False)

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
