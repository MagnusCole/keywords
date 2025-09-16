"""
Sistema de excepciones enterprise con códigos, categorías y handling centralizado.
"""

from __future__ import annotations

import json
import traceback
from datetime import datetime
from enum import Enum
from typing import Any


class ErrorCategory(Enum):
    """Categorías de errores enterprise."""

    CONFIGURATION = "configuration"
    VALIDATION = "validation"
    NETWORK = "network"
    RATE_LIMIT = "rate_limit"
    AUTHENTICATION = "authentication"
    DATA_PROCESSING = "data_processing"
    DATABASE = "database"
    EXPORT = "export"
    SYSTEM = "system"
    EXTERNAL_API = "external_api"
    BUSINESS_LOGIC = "business_logic"


class ErrorSeverity(Enum):
    """Severidad de errores enterprise."""

    LOW = "low"  # Warning, no afecta funcionalidad
    MEDIUM = "medium"  # Error recuperable con retry
    HIGH = "high"  # Error crítico pero sistema continúa
    CRITICAL = "critical"  # Error que requiere intervención inmediata


class EnterpriseError(Exception):
    """Excepción base enterprise con códigos, categorías y contexto."""

    def __init__(
        self,
        message: str,
        error_code: str,
        category: ErrorCategory,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: dict[str, Any] | None = None,
        cause: Exception | None = None,
        retryable: bool = False,
        user_message: str | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.category = category
        self.severity = severity
        self.context = context or {}
        self.cause = cause
        self.retryable = retryable
        self.user_message = user_message or message
        self.timestamp = datetime.now().isoformat()
        self.traceback_str = traceback.format_exc() if cause else None

    def to_dict(self) -> dict[str, Any]:
        """Convierte la excepción a diccionario para logging/API."""
        return {
            "error_code": self.error_code,
            "category": self.category.value,
            "severity": self.severity.value,
            "message": self.message,
            "user_message": self.user_message,
            "context": self.context,
            "retryable": self.retryable,
            "timestamp": self.timestamp,
            "cause": str(self.cause) if self.cause else None,
            "traceback": self.traceback_str,
        }

    def to_json(self) -> str:
        """Convierte la excepción a JSON."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


# =============================================================================
# CONFIGURATION ERRORS
# =============================================================================


class ConfigError(EnterpriseError):
    """Error en configuración del sistema."""

    def __init__(
        self,
        message: str,
        config_path: str | None = None,
        field: str | None = None,
        expected_type: str | None = None,
        cause: Exception | None = None,
    ):
        context = {"config_path": config_path, "field": field, "expected_type": expected_type}
        super().__init__(
            message=message,
            error_code="CONFIG_001",
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.HIGH,
            context=context,
            cause=cause,
            retryable=False,
        )


class ProfileNotFoundError(ConfigError):
    """Profile de configuración no encontrado."""

    def __init__(self, profile: str, available_profiles: list[str]):
        super().__init__(
            message=f"Profile '{profile}' not found", config_path=None, field="profiles"
        )
        self.error_code = "CONFIG_002"
        self.context.update(
            {"requested_profile": profile, "available_profiles": available_profiles}
        )


# =============================================================================
# VALIDATION ERRORS
# =============================================================================


class ValidationError(EnterpriseError):
    """Error de validación de datos de entrada."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: Any = None,
        expected: str | None = None,
        constraints: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ):
        context = {
            "field": field,
            "value": str(value) if value is not None else None,
            "expected": expected,
            "constraints": constraints,
        }
        super().__init__(
            message=message,
            error_code="VALIDATION_001",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            cause=cause,
            retryable=False,
            user_message=f"Invalid {field}: {message}" if field else message,
        )


class SeedsValidationError(ValidationError):
    """Error específico en validación de seeds."""

    def __init__(self, seeds: list[str], message: str = "Invalid seeds provided"):
        super().__init__(message=message, field="seeds", value=seeds)
        self.error_code = "VALIDATION_002"


# =============================================================================
# RATE LIMIT ERRORS
# =============================================================================


class RateLimitError(EnterpriseError):
    """Error de rate limiting."""

    def __init__(
        self,
        message: str,
        service: str,
        retry_after: int | None = None,
        requests_made: int | None = None,
        requests_limit: int | None = None,
        window_seconds: int | None = None,
    ):
        context = {
            "service": service,
            "retry_after_seconds": retry_after,
            "requests_made": requests_made,
            "requests_limit": requests_limit,
            "window_seconds": window_seconds,
        }
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_001",
            category=ErrorCategory.RATE_LIMIT,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            retryable=True,
            user_message=(
                f"Rate limit exceeded for {service}. Retry in {retry_after}s"
                if retry_after
                else f"Rate limit exceeded for {service}"
            ),
        )


