"""
YAML configuration loader utilities.
"""

from pathlib import Path
from typing import cast

import yaml


def load_yaml_config(config_path: str) -> dict[str, object]:
    """
    Load YAML configuration file.

    Args:
        config_path: Path to YAML config file

    Returns:
        Configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If YAML parsing fails
    """
    config_file = Path(config_path)

    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    try:
        with open(config_file, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        if config is None:
            config = {}

        return cast(dict[str, object], config)

    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Failed to parse YAML config {config_path}: {e}") from e


def merge_configs(
    base_config: dict[str, object], override_config: dict[str, object]
) -> dict[str, object]:
    """
    Merge two configuration dictionaries recursively.

    Args:
        base_config: Base configuration
        override_config: Override configuration

    Returns:
        Merged configuration dictionary
    """
    merged = base_config.copy()

    for key, value in override_config.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            # Cast to dict[str, object] for recursion
            merged[key] = merge_configs(
                cast(dict[str, object], merged[key]),
                cast(dict[str, object], value),
            )
        else:
            merged[key] = value

    return merged
