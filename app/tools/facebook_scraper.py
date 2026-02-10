"""
Facebook business page scraper for OSINT business verification.

Uses Playwright to scrape public Facebook business pages.
"""

import asyncio
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

from app.tools.browser_manager import browser_manager


class FacebookResult(BaseModel):
    """Result from Facebook business page search."""

    found: bool = Field(description="Whether page was found")
    page_url: Optional[str] = Field(
        default=None, description="Facebook page URL")
    likes_count: int = Field(default=0, description="Number of page likes")
    checkins_count: int = Field(default=0, description="Number of check-ins")
    last_post_date: Optional[datetime] = Field(
        default=None, description="Date of most recent post"
    )
    is_active: bool = Field(
        default=False, description="Whether page has recent activity (30 days)"
    )
    category: Optional[str] = Field(
        default=None, description="Business category")
    about: Optional[str] = Field(default=None, description="About section")


class FacebookScraper:
    """Playwright-based Facebook business page scraper."""

    BASE_URL = "https://www.facebook.com"
    SEARCH_TIMEOUT = 10000  # 10 seconds
    RATE_LIMIT_DELAY = 3  # 3 seconds between requests

    async def search_business_page(
        self, business_name: str, address: str
    ) -> FacebookResult:
        """
        Search Facebook for business page.

        Args:
            business_name: Name of the business
            address: Business address for context

        Returns:
            FacebookResult with page information

        Note:
            This scraper uses public Facebook pages (no authentication).
            It may fail if Facebook changes their HTML structure.
        """
        try:
            # Create browser context
            context = await browser_manager.create_context()
            page = await context.new_page()

            # Search for business page
            page_url = await self._search_page_url(page, business_name, address)

            if not page_url:
                await context.close()
                return FacebookResult(found=False)

            # Get page data
            result = await self._scrape_page(page, page_url)

            await context.close()

            # Rate limiting
            await asyncio.sleep(self.RATE_LIMIT_DELAY)

            return result

        except Exception as e:
            print(f"Facebook scraper failed: {e}")
            return FacebookResult(found=False)

    async def _search_page_url(
        self, page: Page, business_name: str, address: str
    ) -> Optional[str]:
        """
        Search for Facebook page URL from business name.

        Args:
            page: Playwright page
            business_name: Business name to search
            address: Business address for context

        Returns:
            Facebook page URL or None if not found
        """
        try:
            # Navigate to Facebook search (using Google as fallback)
            search_query = f"site:facebook.com {business_name} {address}"
            await page.goto(
                f"https://www.google.com/search?q={search_query}",
                timeout=self.SEARCH_TIMEOUT,
            )

            # Wait for results
            await page.wait_for_selector("div#search", timeout=self.SEARCH_TIMEOUT)

            # Extract first Facebook link
            links = await page.query_selector_all("a[href*='facebook.com/']")

            for link in links:
                href = await link.get_attribute("href")
                if href and "/posts/" not in href and "/photos/" not in href:
                    # Clean URL
                    if "facebook.com" in href:
                        # Extract clean page URL
                        parts = href.split("facebook.com/")
                        if len(parts) > 1:
                            page_id = parts[1].split("/")[0].split("?")[0]
                            if page_id and page_id not in [
                                "login",
                                "privacy",
                                "help",
                            ]:
                                return f"{self.BASE_URL}/{page_id}"

            return None

        except Exception as e:
            print(f"Facebook page URL search failed: {e}")
            return None

    async def _scrape_page(self, page: Page, page_url: str) -> FacebookResult:
        """
        Scrape Facebook page data.

        Args:
            page: Playwright page
            page_url: Facebook page URL

        Returns:
            FacebookResult with page data
        """
        try:
            # Navigate to page
            await page.goto(page_url, timeout=self.SEARCH_TIMEOUT)

            # Wait for page to load
            await page.wait_for_selector("body", timeout=self.SEARCH_TIMEOUT)

            # Extract page data from meta tags (works without login)
            page_data = await page.evaluate(
                """
                () => {
                    const getMetaContent = (property) => {
                        const meta = document.querySelector(`meta[property="${property}"]`);
                        return meta ? meta.content : null;
                    };
                    
                    return {
                        title: getMetaContent('og:title'),
                        description: getMetaContent('og:description'),
                        url: getMetaContent('og:url')
                    };
                }
            """
            )

            # Try to extract likes count from page text
            likes_count = 0
            try:
                page_text = await page.inner_text("body")
                likes_count = self._extract_likes_count(page_text)
            except:
                pass

            # Check if page exists (has valid title)
            title = page_data.get("title", "")
            if not title or "Facebook" == title:
                return FacebookResult(found=False)

            return FacebookResult(
                found=True,
                page_url=page_url,
                likes_count=likes_count,
                checkins_count=0,  # Requires authentication
                last_post_date=None,  # Requires authentication
                is_active=False,  # Requires authentication
                category=None,  # Requires authentication
                about=page_data.get("description"),
            )

        except PlaywrightTimeout:
            print(f"Facebook page timeout for: {page_url}")
            return FacebookResult(found=False)
        except Exception as e:
            print(f"Facebook page scraping failed: {e}")
            return FacebookResult(found=False)

    def _extract_likes_count(self, text: str) -> int:
        """
        Extract likes count from Facebook page text.

        Args:
            text: Page text content

        Returns:
            Extracted likes count or 0 if not found
        """
        try:
            # Look for patterns like "1.2K likes" or "500 people like this"
            import re

            patterns = [
                r"([\d,.]+)\s*([KM])?\s*(?:likes|people like this)",
                r"([\d,.]+)\s*([KM])?\s*followers",
            ]

            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    count_str = match.group(1).replace(",", "")
                    suffix = match.group(2)

                    # Handle K, M suffixes
                    if suffix and suffix.upper() == "K":
                        return int(float(count_str) * 1000)
                    elif suffix and suffix.upper() == "M":
                        return int(float(count_str) * 1000000)
                    else:
                        return int(float(count_str))

            return 0

        except (ValueError, AttributeError):
            return 0
