"""
Unified configuration system with profile support and CLI overrides.

Usage:
    config = load_config()                              # Default profile (development)
    config = load_config(profile="production")         # Specific profile  
    config = load_config(overrides={"ml.clustering.algo": "kmeans"})  # With overrides
"""

from __future__ import annotations

import logging
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """Configuration loading or validation error."""

    pass


def load_config(
    config_path: str | Path | None = None,
    profile: str = "development",
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Load unified configuration with profile and override support.

    Args:
            config_path: Path to config file. Defaults to config/config.yaml
        profile: Configuration profile (development, validation, production, test)
        overrides: Dict of override values using dot notation (e.g. {"ml.clustering.algo": "kmeans"})

    Returns:
        Complete configuration dictionary

    Raises:
        ConfigError: If config file not found or invalid profile
    """
    # Default config path
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        raise ConfigError(f"Config file not found: {config_path}")

    # Load base configuration
    try:
        with open(config_path, encoding="utf-8") as f:
            config_data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML in config file: {e}") from e

    # Extract base config (everything except 'profiles')
    base_config = {k: v for k, v in config_data.items() if k != "profiles"}

    # Apply profile overrides if not development
    if profile != "development":
        if "profiles" not in config_data:
            raise ConfigError("No profiles section found in config")

        if profile not in config_data["profiles"]:
            available = list(config_data["profiles"].keys())
            raise ConfigError(f"Profile '{profile}' not found. Available: {available}")

        profile_config = config_data["profiles"][profile]
        base_config = _deep_merge(base_config, profile_config)

    # Apply CLI overrides
    if overrides:
        base_config = _apply_overrides(base_config, overrides)

    # Validate required fields
    _validate_config(base_config)

    logger.info(f"Loaded config profile: {profile}")
    return base_config


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two dictionaries, overlay values take precedence."""
    result = deepcopy(base)

    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)

    return result


def _apply_overrides(config: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """Apply dot-notation overrides to config."""
    result = deepcopy(config)

    for key, value in overrides.items():
        _set_nested_value(result, key, value)

    return result


def _set_nested_value(config: dict[str, Any], key_path: str, value: Any) -> None:
    """Set nested value using dot notation (e.g. 'ml.clustering.algo')."""
    keys = key_path.split(".")
    current = config

    # Navigate to parent of target key
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        elif not isinstance(current[key], dict):
            raise ConfigError(f"Cannot override {key_path}: {key} is not a dict")
        current = current[key]

    # Set final value
    final_key = keys[-1]
    current[final_key] = value
    logger.debug(f"Override applied: {key_path} = {value}")


def _validate_config(config: dict[str, Any]) -> None:
    """Validate required configuration fields."""
    required_sections = ["project", "run", "sources", "io"]

    for section in required_sections:
        if section not in config:
            raise ConfigError(f"Missing required config section: {section}")

    # Validate project info
    if "name" not in config["project"]:
        raise ConfigError("Missing project.name in config")

    # Validate I/O paths
    if "db_path" not in config["io"]:
        raise ConfigError("Missing io.db_path in config")


def get_profile_names(config_path: str | Path | None = None) -> list[str]:
    """Get list of available profile names."""
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        return ["development"]  # Default fallback

    try:
        with open(config_path, encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        profiles = ["development"]  # Always include default
        if "profiles" in config_data:
            profiles.extend(config_data["profiles"].keys())

        return sorted(profiles)
    except Exception:
        return ["development"]


# Configuration access helpers
def get_database_path(config: dict[str, Any]) -> str:
    """Get database path from config."""
    path = config["io"]["db_path"]
    if not isinstance(path, str):
        raise ConfigError(f"Database path must be string, got {type(path)}")
    return path


def get_exports_dir(config: dict[str, Any]) -> str:
    """Get exports directory from config."""
    exports_dir = config["io"]["exports_dir"]
    if not isinstance(exports_dir, str):
        raise ConfigError(f"Exports directory must be string, got {type(exports_dir)}")
    return exports_dir


def get_logging_config(config: dict[str, Any]) -> dict[str, Any]:
    """Get logging configuration."""
    logging_config = config.get(
        "logging",
        {"level": "INFO", "format": "text", "file_enabled": True, "console_enabled": True},
    )
    if not isinstance(logging_config, dict):
        raise ConfigError(f"Logging config must be dict, got {type(logging_config)}")
    return logging_config


def is_source_enabled(config: dict[str, Any], source: str) -> bool:
    """Check if a data source is enabled."""
    enabled = config.get("sources", {}).get(source, False)
    return bool(enabled)


if __name__ == "__main__":
    # Test configuration loading
    try:
        config = load_config(profile="production")
        print("✅ Production config loaded successfully")
        print(f"Project: {config['project']['name']} v{config['project']['version']}")
        print(f"Environment: {config['project']['environment']}")

        # Test overrides
        config_with_override = load_config(
            profile="validation",
            overrides={"ml.clustering.algo": "hdbscan", "run.seeds": ["override_test"]},
        )
        print(
            f"✅ Override test: clustering algo = {config_with_override['ml']['clustering']['algo']}"
        )
        print(f"✅ Override test: seeds = {config_with_override['run']['seeds']}")

    except ConfigError as e:
        print(f"❌ Config error: {e}")
