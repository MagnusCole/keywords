"""
Production runner for keyword-finder with Google Ads API integration.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from main import main as _async_main
from src.ads_quota import get_quota_manager


async def production_run():
    """Run keyword finder with production configuration and quota monitoring."""

    print("🚀 Starting Keyword Finder - Production Mode")
    print("=" * 60)

    # Show quota status before starting
    quota_manager = get_quota_manager()
    quota_manager.print_quota_status()

    # Check if we have enough quota for a production run
    status = quota_manager.get_quota_status()

    if status["operations"]["remaining"] < 100:
        print("\n⚠️  WARNING: Low remaining quota for operations")
        print("Consider waiting for quota reset or reducing scope")

        response = input("\nContinue anyway? (y/N): ")
        if response.lower() != "y":
            print("Aborted.")
            return

    print("\n🔄 Starting keyword extraction...")
    print("Using production.yaml configuration")
    print("- Real Google Ads volume data")
    print("- Google Trends integration")
    print("- Conservative rate limiting")
    print("- 3 seeds with 50 keywords each")

    # Set config file to production
    sys.argv.extend(["--config", "config/production.yaml"])

    try:
        # Run the main extraction
        await _async_main()

        print("\n✅ Extraction completed successfully!")

        # Show final quota status
        print("\n📊 Final Quota Status:")
        quota_manager.print_quota_status()

    except Exception as e:
        print(f"\n❌ Error during extraction: {e}")

        # Still show quota status to track usage
        print("\n📊 Quota Status After Error:")
        quota_manager.print_quota_status()

        raise


def main():
    """Main entry point for production runner."""
    asyncio.run(production_run())


if __name__ == "__main__":
    main()
