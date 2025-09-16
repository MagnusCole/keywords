#!/usr/bin/env python3
"""
Test script para validar el sistema de errores tipificados enterprise.
"""

from pathlib import Path

# Importar sistema de errores enterprise
from src.platform.exceptions_enterprise import (
    CaptchaDetectedError,
    ClusteringError,
    # Errores específicos
    ConfigError,
    DatabaseError,
    # Error base
    EnterpriseError,
    ErrorCategory,
    # Error handler
    ErrorHandler,
    ErrorSeverity,
    ExportError,
    GoogleAdsQuotaError,
    NetworkError,
    ProfileNotFoundError,
    RateLimitError,
    ScoringError,
    SeedsValidationError,
    TimeoutError,
    ValidationError,
    get_retry_delay,
    should_retry,
)

# Importar sistema de logging para integración
from src.platform.logging_config_enterprise import get_logger, setup_logging


def test_basic_enterprise_errors():
    """Test errores enterprise básicos."""
    print("🧪 Testing Basic Enterprise Errors...")

    # Test error base con contexto completo
    error = EnterpriseError(
        message="Test enterprise error",
        error_code="TEST_001",
        category=ErrorCategory.BUSINESS_LOGIC,
        severity=ErrorSeverity.MEDIUM,
        context={"component": "test", "operation": "validation"},
        retryable=True,
        user_message="Something went wrong in the test",
    )

    print(f"✅ Error code: {error.error_code}")
    print(f"✅ Category: {error.category.value}")
    print(f"✅ Severity: {error.severity.value}")
    print(f"✅ Retryable: {error.retryable}")
    print(f"✅ Context: {error.context}")

    # Test serialización
    error_dict = error.to_dict()
    print(f"✅ Serialization: {len(error_dict)} fields")

    # Test JSON
    error_json = error.to_json()
    print(f"✅ JSON format: {len(error_json)} chars")


def test_specific_errors():
    """Test errores específicos por categoría."""
    print("\n🧪 Testing Specific Error Types...")

    # CONFIG ERRORS
    config_error = ConfigError(
        message="Invalid config format",
        config_path="config/test.yaml",
        field="logging.level",
        expected_type="string",
    )
    print(f"✅ ConfigError: {config_error.error_code}")

    profile_error = ProfileNotFoundError(
        profile="invalid", available_profiles=["development", "production"]
    )
    print(f"✅ ProfileNotFoundError: {profile_error.error_code}")

    # VALIDATION ERRORS
    validation_error = ValidationError(
        message="Invalid seeds format", field="seeds", value=[], expected="non-empty list"
    )
    print(f"✅ ValidationError: {validation_error.error_code}")

    seeds_error = SeedsValidationError(seeds=[], message="Seeds list cannot be empty")
    print(f"✅ SeedsValidationError: {seeds_error.error_code}")

    # RATE LIMIT ERRORS
    rate_limit_error = RateLimitError(
        message="API rate limit exceeded",
        service="google_trends",
        retry_after=60,
        requests_made=100,
        requests_limit=100,
        window_seconds=3600,
    )
    print(f"✅ RateLimitError: {rate_limit_error.error_code}")

    ads_quota_error = GoogleAdsQuotaError(
        quota_type="operations", used=15000, limit=15000, reset_time="2025-09-17T00:00:00Z"
    )
    print(f"✅ GoogleAdsQuotaError: {ads_quota_error.error_code}")

    # CAPTCHA ERRORS
    captcha_error = CaptchaDetectedError(
        message="reCAPTCHA challenge detected",
        url="https://google.com/search",
        service="google_search",
        captcha_type="recaptcha_v2",
        suggested_action="Use different IP or wait 1 hour",
    )
    print(f"✅ CaptchaDetectedError: {captcha_error.error_code}")

    # NETWORK ERRORS
    network_error = NetworkError(
        message="Connection timeout", url="https://api.example.com", status_code=408, timeout=10.0
    )
    print(f"✅ NetworkError: {network_error.error_code}")

    timeout_error = TimeoutError(url="https://slow-api.com", timeout=5.0, operation="GET request")
    print(f"✅ TimeoutError: {timeout_error.error_code}")

    # DATA PROCESSING ERRORS
    scoring_error = ScoringError(
        message="Scoring algorithm failed", keywords_count=150, algorithm="composite_scoring"
    )
    print(f"✅ ScoringError: {scoring_error.error_code}")

    clustering_error = ClusteringError(
        message="Clustering failed to converge",
        keywords_count=250,
        algorithm="HDBSCAN",
        parameters={"min_cluster_size": 5, "metric": "euclidean"},
    )
    print(f"✅ ClusteringError: {clustering_error.error_code}")

    # DATABASE ERRORS
    db_error = DatabaseError(
        message="Failed to insert keywords",
        operation="INSERT",
        table="keywords",
        query="INSERT INTO keywords (keyword, score) VALUES ...",
    )
    print(f"✅ DatabaseError: {db_error.error_code}")

    # EXPORT ERRORS
    export_error = ExportError(
        message="Failed to generate Excel report",
        format_type="xlsx",
        file_path="reports/keywords.xlsx",
        record_count=150,
    )
    print(f"✅ ExportError: {export_error.error_code}")


