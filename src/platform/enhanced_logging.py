"""
Enhanced Enterprise Logging v2.0.0 for PR-06

This module provides production-grade logging with:
- Structured JSON logging with correlation IDs
- Error classification and severity levels
- Environment-specific configuration
- Performance monitoring and metrics
- Centralized logging configuration
- Audit trail and compliance features
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import os
import sys
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Thread-local storage for correlation context
_context = threading.local()


@dataclass
class LogContext:
    """Logging context with correlation IDs and metadata."""
    
    correlation_id: str
    run_id: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    operation: Optional[str] = None
    component: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass 
class ErrorClassification:
    """Error classification for better incident management."""
    
    category: str  # SYSTEM, USER, NETWORK, DATA, CONFIG, SECURITY
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    recoverable: bool
    component: str
    error_code: Optional[str] = None
    upstream_service: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {k: v for k, v in asdict(self).items() if v is not None}


def set_log_context(
    correlation_id: str | None = None,
    run_id: str | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
    operation: str | None = None,
    component: str | None = None
) -> None:
    """Set logging context for current thread."""
    if not hasattr(_context, 'log_context'):
        _context.log_context = LogContext(
            correlation_id=correlation_id or str(uuid.uuid4()),
            run_id=run_id or f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
    
    # Update existing context
    if correlation_id:
        _context.log_context.correlation_id = correlation_id
    if run_id:
        _context.log_context.run_id = run_id
    if user_id:
        _context.log_context.user_id = user_id
    if session_id:
        _context.log_context.session_id = session_id
    if operation:
        _context.log_context.operation = operation
    if component:
        _context.log_context.component = component


def get_log_context() -> LogContext:
    """Get current logging context."""
    if not hasattr(_context, 'log_context'):
        set_log_context()  # Initialize with defaults
    return _context.log_context


def clear_log_context() -> None:
    """Clear logging context for current thread."""
    if hasattr(_context, 'log_context'):
        delattr(_context, 'log_context')


class EnhancedJSONFormatter(logging.Formatter):
    """Enhanced JSON formatter with correlation IDs and error classification."""
    
    def __init__(
        self,
        service_name: str = "keyword-intel",
        version: str = "1.0.0",
        include_performance_metrics: bool = True
    ):
        super().__init__()
        self.service_name = service_name
        self.version = version
        self.include_performance_metrics = include_performance_metrics
        self.start_time = time.time()
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        context = get_log_context()
        
        # Base log entry with correlation context
        log_entry = {
            "@timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "@version": "2.0.0",
            "service": self.service_name,
            "version": self.version,
            "environment": os.getenv("ENVIRONMENT", "development"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation": context.to_dict(),
            "source": {
                "file": record.filename,
                "line": record.lineno,
                "function": record.funcName,
                "module": record.module,
                "path": record.pathname,
            },
            "execution": {
                "thread_id": record.thread,
                "thread_name": getattr(record, "threadName", "MainThread"),
                "process_id": record.process,
                "process_name": getattr(record, "processName", "MainProcess"),
            },
            "timing": {
                "created": record.created,
                "relative_ms": record.relativeCreated,
                "uptime_seconds": time.time() - self.start_time
            }
        }
        
        # Add performance metrics if enabled
        if self.include_performance_metrics:
            log_entry["performance"] = self._get_performance_metrics()
        
        # Add error classification for errors
        if record.levelno >= logging.ERROR:
            error_classification = getattr(record, 'error_classification', None)
            if error_classification and isinstance(error_classification, ErrorClassification):
                log_entry["error"] = error_classification.to_dict()
            else:
                log_entry["error"] = self._classify_error(record)
        
        # Add exception information
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info) if record.exc_info else None
            }
        
        # Add extra fields
        extra_fields = self._extract_extra_fields(record)
        if extra_fields:
            log_entry["extra"] = extra_fields
        
        return json.dumps(log_entry, ensure_ascii=False, separators=(",", ":"))
    
    def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get basic performance metrics."""
        try:
            import psutil
            process = psutil.Process()
            return {
                "memory_mb": round(process.memory_info().rss / 1024 / 1024, 2),
                "cpu_percent": process.cpu_percent(),
                "open_files": len(process.open_files()),
                "threads": process.num_threads()
            }
        except ImportError:
            # psutil not available
            return {}
        except Exception:
            return {}
    
    def _classify_error(self, record: logging.LogRecord) -> Dict[str, Any]:
        """Automatically classify error based on content and context."""
        message = record.getMessage().lower()
        
        # Simple error classification based on message content
        if any(term in message for term in ["connection", "timeout", "network", "http"]):
            category = "NETWORK"
            severity = "MEDIUM"
        elif any(term in message for term in ["database", "sqlite", "sql", "constraint"]):
            category = "DATA"
            severity = "HIGH"
        elif any(term in message for term in ["config", "setting", "yaml", "invalid"]):
            category = "CONFIG"
            severity = "MEDIUM"
        elif any(term in message for term in ["memory", "disk", "cpu", "resource"]):
            category = "SYSTEM"
            severity = "HIGH"
        elif any(term in message for term in ["auth", "permission", "security", "token"]):
            category = "SECURITY"
            severity = "HIGH"
        else:
            category = "USER"
            severity = "LOW"
        
        return {
            "category": category,
            "severity": severity,
            "recoverable": record.levelno < logging.CRITICAL,
            "component": record.module or "unknown",
            "auto_classified": True
        }
    
    def _extract_extra_fields(self, record: logging.LogRecord) -> Dict[str, Any]:
        """Extract extra fields from log record."""
        excluded_keys = {
            "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
            "module", "lineno", "funcName", "created", "msecs", "relativeCreated",
            "thread", "threadName", "processName", "process", "getMessage", "exc_info",
            "exc_text", "stack_info", "error_classification"
        }
        
        extra = {}
        for key, value in record.__dict__.items():
            if key not in excluded_keys:
                try:
                    # Ensure value is JSON serializable
                    json.dumps(value)
                    extra[key] = value
                except (TypeError, ValueError):
                    extra[key] = str(value)
        
        return extra


