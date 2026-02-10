"""
Unit tests for social media scrapers.

Tests Instagram and Facebook scrapers with mocked browser interactions.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.tools.instagram_scraper import InstagramScraper, InstagramResult
from app.tools.facebook_scraper import FacebookScraper, FacebookResult


class TestInstagramScraper:
    """Test Instagram scraper functionality."""

    @pytest.mark.asyncio
    async def test_extract_count_with_k_suffix(self):
        """Test count extraction with K suffix."""
        scraper = InstagramScraper()

        count = scraper._extract_count(
            "10.5K Followers, 100 Posts", "Followers")
        assert count == 10500

        count = scraper._extract_count("1.2K Posts", "Posts")
        assert count == 1200

    @pytest.mark.asyncio
    async def test_extract_count_with_m_suffix(self):
        """Test count extraction with M suffix."""
        scraper = InstagramScraper()

        count = scraper._extract_count("1.5M Followers", "Followers")
        assert count == 1500000

    @pytest.mark.asyncio
    async def test_extract_count_plain_number(self):
        """Test count extraction with plain numbers."""
        scraper = InstagramScraper()

        count = scraper._extract_count("500 Followers, 25 Posts", "Followers")
        assert count == 500

        count = scraper._extract_count("1,234 Posts", "Posts")
        assert count == 1234

    @pytest.mark.asyncio
    async def test_extract_count_not_found(self):
        """Test count extraction when keyword not found."""
        scraper = InstagramScraper()

        count = scraper._extract_count("No followers here", "Followers")
        assert count == 0


class TestFacebookScraper:
    """Test Facebook scraper functionality."""

    @pytest.mark.asyncio
    async def test_extract_likes_count(self):
        """Test likes count extraction."""
        scraper = FacebookScraper()

        count = scraper._extract_likes_count("1.2K people like this")
        assert count == 1200

        count = scraper._extract_likes_count("500 likes")
        assert count == 500

    @pytest.mark.asyncio
    async def test_extract_likes_count_not_found(self):
        """Test likes count extraction when not found."""
        scraper = FacebookScraper()

        count = scraper._extract_likes_count("No likes information")
        assert count == 0


# Note: Full integration tests with real browser automation would require
# actual network access and are better suited for manual testing or E2E tests.
# These unit tests focus on the parsing logic.
