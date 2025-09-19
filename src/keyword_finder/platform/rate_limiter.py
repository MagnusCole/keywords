"""
Rate limiting utilities for API calls and web scraping.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Optional

import httpx


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    requests_per_minute: int = 60
    burst_limit: int = 10
    cooldown_seconds: float = 1.0

    @property
    def requests_per_second(self) -> float:
        return self.requests_per_minute / 60.0


class RateLimiter:
    """Simple rate limiter for API calls."""

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.requests = []
        self.logger = logging.getLogger(__name__)

    async def wait_if_needed(self) -> None:
        """Wait if we're exceeding the rate limit."""
        now = time.time()

        # Remove old requests outside the time window
        window_start = now - 60.0  # 1 minute window
        self.requests = [req_time for req_time in self.requests if req_time > window_start]

        if len(self.requests) >= self.config.requests_per_minute:
            # Calculate wait time
            oldest_request = min(self.requests)
            wait_time = 60.0 - (now - oldest_request)
            if wait_time > 0:
                self.logger.debug(f"Rate limit reached, waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)

        self.requests.append(now)

    def is_allowed(self) -> bool:
        """Check if a request is allowed without waiting."""
        now = time.time()
        window_start = now - 60.0
        self.requests = [req_time for req_time in self.requests if req_time > window_start]
        return len(self.requests) < self.config.requests_per_minute


class ThrottledSession:
    """HTTP session with built-in rate limiting."""

    def __init__(self, rate_limiter: RateLimiter, timeout: float = 30.0):
        self.rate_limiter = rate_limiter
        self.timeout = timeout
        self.session: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self.session = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.aclose()

    async def get(self, url: str, **kwargs) -> httpx.Response:
        """Make a GET request with rate limiting."""
        if not self.session:
            raise RuntimeError("Session not initialized")

        await self.rate_limiter.wait_if_needed()
        response = await self.session.get(url, **kwargs)
        return response

    async def post(self, url: str, **kwargs) -> httpx.Response:
        """Make a POST request with rate limiting."""
        if not self.session:
            raise RuntimeError("Session not initialized")

        await self.rate_limiter.wait_if_needed()
        response = await self.session.post(url, **kwargs)
        return response