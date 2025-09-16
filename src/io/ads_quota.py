"""
API Quota Management for Google Ads API.
Tracks daily usage to respect 15,000 operations and 1,000 GET requests limits.
"""

import json
import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


@dataclass
class QuotaLimits:
    """Google Ads API quota limits."""

    daily_operations: int = 15000
    daily_get_requests: int = 1000

    # Safety margins (use 80% of limits)
    operations_margin: float = 0.8
    get_requests_margin: float = 0.8

    @property
    def safe_operations_limit(self) -> int:
        return int(self.daily_operations * self.operations_margin)

    @property
    def safe_get_requests_limit(self) -> int:
        return int(self.daily_get_requests * self.get_requests_margin)


@dataclass
class DailyUsage:
    """Daily API usage tracking."""

    date: str
    operations_used: int = 0
    get_requests_used: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "operations_used": self.operations_used,
            "get_requests_used": self.get_requests_used,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DailyUsage":
        return cls(
            date=data["date"],
            operations_used=data.get("operations_used", 0),
            get_requests_used=data.get("get_requests_used", 0),
        )


class GoogleAdsQuotaManager:
    """
    Manages Google Ads API quota usage tracking and enforcement.

    Features:
    - Tracks daily operations and GET requests
    - Enforces safety margins to prevent quota exhaustion
    - Persists usage data across sessions
    - Provides quota availability checks
    """

    def __init__(self, cache_dir: str = "cache", limits: QuotaLimits | None = None):
        self.logger = logging.getLogger(__name__)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.quota_file = self.cache_dir / "google_ads_quota.json"

        self.limits = limits or QuotaLimits()
        self.usage_data: dict[str, DailyUsage] = self._load_usage_data()

    def _load_usage_data(self) -> dict[str, DailyUsage]:
        """Load usage data from cache file."""
        try:
            if self.quota_file.exists():
                data = json.loads(self.quota_file.read_text(encoding="utf-8"))
                return {
                    date_str: DailyUsage.from_dict(usage_dict)
                    for date_str, usage_dict in data.items()
                }
        except Exception as e:
            self.logger.warning(f"Failed to load quota usage data: {e}")
        return {}

    def _save_usage_data(self) -> None:
        """Save usage data to cache file."""
        try:
            data = {date_str: usage.to_dict() for date_str, usage in self.usage_data.items()}
            self.quota_file.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception as e:
            self.logger.warning(f"Failed to save quota usage data: {e}")

    def _get_today_usage(self) -> DailyUsage:
        """Get or create today's usage record."""
        today_str = date.today().isoformat()
        if today_str not in self.usage_data:
            self.usage_data[today_str] = DailyUsage(date=today_str)
        return self.usage_data[today_str]

    def _cleanup_old_data(self, days_to_keep: int = 30) -> None:
        """Remove usage data older than specified days."""
        cutoff_date = date.today().replace(day=1)  # Keep at least current month
        cutoff_str = cutoff_date.isoformat()

        old_dates = [date_str for date_str in self.usage_data.keys() if date_str < cutoff_str]

        for old_date in old_dates:
            self.usage_data.pop(old_date, None)

        if old_dates:
            self.logger.info(f"Cleaned up quota data for {len(old_dates)} old dates")

    def can_make_operation(self, operation_count: int = 1) -> bool:
        """Check if we can make the specified number of operations today."""
        today_usage = self._get_today_usage()
        projected_usage = today_usage.operations_used + operation_count
        return projected_usage <= self.limits.safe_operations_limit

    def can_make_get_request(self, request_count: int = 1) -> bool:
        """Check if we can make the specified number of GET requests today."""
        today_usage = self._get_today_usage()
        projected_usage = today_usage.get_requests_used + request_count
        return projected_usage <= self.limits.safe_get_requests_limit

    def record_operations(self, operation_count: int) -> None:
        """Record operations usage for today."""
        today_usage = self._get_today_usage()
        today_usage.operations_used += operation_count
        self._save_usage_data()

        self.logger.debug(
            f"Recorded {operation_count} operations. "
            f"Daily total: {today_usage.operations_used}/{self.limits.safe_operations_limit}"
        )

    def record_get_requests(self, request_count: int) -> None:
        """Record GET requests usage for today."""
        today_usage = self._get_today_usage()
        today_usage.get_requests_used += request_count
        self._save_usage_data()

        self.logger.debug(
            f"Recorded {request_count} GET requests. "
            f"Daily total: {today_usage.get_requests_used}/{self.limits.safe_get_requests_limit}"
        )

    def get_quota_status(self) -> dict[str, Any]:
        """Get current quota usage status."""
        today_usage = self._get_today_usage()

        return {
            "date": today_usage.date,
            "operations": {
                "used": today_usage.operations_used,
                "limit": self.limits.daily_operations,
                "safe_limit": self.limits.safe_operations_limit,
                "remaining": self.limits.safe_operations_limit - today_usage.operations_used,
                "percentage_used": (today_usage.operations_used / self.limits.safe_operations_limit)
                * 100,
            },
            "get_requests": {
                "used": today_usage.get_requests_used,
                "limit": self.limits.daily_get_requests,
                "safe_limit": self.limits.safe_get_requests_limit,
                "remaining": self.limits.safe_get_requests_limit - today_usage.get_requests_used,
                "percentage_used": (
                    today_usage.get_requests_used / self.limits.safe_get_requests_limit
                )
                * 100,
            },
        }

    def print_quota_status(self) -> None:
        """Print a formatted quota status report."""
        status = self.get_quota_status()

        print(f"\n📊 Google Ads API Quota Status - {status['date']}")
        print("=" * 50)

        ops = status["operations"]
        print(
            f"🔧 Operations: {ops['used']:,}/{ops['safe_limit']:,} ({ops['percentage_used']:.1f}%)"
        )
        print(f"   Remaining: {ops['remaining']:,}")

        gets = status["get_requests"]
        print(
            f"📥 GET Requests: {gets['used']:,}/{gets['safe_limit']:,} ({gets['percentage_used']:.1f}%)"
        )
        print(f"   Remaining: {gets['remaining']:,}")

        # Warning if approaching limits
        if ops["percentage_used"] > 90 or gets["percentage_used"] > 90:
            print("⚠️  WARNING: Approaching daily quota limits!")
        elif ops["percentage_used"] > 75 or gets["percentage_used"] > 75:
            print("🟡 CAUTION: High quota usage today")
        else:
            print("✅ Quota usage within safe limits")

        print("=" * 50)

    def reset_daily_usage(self) -> None:
        """Reset today's usage (for testing purposes)."""
        today_str = date.today().isoformat()
        if today_str in self.usage_data:
            del self.usage_data[today_str]
            self._save_usage_data()
            self.logger.info("Reset today's quota usage")


# Singleton instance for global quota management
_quota_manager: GoogleAdsQuotaManager | None = None


def get_quota_manager() -> GoogleAdsQuotaManager:
    """Get the global quota manager instance."""
    global _quota_manager
    if _quota_manager is None:
        _quota_manager = GoogleAdsQuotaManager()
    return _quota_manager


def check_quota_before_request(operation_count: int = 1, get_request_count: int = 0) -> bool:
    """
    Check if we can make a request without exceeding quotas.

    Args:
        operation_count: Number of operations this request will consume
        get_request_count: Number of GET requests this will consume

    Returns:
        True if request can be made, False otherwise
    """
    manager = get_quota_manager()

    if operation_count > 0 and not manager.can_make_operation(operation_count):
        return False

    if get_request_count > 0 and not manager.can_make_get_request(get_request_count):
        return False

    return True


def record_quota_usage(operation_count: int = 0, get_request_count: int = 0) -> None:
    """
    Record quota usage after making a request.

    Args:
        operation_count: Number of operations consumed
        get_request_count: Number of GET requests consumed
    """
    manager = get_quota_manager()

    if operation_count > 0:
        manager.record_operations(operation_count)

    if get_request_count > 0:
        manager.record_get_requests(get_request_count)
