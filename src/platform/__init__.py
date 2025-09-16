"""Platform infrastructure: CLI, config, logging."""

# Importaciones explícitas para evitar conflictos
from .cli import create_parser, parse_overrides
from .config_loader import ConfigError as ConfigLoaderError
from .config_loader import (
    get_database_path,
    get_exports_dir,
    get_logging_config,
    is_source_enabled,
    load_config,
)
from .env_config import (
    get_google_ads_credentials,
    load_dotenv_file,
    print_credentials_status,
    validate_credentials,
)
from .exceptions_enterprise import (
    ConfigError,
    DatabaseError,
    DataProcessingError,
    EnterpriseError,
    ErrorCategory,
    ErrorHandler,
    ErrorSeverity,
    ExportError,
    NetworkError,
    RateLimitError,
    TimeoutError,
    ValidationError,
    get_error_handler,
    handle_error,
)
from .logging_config_enterprise import (
    get_logger,
    log_metric,
    log_operation_end,
    log_operation_start,
    log_with_context,
    setup_logging,
    setup_logging_from_config,
)
from .rate_limiter import AdaptiveRateLimiter, RateLimitConfig, ThrottledSession
from .settings import AppConfig
from .settings import parse_overrides as settings_parse_overrides

__all__ = [
    "create_parser",
    "parse_overrides",
    "load_config",
    "get_database_path",
    "get_exports_dir",
    "get_logging_config",
    "is_source_enabled",
    "ConfigLoaderError",
    "load_dotenv_file",
    "get_google_ads_credentials",
    "validate_credentials",
    "print_credentials_status",
    "ConfigError",
    "ValidationError",
    "NetworkError",
    "TimeoutError",
    "DataProcessingError",
    "DatabaseError",
    "ExportError",
    "EnterpriseError",
    "ErrorCategory",
    "ErrorHandler",
    "ErrorSeverity",
    "RateLimitError",
    "get_error_handler",
    "handle_error",
    "setup_logging",
    "setup_logging_from_config",
    "get_logger",
    "log_with_context",
    "log_operation_start",
    "log_operation_end",
    "log_metric",
    "AdaptiveRateLimiter",
    "RateLimitConfig",
    "ThrottledSession",
    "AppConfig",
    "settings_parse_overrides",
]
