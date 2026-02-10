"""
Unit tests for SerpAPI client.

Tests Google Maps search, rate limiting, and error handling.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.tools.serpapi_client import (
    SerpAPIClient,
    GoogleMapsResult,
    WebSearchResult,
    RateLimiter,
)


class TestRateLimiter:
    """Test rate limiter functionality."""

    @pytest.mark.asyncio
    async def test_rate_limiter_allows_requests(self):
        """Test that rate limiter allows requests within limit."""
        limiter = RateLimiter(rate_per_minute=60)

        # Should allow immediate requests
        await limiter.acquire()
        await limiter.acquire()

        assert limiter.tokens >= 0

    @pytest.mark.asyncio
    async def test_rate_limiter_enforces_limit(self):
        """Test that rate limiter enforces rate limit."""
        limiter = RateLimiter(rate_per_minute=2)

        # Consume all tokens
        await limiter.acquire()
        await limiter.acquire()

        # Next request should wait (tokens < 1)
        assert limiter.tokens < 1


class TestSerpAPIClient:
    """Test SerpAPI client functionality."""

    def test_client_initialization_requires_api_key(self):
        """Test that client requires API key."""
        with patch("app.tools.serpapi_client.settings") as mock_settings:
            mock_settings.external.serpapi_key = ""

            with pytest.raises(ValueError, match="SERPAPI_KEY not configured"):
                SerpAPIClient()

    @pytest.mark.asyncio
    async def test_google_maps_search_found(self):
        """Test Google Maps search with business found."""
        with patch("app.tools.serpapi_client.settings") as mock_settings:
            mock_settings.external.serpapi_key = "test_key"
            mock_settings.external.serpapi_rate_limit = 10
            mock_settings.external.serpapi_timeout = 30

            client = SerpAPIClient()

            # Mock SerpAPI response
            mock_results = {
                "local_results": [
                    {
                        "place_id": "ChIJ123",
                        "rating": 4.5,
                        "reviews": 25,
                        "address": "Calle Principal, Santo Domingo",
                        "phone": "+1809-555-1234",
                        "website": "https://example.com",
                        "type": "Restaurant",
                    }
                ]
            }

            with patch("app.tools.serpapi_client.GoogleSearch") as mock_search:
                mock_instance = Mock()
                mock_instance.get_dict.return_value = mock_results
                mock_search.return_value = mock_instance

                result = await client.search_google_maps(
                    business_name="Colmado La Bendición",
                    address="Los Mina, Santo Domingo Este",
                )

                assert result.found is True
                assert result.place_id == "ChIJ123"
                assert result.rating == 4.5
                assert result.reviews_count == 25
                assert result.address_match_score > 0.0

    @pytest.mark.asyncio
    async def test_google_maps_search_not_found(self):
        """Test Google Maps search with no results."""
        with patch("app.tools.serpapi_client.settings") as mock_settings:
            mock_settings.external.serpapi_key = "test_key"
            mock_settings.external.serpapi_rate_limit = 10
            mock_settings.external.serpapi_timeout = 30

            client = SerpAPIClient()

            # Mock empty response
            mock_results = {"local_results": []}

            with patch("app.tools.serpapi_client.GoogleSearch") as mock_search:
                mock_instance = Mock()
                mock_instance.get_dict.return_value = mock_results
                mock_search.return_value = mock_instance

                result = await client.search_google_maps(
                    business_name="Fake Business XYZ 12345",
                    address="Nowhere Street",
                )

                assert result.found is False
                assert result.place_id is None

    @pytest.mark.asyncio
    async def test_google_maps_search_handles_errors(self):
        """Test that Google Maps search handles API errors gracefully."""
        with patch("app.tools.serpapi_client.settings") as mock_settings:
            mock_settings.external.serpapi_key = "test_key"
            mock_settings.external.serpapi_rate_limit = 10
            mock_settings.external.serpapi_timeout = 30

            client = SerpAPIClient()

            with patch("app.tools.serpapi_client.GoogleSearch") as mock_search:
                mock_search.side_effect = Exception("API Error")

                result = await client.search_google_maps(
                    business_name="Test Business", address="Test Address"
                )

                # Should return not found instead of raising
                assert result.found is False

    @pytest.mark.asyncio
    async def test_web_search(self):
        """Test general web search functionality."""
        with patch("app.tools.serpapi_client.settings") as mock_settings:
            mock_settings.external.serpapi_key = "test_key"
            mock_settings.external.serpapi_rate_limit = 10
            mock_settings.external.serpapi_timeout = 30

            client = SerpAPIClient()

            mock_results = {
                "organic_results": [
                    {
                        "title": "Test Result",
                        "link": "https://example.com",
                        "snippet": "Test snippet",
                        "position": 1,
                    }
                ]
            }

            with patch("app.tools.serpapi_client.GoogleSearch") as mock_search:
                mock_instance = Mock()
                mock_instance.get_dict.return_value = mock_results
                mock_search.return_value = mock_instance

                results = await client.search_web("test query")

                assert len(results) == 1
                assert results[0].title == "Test Result"
                assert results[0].link == "https://example.com"

    def test_address_match_calculation(self):
        """Test address fuzzy matching."""
        with patch("app.tools.serpapi_client.settings") as mock_settings:
            mock_settings.external.serpapi_key = "test_key"
            mock_settings.external.serpapi_rate_limit = 10
            mock_settings.external.serpapi_timeout = 30

            client = SerpAPIClient()

            # Exact match
            score = client._calculate_address_match(
                "calle principal santo domingo", "calle principal santo domingo"
            )
            assert score == 1.0

            # Partial match
            score = client._calculate_address_match(
                "calle principal santo domingo este", "calle principal santo domingo"
            )
            assert 0.0 < score < 1.0

            # No match
            score = client._calculate_address_match(
                "calle principal", "avenida independencia"
            )
            assert score < 0.5
