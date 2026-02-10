"""
Browser manager for Playwright-based web scrapers.

Provides singleton browser context management for OSINT tools.
"""

import asyncio
from typing import Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page


class BrowserManager:
    """Singleton browser context manager for scrapers."""

    _instance: Optional["BrowserManager"] = None
    _browser: Optional[Browser] = None
    _playwright = None
    _lock = asyncio.Lock()

    def __new__(cls):
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def get_browser(self) -> Browser:
        """
        Get or create shared browser instance.

        Returns:
            Browser instance (Chromium headless)
        """
        async with self._lock:
            if self._browser is None:
                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",
                        "--no-sandbox",
                    ],
                )
            return self._browser

    async def create_context(self, **kwargs) -> BrowserContext:
        """
        Create new browser context with stealth settings.

        Args:
            **kwargs: Additional context options

        Returns:
            BrowserContext with anti-detection settings
        """
        browser = await self.get_browser()

        # Default stealth settings
        default_options = {
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "locale": "es-DO",
            "timezone_id": "America/Santo_Domingo",
        }

        # Merge with custom options
        options = {**default_options, **kwargs}

        context = await browser.new_context(**options)

        # Add stealth JavaScript
        await context.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """
        )

        return context

    async def close(self) -> None:
        """Close browser and cleanup resources."""
        async with self._lock:
            if self._browser:
                await self._browser.close()
                self._browser = None

            if self._playwright:
                await self._playwright.stop()
                self._playwright = None


# Global browser manager instance
browser_manager = BrowserManager()
