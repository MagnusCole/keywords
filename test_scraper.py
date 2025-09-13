#!/usr/bin/env python3
"""
Test script para debug del scraper
"""

import asyncio
import logging
import sys
from pathlib import Path

# Agregar src al path
sys.path.append(str(Path(__file__).parent / "src"))

from scrapers import GoogleScraper

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


async def test_scraper():
    scraper = GoogleScraper()

    print("🔍 Testing Google Autocomplete...")
    suggestions = await scraper.get_autocomplete_suggestions("marketing")
    print(f"Autocomplete suggestions: {suggestions}")

    print("\n🔍 Testing Google Related Searches...")
    related = await scraper.get_related_searches("marketing")
    print(f"Related searches: {related}")

    await scraper.close()


if __name__ == "__main__":
    asyncio.run(test_scraper())