class StructuredLogger:
    """Enhanced structured logger with correlation support."""
    
    def __init__(self, name: str, level: int = logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
    
    def _log_with_context(
        self,
        level: int,
        message: str,
        error_classification: ErrorClassification | None = None,
        operation: str | None = None,
        **kwargs
    ) -> None:
        """Log with enhanced context and classification."""
        # Set operation in context if provided
        if operation:
            context = get_log_context()
            context.operation = operation
        
        # Create log record with extra fields
        extra = kwargs.copy()
        if error_classification:
            extra['error_classification'] = error_classification
        
        self.logger.log(level, message, extra=extra)
    
    def info(self, message: str, operation: str | None = None, **kwargs) -> None:
        """Log info message with context."""
        self._log_with_context(logging.INFO, message, operation=operation, **kwargs)
    
    def warning(self, message: str, operation: str | None = None, **kwargs) -> None:
        """Log warning message with context."""
        self._log_with_context(logging.WARNING, message, operation=operation, **kwargs)
    
    def error(
        self,
        message: str,
        error_classification: ErrorClassification | None = None,
        operation: str | None = None,
        **kwargs
    ) -> None:
        """Log error message with classification."""
        self._log_with_context(
            logging.ERROR, message, error_classification, operation, **kwargs
        )
    
    def critical(
        self,
        message: str,
        error_classification: ErrorClassification | None = None,
        operation: str | None = None,
        **kwargs
    ) -> None:
        """Log critical message with classification."""
        self._log_with_context(
            logging.CRITICAL, message, error_classification, operation, **kwargs
        )
    
    def debug(self, message: str, operation: str | None = None, **kwargs) -> None:
        """Log debug message with context."""
        self._log_with_context(logging.DEBUG, message, operation=operation, **kwargs)


def setup_enhanced_logging(
    run_id: str = "",
    correlation_id: str = "",
    level: str = "INFO",
    log_file: str | Path | None = None,
    console_enabled: bool = True,
    service_name: str = "keyword-intel",
    environment: str = "",
    component: str = ""
) -> None:
    """
    Setup enhanced enterprise logging with correlation IDs.
    
    Args:
        run_id: Run identifier for tracking
        correlation_id: Correlation ID for request tracing
        level: Logging level
        log_file: Optional log file path
        console_enabled: Enable console logging
        service_name: Service name for logs
        environment: Environment (dev, test, prod)
        component: Component name
    """
    # Set environment
    if environment:
        os.environ["ENVIRONMENT"] = environment
    
    # Initialize logging context
    set_log_context(
        correlation_id=correlation_id or str(uuid.uuid4()),
        run_id=run_id or f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        component=component
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Setup formatter
    formatter = EnhancedJSONFormatter(
        service_name=service_name,
        include_performance_metrics=True
    )
    
    # Console handler
    if console_enabled:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def get_structured_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance."""
    return StructuredLogger(name)


# Error classification helpers
def create_network_error(component: str, recoverable: bool = True) -> ErrorClassification:
    """Create network error classification."""
    return ErrorClassification(
        category="NETWORK",
        severity="MEDIUM",
        recoverable=recoverable,
        component=component
    )


def create_data_error(component: str, recoverable: bool = False) -> ErrorClassification:
    """Create data error classification."""
    return ErrorClassification(
        category="DATA", 
        severity="HIGH",
        recoverable=recoverable,
        component=component
    )


def create_config_error(component: str, recoverable: bool = True) -> ErrorClassification:
    """Create configuration error classification."""
    return ErrorClassification(
        category="CONFIG",
        severity="MEDIUM", 
        recoverable=recoverable,
        component=component
    )


def create_system_error(component: str, recoverable: bool = False) -> ErrorClassification:
    """Create system error classification."""
    return ErrorClassification(
        category="SYSTEM",
        severity="HIGH",
        recoverable=recoverable,
        component=component
    )