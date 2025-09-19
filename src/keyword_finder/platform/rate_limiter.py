"""
Rate limiting utilities for API calls and web scraping.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    requests_per_minute: int = 60
    burst_limit: int = 10
    cooldown_seconds: float = 1.0
    min_delay: float = 1.0
    max_delay: float = 3.0
    max_concurrent: int = 5
    retry_limit: int = 3
    request_timeout: float = 30.0

    @property
    def requests_per_second(self) -> float:
        return self.requests_per_minute / 60.0

    def get_delay_range(self) -> tuple[float, float]:
        """Get the delay range as a tuple."""
        return (self.min_delay, self.max_delay)


class RateLimiter:
    """Simple rate limiter for API calls."""

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.requests: list[float] = []
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

    def get_stats(self) -> dict[str, Any]:
        """Get rate limiter statistics."""
        now = time.time()
        window_start = now - 60.0
        recent_requests = [req_time for req_time in self.requests if req_time > window_start]

        return {
            "total_requests": len(self.requests),
            "recent_requests": len(recent_requests),
            "requests_per_minute": self.config.requests_per_minute,
            "burst_limit": self.config.burst_limit,
            "cooldown_seconds": self.config.cooldown_seconds,
            "is_rate_limited": len(recent_requests) >= self.config.requests_per_minute,
        }


class ThrottledSession:
    """HTTP session with built-in rate limiting."""

    def __init__(self, session: httpx.AsyncClient, rate_limiter: RateLimiter):
        self.session = session
        self.rate_limiter = rate_limiter

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass  # Session is managed externally

    async def get(self, url: str, **kwargs) -> httpx.Response:
        """Make a GET request with rate limiting."""
        await self.rate_limiter.wait_if_needed()
        response = await self.session.get(url, **kwargs)
        return response

    async def post(self, url: str, **kwargs) -> httpx.Response:
        """Make a POST request with rate limiting."""
        await self.rate_limiter.wait_if_needed()
        response = await self.session.post(url, **kwargs)
        return response


# Factory functions
def create_rate_limited_scraper_config(
    requests_per_minute: int = 30,
    min_delay: float = 1.0,
    max_delay: float = 3.0,
    max_concurrent: int = 3,
    retry_limit: int = 3,
    request_timeout: float = 30.0,
) -> RateLimitConfig:
    """
    Create a rate limit configuration for web scraping.

    Args:
        requests_per_minute: Maximum requests per minute
        min_delay: Minimum delay between requests
        max_delay: Maximum delay between requests
        max_concurrent: Maximum concurrent connections
        retry_limit: Maximum number of retries
        request_timeout: Request timeout in seconds

    Returns:
        RateLimitConfig configured for scraping
    """
    return RateLimitConfig(
        requests_per_minute=requests_per_minute,
        min_delay=min_delay,
        max_delay=max_delay,
        max_concurrent=max_concurrent,
        retry_limit=retry_limit,
        request_timeout=request_timeout,
    )
