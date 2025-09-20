"""
Logging utilities for the keyword finder application.
"""

import logging
from pathlib import Path
from typing import Any


class NetworkError(Exception):
    """Exception raised for network-related errors."""

    def __init__(self, message: str, context: dict[str, Any] | None = None):
        super().__init__(message)
        self.context = context or {}


class ConfigError(Exception):
    """Exception raised for configuration-related errors."""

    def __init__(self, message: str, context: dict[str, Any] | None = None):
        super().__init__(message)
        self.context = context or {}


def setup_enhanced_logging(
    run_id: str,
    level: str = "INFO",
    log_file: str | None = None,
    console_enabled: bool = True,
    service_name: str = "keyword-intel",
    environment: str = "development",
    component: str = "main",
) -> None:
    """
    Setup enhanced enterprise logging with structured JSON format.

    Args:
        run_id: Unique identifier for this run
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for logging
        console_enabled: Whether to enable console logging
        service_name: Name of the service
        environment: Environment (development, production, test)
        component: Component name
    """
    # Convert string level to logging level
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Create logger
    logger = logging.getLogger()
    logger.setLevel(numeric_level)

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create formatter
    formatter = logging.Formatter(
        f"%(asctime)s [{service_name}] [{environment}] [{component}] [{run_id}] %(levelname)s %(name)s - %(message)s"
    )

    # Console handler
    if console_enabled:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # File handler
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)


def set_log_context(run_id: str, component: str, operation: str) -> None:
    """
    Set logging context for structured logging.

    Args:
        run_id: Unique identifier for this run
        component: Component name
        operation: Operation being performed
    """
    # This is a placeholder for more advanced logging context
    # In a real implementation, this might set thread-local variables
    # or use logging adapters
    logger = logging.getLogger(__name__)
    logger.info(
        f"Setting log context: run_id={run_id}, component={component}, operation={operation}"
    )


def load_config(config_path: str, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to the configuration file
        overrides: Optional dictionary of configuration overrides

    Returns:
        Configuration object with loaded data

    Raises:
        ConfigError: If configuration cannot be loaded
    """
    try:
        import yaml

        config_file = Path(config_path)
        if not config_file.exists():
            raise ConfigError(f"Configuration file not found: {config_path}")

        with open(config_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if overrides:
            # Apply overrides (deep merge)
            def deep_merge(base: dict, override: dict) -> dict:
                result = base.copy()
                for key, value in override.items():
                    if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                        result[key] = deep_merge(result[key], value)
                    else:
                        result[key] = value
                return result

            data = deep_merge(data, overrides)

        return data

    except ImportError:
        raise ConfigError("PyYAML is required for configuration loading") from None
    except (ValueError, OSError) as e:
        raise ConfigError(f"Failed to load configuration: {e}") from e