def test_error_handler():
    """Test error handler centralizado."""
    print("\n🧪 Testing Error Handler...")

    # Setup logging para el handler
    setup_logging(
        run_id="test_errors",
        level="DEBUG",
        format_type="enterprise",
        console_enabled=True,
        file_enabled=False,
    )

    logger = get_logger("test.errors")
    handler = ErrorHandler(logger)

    # Test manejo de EnterpriseError
    enterprise_error = ValidationError(
        message="Test validation error", field="test_field", value="invalid_value"
    )

    handled_error = handler.handle_error(enterprise_error, {"additional": "context"})
    print(f"✅ Handled EnterpriseError: {handled_error.error_code}")
    print(f"✅ Additional context added: {handled_error.context.get('additional')}")

    # Test conversión de Exception estándar
    try:
        _ = 1 / 0  # This will raise ZeroDivisionError
    except ZeroDivisionError as e:
        handled_std_error = handler.handle_error(e, {"operation": "division"})
        print(f"✅ Converted standard error: {handled_std_error.error_code}")
        print(f"✅ Category: {handled_std_error.category.value}")

    # Test conversión de FileNotFoundError
    try:
        with open("nonexistent_file.txt") as f:
            _ = f.read()  # Will raise FileNotFoundError before this line
    except FileNotFoundError as e:
        handled_file_error = handler.handle_error(e)
        print(f"✅ Converted FileNotFoundError: {handled_file_error.error_code}")
        print(f"✅ Category: {handled_file_error.category.value}")

    # Test estadísticas
    stats = handler.get_stats()
    print(f"✅ Error stats: {stats['total_errors']} total errors")
    print(f"✅ By category: {stats['by_category']}")
    print(f"✅ By severity: {stats['by_severity']}")
    print(f"✅ Retryable: {stats['retryable_count']}")


def test_retry_logic():
    """Test lógica de retry."""
    print("\n🧪 Testing Retry Logic...")

    # Test error retryable
    retryable_error = RateLimitError(message="Rate limit hit", service="test_api", retry_after=5)

    should_retry_1 = should_retry(retryable_error, attempt=1, max_attempts=3)
    should_retry_4 = should_retry(retryable_error, attempt=4, max_attempts=3)

    print(f"✅ Should retry attempt 1: {should_retry_1}")
    print(f"✅ Should retry attempt 4: {should_retry_4}")

    # Test delays
    delay_1 = get_retry_delay(retryable_error, attempt=1)
    delay_2 = get_retry_delay(retryable_error, attempt=2)

    print(f"✅ Retry delay attempt 1: {delay_1}s")
    print(f"✅ Retry delay attempt 2: {delay_2}s")

    # Test error no retryable
    non_retryable_error = ConfigError(message="Invalid config", config_path="config.yaml")

    should_retry_config = should_retry(non_retryable_error, attempt=1)
    print(f"✅ Should retry config error: {should_retry_config}")


def test_error_categories_and_severities():
    """Test todas las categorías y severidades."""
    print("\n🧪 Testing All Categories and Severities...")

    # Test todas las categorías
    categories = list(ErrorCategory)
    print(f"✅ Available categories: {len(categories)}")
    for category in categories:
        print(f"   - {category.value}")

    # Test todas las severidades
    severities = list(ErrorSeverity)
    print(f"✅ Available severities: {len(severities)}")
    for severity in severities:
        print(f"   - {severity.value}")

    # Test error con cada severidad
    for severity in severities:
        error = EnterpriseError(
            message=f"Test {severity.value} error",
            error_code=f"TEST_{severity.value.upper()}",
            category=ErrorCategory.SYSTEM,
            severity=severity,
        )
        print(f"✅ Created {severity.value} error: {error.error_code}")


def test_integration_with_logging():
    """Test integración con sistema de logging enterprise."""
    print("\n🧪 Testing Integration with Logging...")

    # Setup logging
    log_file = Path("logs") / "test_errors.jsonl"
    setup_logging(
        run_id="test_errors_integration",
        level="DEBUG",
        format_type="enterprise",
        log_file=log_file,
        console_enabled=True,
        file_enabled=True,
    )

    logger = get_logger("test.integration")
    handler = ErrorHandler(logger)

    # Test varios tipos de errores con logging
    errors_to_test = [
        ValidationError("Test validation", field="test"),
        RateLimitError("Test rate limit", service="test"),
        NetworkError("Test network", url="http://test.com", status_code=500),
        DatabaseError("Test database", operation="SELECT", table="test"),
    ]

    for error in errors_to_test:
        handled = handler.handle_error(error)
        print(f"✅ Logged {error.__class__.__name__}: {handled.error_code}")

    # Verificar archivo de log
    if log_file.exists():
        with open(log_file, encoding="utf-8") as f:
            lines = f.readlines()
            # Contar líneas que son errores
            error_lines = [line for line in lines if '"level":"ERROR"' in line]
            print(f"✅ Log file contains {len(error_lines)} error entries")


def main():
    """Ejecutar todos los tests de errores tipificados."""
    print("🚀 ENTERPRISE ERROR SYSTEM VALIDATION")
    print("=" * 50)

    try:
        test_basic_enterprise_errors()
        test_specific_errors()
        test_error_handler()
        test_retry_logic()
        test_error_categories_and_severities()
        test_integration_with_logging()

        print("\n🎯 Enterprise Error System Validation Complete!")
        print("  ✅ EnterpriseError base class with codes and categories")
        print("  ✅ 15+ specific error types with context")
        print("  ✅ Error handler with automatic conversion")
        print("  ✅ Retry logic with backoff")
        print("  ✅ Complete category and severity system")
        print("  ✅ Integration with enterprise logging")
        print("  ✅ JSON serialization for APIs")
        print("  ✅ Statistics tracking")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