class GoogleAdsQuotaError(RateLimitError):
    """Error específico de cuota de Google Ads."""

    def __init__(self, quota_type: str, used: int, limit: int, reset_time: str | None = None):
        super().__init__(
            message=f"Google Ads {quota_type} quota exceeded: {used}/{limit}", service="google_ads"
        )
        self.error_code = "RATE_LIMIT_002"
        self.context.update(
            {"quota_type": quota_type, "used": used, "limit": limit, "reset_time": reset_time}
        )


# =============================================================================
# CAPTCHA AND BLOCKING ERRORS
# =============================================================================


class CaptchaDetectedError(EnterpriseError):
    """Error cuando se detecta captcha o bloqueo."""

    def __init__(
        self,
        message: str,
        url: str,
        service: str,
        captcha_type: str | None = None,
        suggested_action: str | None = None,
    ):
        context = {
            "url": url,
            "service": service,
            "captcha_type": captcha_type,
            "suggested_action": suggested_action or "Switch IP or wait before retrying",
        }
        super().__init__(
            message=message,
            error_code="CAPTCHA_001",
            category=ErrorCategory.EXTERNAL_API,
            severity=ErrorSeverity.HIGH,
            context=context,
            retryable=False,
            user_message=f"Access blocked by {service}. {suggested_action or 'Manual intervention required.'}",
        )


# =============================================================================
# NETWORK ERRORS
# =============================================================================


class NetworkError(EnterpriseError):
    """Error de red o conectividad."""

    def __init__(
        self,
        message: str,
        url: str | None = None,
        status_code: int | None = None,
        timeout: float | None = None,
        cause: Exception | None = None,
    ):
        context = {"url": url, "status_code": status_code, "timeout_seconds": timeout}
        # Determinar si es retryable basado en el status code
        retryable = status_code in [408, 429, 500, 502, 503, 504] if status_code else True

        super().__init__(
            message=message,
            error_code="NETWORK_001",
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            cause=cause,
            retryable=retryable,
        )


class TimeoutError(NetworkError):
    """Error específico de timeout."""

    def __init__(self, url: str, timeout: float, operation: str = "request"):
        super().__init__(
            message=f"{operation.title()} timeout after {timeout}s", url=url, timeout=timeout
        )
        self.error_code = "NETWORK_002"


# =============================================================================
# DATA PROCESSING ERRORS
# =============================================================================


class DataProcessingError(EnterpriseError):
    """Error en procesamiento de datos."""

    def __init__(
        self,
        message: str,
        operation: str,
        data_type: str | None = None,
        record_count: int | None = None,
        cause: Exception | None = None,
    ):
        context = {"operation": operation, "data_type": data_type, "record_count": record_count}
        super().__init__(
            message=message,
            error_code="DATA_001",
            category=ErrorCategory.DATA_PROCESSING,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            cause=cause,
            retryable=False,
        )


class ScoringError(DataProcessingError):
    """Error en scoring de keywords."""

    def __init__(self, message: str, keywords_count: int, algorithm: str):
        super().__init__(
            message=message, operation="scoring", data_type="keywords", record_count=keywords_count
        )
        self.error_code = "DATA_002"
        self.context["algorithm"] = algorithm


class ClusteringError(DataProcessingError):
    """Error en clustering de keywords."""

    def __init__(
        self, message: str, keywords_count: int, algorithm: str, parameters: dict | None = None
    ):
        super().__init__(
            message=message,
            operation="clustering",
            data_type="keywords",
            record_count=keywords_count,
        )
        self.error_code = "DATA_003"
        self.context.update({"algorithm": algorithm, "parameters": parameters})


# =============================================================================
# DATABASE ERRORS
# =============================================================================


class DatabaseError(EnterpriseError):
    """Error en operaciones de base de datos."""

    def __init__(
        self,
        message: str,
        operation: str,
        table: str | None = None,
        query: str | None = None,
        cause: Exception | None = None,
    ):
        context = {
            "operation": operation,
            "table": table,
            "query": query[:200] + "..." if query and len(query) > 200 else query,
        }
        super().__init__(
            message=message,
            error_code="DATABASE_001",
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.HIGH,
            context=context,
            cause=cause,
            retryable=True,
        )


# =============================================================================
# EXPORT ERRORS
# =============================================================================


class ExportError(EnterpriseError):
    """Error en exportación de datos."""

    def __init__(
        self,
        message: str,
        format_type: str,
        file_path: str | None = None,
        record_count: int | None = None,
        cause: Exception | None = None,
    ):
        context = {"format_type": format_type, "file_path": file_path, "record_count": record_count}
        super().__init__(
            message=message,
            error_code="EXPORT_001",
            category=ErrorCategory.EXPORT,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            cause=cause,
            retryable=True,
        )


# =============================================================================
# ERROR HANDLING UTILITIES
# =============================================================================


