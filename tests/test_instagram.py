"""
Test Instagram search for @deiquelparty.
"""

import asyncio
from app.tools.instagram_scraper import InstagramScraper


async def test_instagram():
    """Test Instagram search."""

    scraper = InstagramScraper()

    # Test 1: Search by business name
    print("=" * 60)
    print("Test 1: Search 'Deiquel Cake Toppers'")
    print("=" * 60)
    result1 = await scraper.search_profile("Deiquel Cake Toppers")
    if result1.found:
        print(f"✅ Found: @{result1.username}")
        print(f"   Followers: {result1.follower_count:,}")
        print(f"   Posts: {result1.post_count}")
        if result1.bio:
            print(f"   Bio: {result1.bio[:100]}")
    else:
        print("❌ Not found")

    print("\n" + "=" * 60)
    print("Test 2: Direct username '@deiquelparty'")
    print("=" * 60)
    result2 = await scraper.search_profile("@deiquelparty")
    if result2.found:
        print(f"✅ Found: @{result2.username}")
        print(f"   Followers: {result2.follower_count:,}")
        print(f"   Posts: {result2.post_count}")
        if result2.bio:
            print(f"   Bio: {result2.bio[:100]}")
    else:
        print("❌ Not found")

    print("\n" + "=" * 60)
    print("Test 3: Username without @ 'deiquelparty'")
    print("=" * 60)
    result3 = await scraper.search_profile("deiquelparty")
    if result3.found:
        print(f"✅ Found: @{result3.username}")
        print(f"   Followers: {result3.follower_count:,}")
        print(f"   Posts: {result3.post_count}")
        if result3.bio:
            print(f"   Bio: {result3.bio[:100]}")
    else:
        print("❌ Not found")


if __name__ == "__main__":
    asyncio.run(test_instagram())
