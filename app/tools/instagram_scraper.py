"""
Instagram public profile scraper for OSINT business verification.

Uses Playwright to scrape public Instagram profiles and detect business activity.
"""

import asyncio
from typing import Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

from app.tools.browser_manager import browser_manager


class InstagramResult(BaseModel):
    """Result from Instagram profile search."""

    found: bool = Field(description="Whether profile was found")
    username: Optional[str] = Field(
        default=None, description="Instagram username")
    follower_count: int = Field(default=0, description="Number of followers")
    post_count: int = Field(default=0, description="Total posts")
    last_post_date: Optional[datetime] = Field(
        default=None, description="Date of most recent post"
    )
    posts_last_30d: int = Field(default=0, description="Posts in last 30 days")
    posts_last_90d: int = Field(default=0, description="Posts in last 90 days")
    is_business_account: bool = Field(
        default=False, description="Whether it's a business account"
    )
    bio: Optional[str] = Field(default=None, description="Profile bio")


class InstagramScraper:
    """Playwright-based Instagram public profile scraper."""

    BASE_URL = "https://www.instagram.com"
    SEARCH_TIMEOUT = 10000  # 10 seconds
    RATE_LIMIT_DELAY = 3  # 3 seconds between requests

    async def search_profile(self, business_name: str) -> InstagramResult:
        """
        Search Instagram for business profile.

        Args:
            business_name: Name of the business to search

        Returns:
            InstagramResult with profile information

        Note:
            This scraper uses public Instagram pages (no authentication).
            It may fail if Instagram changes their HTML structure.
        """
        try:
            # Create browser context
            context = await browser_manager.create_context()
            page = await context.new_page()

            # Search for profile
            username = await self._search_username(page, business_name)

            if not username:
                await context.close()
                return InstagramResult(found=False)

            # Get profile data
            result = await self._scrape_profile(page, username)

            await context.close()

            # Rate limiting
            await asyncio.sleep(self.RATE_LIMIT_DELAY)

            return result

        except Exception as e:
            print(f"Instagram scraper failed: {e}")
            return InstagramResult(found=False)

    async def _search_username(self, page: Page, business_name: str) -> Optional[str]:
        """
        Search for Instagram username from business name.

        Args:
            page: Playwright page
            business_name: Business name to search

        Returns:
            Instagram username or None if not found
        """
        try:
            # Navigate to Instagram search (using Google as fallback)
            search_query = f"site:instagram.com {business_name}"
            await page.goto(
                f"https://www.google.com/search?q={search_query}",
                timeout=self.SEARCH_TIMEOUT,
            )

            # Wait for results
            await page.wait_for_selector("div#search", timeout=self.SEARCH_TIMEOUT)

            # Extract first Instagram link
            links = await page.query_selector_all("a[href*='instagram.com/']")

            for link in links:
                href = await link.get_attribute("href")
                if href and "/p/" not in href and "/reel/" not in href:
                    # Extract username from URL
                    parts = href.split("instagram.com/")
                    if len(parts) > 1:
                        username = parts[1].split("/")[0].split("?")[0]
                        if username and username not in ["explore", "accounts", "direct"]:
                            return username

            return None

        except Exception as e:
            print(f"Instagram username search failed: {e}")
            return None

    async def _scrape_profile(self, page: Page, username: str) -> InstagramResult:
        """
        Scrape Instagram profile data.

        Args:
            page: Playwright page
            username: Instagram username

        Returns:
            InstagramResult with profile data
        """
        try:
            # Navigate to profile
            profile_url = f"{self.BASE_URL}/{username}/"
            await page.goto(profile_url, timeout=self.SEARCH_TIMEOUT)

            # Wait for profile to load
            await page.wait_for_selector("header", timeout=self.SEARCH_TIMEOUT)

            # Extract profile data from meta tags (works without login)
            profile_data = await page.evaluate(
                """
                () => {
                    const getMetaContent = (property) => {
                        const meta = document.querySelector(`meta[property="${property}"]`);
                        return meta ? meta.content : null;
                    };
                    
                    return {
                        description: getMetaContent('og:description'),
                        title: getMetaContent('og:title')
                    };
                }
            """
            )

            # Parse follower count and post count from description
            # Format: "X Followers, Y Following, Z Posts - See Instagram photos..."
            description = profile_data.get("description", "")
            follower_count = self._extract_count(description, "Followers")
            post_count = self._extract_count(description, "Posts")

            # Get bio
            bio = None
            try:
                bio_element = await page.query_selector("header section div")
                if bio_element:
                    bio = await bio_element.inner_text()
            except:
                pass

            # Note: Without authentication, we can't get exact post dates
            # We'll estimate activity based on post count and profile age
            is_active = post_count > 0

            return InstagramResult(
                found=True,
                username=username,
                follower_count=follower_count,
                post_count=post_count,
                last_post_date=None,  # Requires authentication
                posts_last_30d=0,  # Requires authentication
                posts_last_90d=0,  # Requires authentication
                is_business_account=False,  # Requires authentication
                bio=bio,
            )

        except PlaywrightTimeout:
            print(f"Instagram profile timeout for: {username}")
            return InstagramResult(found=False)
        except Exception as e:
            print(f"Instagram profile scraping failed: {e}")
            return InstagramResult(found=False)

    def _extract_count(self, text: str, keyword: str) -> int:
        """
        Extract count from Instagram description text.

        Args:
            text: Description text
            keyword: Keyword to search for (e.g., "Followers", "Posts")

        Returns:
            Extracted count or 0 if not found
        """
        try:
            # Find keyword in text
            if keyword not in text:
                return 0

            # Extract number before keyword
            parts = text.split(keyword)[0].strip().split()
            if not parts:
                return 0

            # Get last part (should be the number)
            count_str = parts[-1]

            # Handle K, M suffixes
            if count_str.endswith("K"):
                return int(float(count_str[:-1]) * 1000)
            elif count_str.endswith("M"):
                return int(float(count_str[:-1]) * 1000000)
            else:
                # Remove commas and convert
                return int(count_str.replace(",", ""))

        except (ValueError, IndexError):
            return 0
