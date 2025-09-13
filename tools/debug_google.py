#!/usr/bin/env python3
"""Debug utility to inspect Google Search HTML locally (non-shipping)."""

import asyncio
import httpx
from selectolax.parser import HTMLParser


async def debug_google_html() -> None:
    async with httpx.AsyncClient() as client:
        url = "https://www.google.com/search?q=marketing&hl=es&gl=es"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
        }
        r = await client.get(url, headers=headers)
        html = r.text
        with open("tools/google_search.html", "w", encoding="utf-8") as f:
            f.write(html)
        parser = HTMLParser(html)
        # Print a few sample text nodes for manual inspection
        print(f"Status: {r.status_code}; HTML length: {len(html)}; sample nodes: {len(parser.css('h3'))}")


if __name__ == "__main__":
    asyncio.run(debug_google_html())
