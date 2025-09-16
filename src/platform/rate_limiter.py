"""
Rate limiting and throttling controls for web scraping.
Implements configurable delays and concurrent request limits.
"""

import asyncio
import logging
import random
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting parameters."""

    min_delay: float = 1.0
    max_delay: float = 3.0
    max_concurrent: int = 3
    backoff_factor: float = 2.0
    max_backoff: float = 60.0
    retry_limit: int = 3
    request_timeout: float = 30.0

    def get_delay_range(self) -> tuple[float, float]:
        """Get the delay range as a tuple."""
        return (self.min_delay, self.max_delay)


class AdaptiveRateLimiter:
    """
    Adaptive rate limiter that adjusts delays based on response patterns.
    Implements exponential backoff for errors and throttling detection.
    """

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self._semaphore = asyncio.Semaphore(config.max_concurrent)
        self._last_request_times: list[float] = []
        self._consecutive_errors = 0
        self._current_backoff = 0.0
        self._total_requests = 0
        self._successful_requests = 0

    async def acquire(self) -> None:
        """Acquire permission to make a request with rate limiting."""
        await self._semaphore.acquire()

        # Apply base delay
        delay = self._calculate_delay()
        if delay > 0:
            logger.debug(f"Rate limiting: waiting {delay:.2f}s")
            await asyncio.sleep(delay)

        # Track request timing
        self._last_request_times.append(time.time())
        # Keep only recent requests (last 60 seconds)
        cutoff = time.time() - 60
        self._last_request_times = [t for t in self._last_request_times if t > cutoff]

        self._total_requests += 1

    def release(self, success: bool = True, status_code: int | None = None) -> None:
        """Release the semaphore and update rate limiting state."""
        self._semaphore.release()

        if success:
            self._successful_requests += 1
            self._consecutive_errors = 0
            # Gradually reduce backoff on success
            self._current_backoff = max(0, self._current_backoff * 0.8)
        else:
            self._consecutive_errors += 1

            # Apply exponential backoff for errors
            if status_code == 429:  # Rate limited
                self._current_backoff = min(
                    self.config.max_backoff,
                    max(5.0, self._current_backoff * self.config.backoff_factor),
                )
                logger.warning(f"Rate limited (429), backing off to {self._current_backoff:.2f}s")
            elif status_code and 500 <= status_code < 600:  # Server errors
                self._current_backoff = min(
                    self.config.max_backoff, max(2.0, self._current_backoff * 1.5)
                )
                logger.warning(
                    f"Server error ({status_code}), backing off to {self._current_backoff:.2f}s"
                )

    def _calculate_delay(self) -> float:
        """Calculate the delay before the next request."""
        base_delay = random.uniform(*self.config.get_delay_range())  # noqa: S311

        # Add backoff if we've had errors
        total_delay = base_delay + self._current_backoff

        # Add extra delay if we're making requests too frequently
        if len(self._last_request_times) >= self.config.max_concurrent:
            recent_avg = self._get_recent_request_rate()
            if recent_avg > 0 and recent_avg < 1.0:  # More than 1 req/sec
                total_delay += 1.0

        return total_delay

    def _get_recent_request_rate(self) -> float:
        """Get the average time between recent requests."""
        if len(self._last_request_times) < 2:
            return float("inf")

        time_span = self._last_request_times[-1] - self._last_request_times[0]
        if time_span <= 0:
            return 0

        return time_span / (len(self._last_request_times) - 1)

    def get_stats(self) -> dict[str, Any]:
        """Get rate limiting statistics."""
        success_rate = (
            self._successful_requests / self._total_requests if self._total_requests > 0 else 0
        )

        return {
            "total_requests": self._total_requests,
            "successful_requests": self._successful_requests,
            "success_rate": success_rate,
            "consecutive_errors": self._consecutive_errors,
            "current_backoff": self._current_backoff,
            "recent_requests": len(self._last_request_times),
            "avg_request_interval": self._get_recent_request_rate(),
        }


class ThrottledSession:
    """
    Wrapper around HTTP session with integrated rate limiting.
    Provides context manager interface for automatic rate limiting.
    """

    def __init__(self, session, rate_limiter: AdaptiveRateLimiter):
        self.session = session
        self.rate_limiter = rate_limiter

    async def __aenter__(self):
        await self.rate_limiter.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Determine success based on exception type
        success = exc_type is None
        status_code = None

        if hasattr(exc_val, "response") and hasattr(exc_val.response, "status_code"):
            status_code = exc_val.response.status_code

        self.rate_limiter.release(success=success, status_code=status_code)

    def get(self, *args, **kwargs):
        """Proxy GET method to the underlying session."""
        return self.session.get(*args, **kwargs)

    def post(self, *args, **kwargs):
        """Proxy POST method to the underlying session."""
        return self.session.post(*args, **kwargs)


def create_rate_limited_scraper_config(validation_config: dict[str, Any]) -> RateLimitConfig:
    """Create rate limiter configuration from validation config."""
    scraping_config = validation_config.get("scraping", {})

    return RateLimitConfig(
        min_delay=scraping_config.get("min_delay", 2.0),
        max_delay=scraping_config.get("max_delay", 4.0),
        max_concurrent=scraping_config.get("max_concurrent", 1),
        backoff_factor=scraping_config.get("backoff_factor", 2.0),
        max_backoff=scraping_config.get("max_backoff", 30.0),
        retry_limit=scraping_config.get("retry_limit", 2),
        request_timeout=scraping_config.get("timeout", 20.0),
    )
