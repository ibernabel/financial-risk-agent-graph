"""
OSINT Researcher Agent Node - Business validation using open-source intelligence.

Validates informal businesses using Google Maps, Instagram, and Facebook.
Includes caching and metrics collection for production use.
"""

import asyncio
import logging
from time import time
from app.core.state import AgentState, OSINTFindings
from app.core.config import settings
from app.tools.serpapi_client import SerpAPIClient
from app.tools.instagram_scraper import InstagramScraper
from app.tools.facebook_scraper import FacebookScraper
from app.agents.osint.dvs_calculator import DVSCalculator
from app.tools.osint_cache import osint_cache
from app.tools.osint_metrics import osint_metrics, OSINTSource

logger = logging.getLogger(__name__)


async def osint_researcher_node(state: AgentState) -> dict:
    """
    OSINT researcher - validates business existence online.

    Searches for business on:
    - Google Maps (via SerpAPI)
    - Instagram (public profiles)
    - Facebook (business pages)

    Calculates Digital Veracity Score (DVS) based on findings.

    Args:
        state: Current agent state

    Returns:
        State update with osint_findings
    """
    # Extract business information from triage
    if not state.triage_result:
        return {
            "osint_findings": OSINTFindings(
                business_found=False,
                digital_veracity_score=0.0,
                sources_checked=[],
                evidence={},
            ),
            "current_step": "osint_completed",
            "agents_executed": state.agents_executed + ["osint_researcher"],
        }

    # Extract business information from applicant
    # For informal businesses, declared_employer is the business name
    business_name = state.applicant.get("declared_employer", "")
    business_address = state.applicant.get("declared_address", "")

    # If no business name, cannot perform OSINT
    if not business_name:
        return {
            "osint_findings": OSINTFindings(
                business_found=False,
                digital_veracity_score=0.0,
                sources_checked=[],
                evidence={
                    "error": "No business name provided in applicant data"},
            ),
            "current_step": "osint_completed",
            "agents_executed": state.agents_executed + ["osint_researcher"],
        }

    # Check cache first (if enabled)
    if settings.features.enable_osint_cache:
        cached_result = await osint_cache.get(business_name, business_address)
        if cached_result:
            logger.info(f"OSINT cache HIT for {business_name}")
            return {
                "osint_findings": OSINTFindings(**cached_result),
                "current_step": "osint_completed",
                "agents_executed": state.agents_executed + ["osint_researcher"],
            }

    # Start timing for metrics
    start_time = time()

    # Initialize tools
    serpapi_client = SerpAPIClient()
    instagram_scraper = InstagramScraper()
    facebook_scraper = FacebookScraper()

    # Run searches in parallel
    try:
        google_maps_result, instagram_result, facebook_result = await asyncio.gather(
            serpapi_client.search_google_maps(business_name, business_address),
            instagram_scraper.search_profile(business_name),
            facebook_scraper.search_business_page(
                business_name, business_address),
            return_exceptions=True,
        )

        # Handle exceptions
        if isinstance(google_maps_result, Exception):
            print(f"Google Maps search failed: {google_maps_result}")
            google_maps_result = None

        if isinstance(instagram_result, Exception):
            print(f"Instagram search failed: {instagram_result}")
            instagram_result = None

        if isinstance(facebook_result, Exception):
            print(f"Facebook search failed: {facebook_result}")
            facebook_result = None

        # Calculate DVS
        dvs_result = dvs_calculator.calculate_dvs(
            google_maps=google_maps_result,
            instagram=instagram_result,
            facebook=facebook_result,
            declared_name=business_name,
        )

        # Build evidence dictionary
        evidence = {}

        if google_maps_result:
            evidence["google_maps"] = {
                "found": google_maps_result.found,
                "reviews": google_maps_result.reviews_count,
                "rating": google_maps_result.rating,
                "address": google_maps_result.address,
            }

        if instagram_result:
            evidence["instagram"] = {
                "found": instagram_result.found,
                "username": instagram_result.username,
                "followers": instagram_result.follower_count,
                "posts": instagram_result.post_count,
            }

        if facebook_result:
            evidence["facebook"] = {
                "found": facebook_result.found,
                "page_url": facebook_result.page_url,
                "likes": facebook_result.likes_count,
            }

        # Determine if business was found
        business_found = dvs_result.evidence_count > 0

        osint_findings = OSINTFindings(
            business_found=business_found,
            digital_veracity_score=dvs_result.score,
            sources_checked=dvs_result.sources_checked,
            evidence=evidence,
        )

        # Record metrics (if enabled)
        if settings.features.enable_osint_metrics:
            total_latency = int((time() - start_time) * 1000)  # Convert to ms

            # Record per-source metrics
            if google_maps_result and not isinstance(google_maps_result, Exception):
                osint_metrics.record(
                    business_name=business_name,
                    source=OSINTSource.GOOGLE_MAPS,
                    success=google_maps_result.found,
                    latency_ms=total_latency // 3,  # Approximate
                    dvs_score=dvs_result.score,
                )

            if instagram_result and not isinstance(instagram_result, Exception):
                osint_metrics.record(
                    business_name=business_name,
                    source=OSINTSource.INSTAGRAM,
                    success=instagram_result.found,
                    latency_ms=total_latency // 3,
                    dvs_score=dvs_result.score,
                )

            if facebook_result and not isinstance(facebook_result, Exception):
                osint_metrics.record(
                    business_name=business_name,
                    source=OSINTSource.FACEBOOK,
                    success=facebook_result.found,
                    latency_ms=total_latency // 3,
                    dvs_score=dvs_result.score,
                )

        # Cache result (if enabled)
        if settings.features.enable_osint_cache:
            await osint_cache.set(
                business_name, business_address, osint_findings.model_dump()
            )

        return {
            "osint_findings": osint_findings,
            "current_step": "osint_completed",
            "agents_executed": state.agents_executed + ["osint_researcher"],
        }

    except Exception as e:
        print(f"OSINT researcher failed: {e}")
        # Return graceful degradation
        return {
            "osint_findings": OSINTFindings(
                business_found=False,
                digital_veracity_score=0.0,
                sources_checked=[],
                evidence={"error": str(e)},
            ),
            "current_step": "osint_completed",
            "agents_executed": state.agents_executed + ["osint_researcher"],
        }