class ErrorHandler:
    """Manejador centralizado de errores enterprise."""

    def __init__(self, logger=None):
        self.logger = logger
        self.error_stats = {
            "total_errors": 0,
            "by_category": {},
            "by_severity": {},
            "retryable_count": 0,
        }

    def handle_error(
        self, error: Exception, context: dict[str, Any] | None = None, log_level: str = "ERROR"
    ) -> EnterpriseError:
        """Maneja cualquier error convirtiéndolo a EnterpriseError si es necesario."""

        # Si ya es EnterpriseError, agregamos contexto adicional
        if isinstance(error, EnterpriseError):
            if context:
                error.context.update(context)
            enterprise_error = error
        else:
            # Convertir Exception estándar a EnterpriseError
            enterprise_error = self._convert_to_enterprise_error(error, context)

        # Actualizar estadísticas
        self._update_stats(enterprise_error)

        # Log del error
        if self.logger:
            self._log_error(enterprise_error, log_level)

        return enterprise_error

    def _convert_to_enterprise_error(
        self, error: Exception, context: dict[str, Any] | None = None
    ) -> EnterpriseError:
        """Convierte una excepción estándar a EnterpriseError."""

        error_type = type(error).__name__

        # Mapeo de tipos de error comunes
        if isinstance(error, ConnectionError | OSError):
            return NetworkError(message=str(error), cause=error)
        elif isinstance(error, FileNotFoundError):
            return ConfigError(message=f"File not found: {str(error)}", cause=error)
        elif isinstance(error, ValueError):
            return ValidationError(message=str(error), cause=error)
        elif isinstance(error, KeyError):
            return ConfigError(message=f"Missing required key: {str(error)}", cause=error)
        else:
            # Error genérico del sistema
            return EnterpriseError(
                message=f"{error_type}: {str(error)}",
                error_code="SYSTEM_001",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.HIGH,
                context=context or {"original_type": error_type},
                cause=error,
            )

    def _update_stats(self, error: EnterpriseError) -> None:
        """Actualiza estadísticas de errores."""
        self.error_stats["total_errors"] += 1

        category = error.category.value
        self.error_stats["by_category"][category] = (
            self.error_stats["by_category"].get(category, 0) + 1
        )

        severity = error.severity.value
        self.error_stats["by_severity"][severity] = (
            self.error_stats["by_severity"].get(severity, 0) + 1
        )

        if error.retryable:
            self.error_stats["retryable_count"] += 1

    def _log_error(self, error: EnterpriseError, level: str) -> None:
        """Log estructurado del error."""
        if self.logger is not None and hasattr(self.logger, "log"):
            numeric_level = getattr(__import__("logging"), level.upper(), 40)  # ERROR = 40
            self.logger.log(
                numeric_level,
                f"[{error.error_code}] {error.message}",
                extra={
                    "error_code": error.error_code,
                    "error_category": error.category.value,
                    "error_severity": error.severity.value,
                    "error_context": error.context,
                    "retryable": error.retryable,
                },
            )
        else:
            print(f"ERROR [{error.error_code}]: {error.message}")

    def get_stats(self) -> dict[str, Any]:
        """Obtiene estadísticas de errores."""
        return dict(self.error_stats)

    def reset_stats(self) -> None:
        """Resetea estadísticas de errores."""
        self.error_stats = {
            "total_errors": 0,
            "by_category": {},
            "by_severity": {},
            "retryable_count": 0,
        }


# =============================================================================
# RETRY UTILITIES
# =============================================================================


def should_retry(error: EnterpriseError, attempt: int, max_attempts: int = 3) -> bool:
    """Determina si un error debe ser reintentado."""
    return (
        error.retryable
        and attempt < max_attempts
        and error.severity in [ErrorSeverity.LOW, ErrorSeverity.MEDIUM]
    )


def get_retry_delay(error: EnterpriseError, attempt: int, base_delay: float = 1.0) -> float:
    """Calcula el delay para retry con backoff exponencial."""
    if error.category == ErrorCategory.RATE_LIMIT:
        # Para rate limits, usar el retry_after si está disponible
        retry_after = error.context.get("retry_after_seconds")
        if retry_after and isinstance(retry_after, int | float):
            return max(float(retry_after), base_delay)

    # Backoff exponencial estándar
    return float(base_delay * (2 ** (attempt - 1)))


# Global error handler instance
_global_error_handler: ErrorHandler | None = None


def get_error_handler() -> ErrorHandler:
    """Obtiene el error handler global."""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler()
    return _global_error_handler


def set_error_handler(handler: ErrorHandler) -> None:
    """Establece el error handler global."""
    global _global_error_handler
    _global_error_handler = handler


def handle_error(
    error: Exception, context: dict[str, Any] | None = None, log_level: str = "ERROR"
) -> EnterpriseError:
    """Función de conveniencia para manejar errores."""
    return get_error_handler().handle_error(error, context, log_level)
