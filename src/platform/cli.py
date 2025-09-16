"""
Enterprise CLI for keyword-finder with profile support and config overrides.

Usage:
    keyword-finder                           # Run with default config
    keyword-finder --profile production     # Use production profile  
    keyword-finder --config custom.yaml    # Use custom config file
    keyword-finder --override ml.clustering.algo=kmeans,run.seeds="seo,marketing"
    keyword-finder --dry-run               # Validate config without running
    keyword-finder --list-profiles         # Show available profiles
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from typing import Any

from .config_loader import ConfigError, get_profile_names, load_config

logger = logging.getLogger(__name__)


def parse_overrides(override_str: str) -> dict[str, Any]:
    """Parse override string format: key1=value1,key2=value2 or key1.nested=value"""
    if not override_str:
        return {}

    overrides: dict[str, Any] = {}
    for pair in override_str.split(","):
        if "=" not in pair:
            continue
        key, value_str = pair.split("=", 1)
        key = key.strip()
        value_str = value_str.strip()

        # Type conversion
        value: Any
        if value_str.lower() in ("true", "false"):
            value = value_str.lower() == "true"
        elif value_str.isdigit():
            value = int(value_str)
        elif value_str.replace(".", "").isdigit():
            value = float(value_str)
        else:
            value = value_str

        overrides[key] = value

    return overrides


def create_parser() -> argparse.ArgumentParser:
    """Create the main CLI parser."""
    parser = argparse.ArgumentParser(
        prog="keyword-finder",
        description="Enterprise keyword research and clustering tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  keyword-finder                           # Run with default config
  keyword-finder --profile production     # Use production profile
  keyword-finder --config custom.yaml    # Use custom config file
  keyword-finder --override ml.clustering.algo=kmeans,run.seeds="seo,marketing"
  keyword-finder --dry-run               # Validate config without running
  keyword-finder --list-profiles         # Show available profiles
        """,
    )

    # Configuration arguments
    parser.add_argument(
        "--config", type=str, help="Path to YAML config file (default: config/config.yaml)"
    )
    parser.add_argument(
        "--profile",
        type=str,
        default="development",
        help="Configuration profile to use (default: development)",
    )
    parser.add_argument(
        "--override",
        type=str,
        help="Config overrides: key1=val1,key2=val2 (dot notation supported)",
    )

    # Execution control
    parser.add_argument(
        "--dry-run", action="store_true", help="Validate configuration without running the pipeline"
    )
    parser.add_argument(
        "--list-profiles", action="store_true", help="List available configuration profiles"
    )

    # Output control
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress non-error output")

    # Legacy compatibility (deprecated)
    parser.add_argument("--mode", type=str, help="[DEPRECATED] Use --profile instead")

    return parser


def setup_logging(config: dict[str, Any], verbose: bool = False, quiet: bool = False) -> None:
    """Setup logging based on config and CLI flags."""
    log_config = config.get("logging", {})

    # Determine log level
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    else:
        level_name = log_config.get("level", "INFO")
        level = getattr(logging, level_name.upper(), logging.INFO)

    # Configure root logger
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # TODO: Add JSON structured logging based on config.logging.format


async def run_pipeline(config: dict[str, Any]) -> int:
    """Run the keyword research pipeline."""
    try:
        logger.info("Starting keyword-finder pipeline")
        logger.info(f"Profile: {config['project']['environment']}")
        logger.info(f"Seeds: {config['run']['seeds']}")

        # TODO: Create unified pipeline entry point
        # For now, import and run existing main (compatibility)
        import os
        import sys

        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        from main import main as _async_main

        await _async_main()

        logger.info("Pipeline completed successfully")
        return 0

    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        return 1


def main() -> int:
    """Synchronous entrypoint for packaging scripts.

    Enterprise CLI with profile support, config overrides, and unified commands.
    """
    parser = create_parser()
    args = parser.parse_args()

    # Handle special commands
    if args.list_profiles:
        config_path = args.config
        profiles = get_profile_names(config_path)
        print("Available profiles:")
        for profile in profiles:
            print(f"  - {profile}")
        return 0

    # Handle legacy mode argument
    if args.mode:
        print("WARNING: --mode is deprecated, use --profile instead", file=sys.stderr)
        if not args.profile or args.profile == "development":
            args.profile = args.mode

    try:
        # Load configuration
        overrides = parse_overrides(args.override) if args.override else None
        config = load_config(config_path=args.config, profile=args.profile, overrides=overrides)

        # Setup logging
        setup_logging(config, args.verbose, args.quiet)

        # Dry run - just validate and show config
        if args.dry_run:
            print("✅ Configuration validation successful")
            print(f"Profile: {config['project']['environment']}")
            print(f"Seeds: {config['run']['seeds']}")
            print(
                f"Sources: trends={config['sources']['trends']}, ads_volume={config['sources']['ads_volume']}"
            )
            return 0

        # Run the pipeline
        return asyncio.run(run_pipeline(config))

    except ConfigError as e:
        print(f"❌ Configuration error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n⚠️ Pipeline interrupted by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        return 1


def run() -> None:
    """Legacy entrypoint for backward compatibility."""
    sys.exit(main())


if __name__ == "__main__":
    sys.exit(main())
