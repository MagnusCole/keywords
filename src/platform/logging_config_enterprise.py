"""
Configuración centralizada de logging enterprise con soporte JSONL estructurado.
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import os
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, cast

# Thread-local storage para run_id compartido
_local = threading.local()


def set_run_id(run_id: str) -> None:
    """Set run_id para el thread actual."""
    _local.run_id = run_id


def get_run_id() -> str:
    """Get run_id del thread actual o generar uno por defecto."""
    if hasattr(_local, "run_id"):
        return cast(str, _local.run_id)
    return f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


class JSONFormatter(logging.Formatter):
    """Formatter que produce logs en formato JSONL estructurado."""

    def __init__(self, run_id: str | None = None, include_extra: bool = True):
        super().__init__()
        self.run_id = run_id
        self.include_extra = include_extra

    def format(self, record: logging.LogRecord) -> str:
        """Convierte LogRecord a JSON estructurado."""
        # Usar run_id del thread actual si no se especificó uno
        current_run_id = self.run_id or get_run_id()

        # Datos base del log
        log_data: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "run_id": current_run_id,
            "level": record.levelname,
            "component": record.name,
            "message": record.getMessage(),
            "thread": record.thread,
            "process": record.process,
        }

        # Agregar ubicación del código
        log_data["location"] = {
            "file": record.filename,
            "line": record.lineno,
            "function": record.funcName,
            "module": record.module,
        }

        # Agregar contexto adicional enterprise si está habilitado
        if self.include_extra:
            extra_data = {}
            extra_keys = set(record.__dict__.keys()) - {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "getMessage",
                "exc_info",
                "exc_text",
                "stack_info",
            }
            for key in extra_keys:
                extra_data[key] = getattr(record, key)

            if extra_data:
                log_data["extra_data"] = extra_data

        # Agregar exception info si existe
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Agregar stack trace para errores críticos
        if record.levelno >= logging.ERROR and record.stack_info:
            log_data["stack_trace"] = record.stack_info

        return json.dumps(log_data, ensure_ascii=False, separators=(",", ":"))


class EnterpriseJSONFormatter(JSONFormatter):
    """Formatter JSONL enterprise con campos adicionales y esquema fijo."""

    def __init__(self, run_id: str | None = None, service_name: str = "keyword-finder"):
        super().__init__(run_id, include_extra=True)
        self.service_name = service_name
        self.version = "1.0.0"

    def format(self, record: logging.LogRecord) -> str:
        """Format con esquema enterprise completo."""
        current_run_id = self.run_id or get_run_id()

        # Esquema enterprise completo
        log_entry = {
            "@timestamp": datetime.fromtimestamp(record.created).isoformat() + "Z",
            "@version": "1",
            "service": self.service_name,
            "version": self.version,
            "environment": os.getenv("ENVIRONMENT", "development"),
            "run_id": current_run_id,
            "level": record.levelname,
            "logger": record.name,
            "component": self._extract_component(record.name),
            "message": record.getMessage(),
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
            "timing": {"created": record.created, "relative_ms": record.relativeCreated},
        }

        # Agregar campos extra si existen
        extra_keys = set(record.__dict__.keys()) - {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
            "getMessage",
            "exc_info",
            "exc_text",
            "stack_info",
        }

        if extra_keys:
            log_entry["extra"] = {key: getattr(record, key) for key in extra_keys}

        # Agregar exception si existe
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info),
            }

        return json.dumps(log_entry, ensure_ascii=False, separators=(",", ":"))

    def _extract_component(self, logger_name: str) -> str:
        """Extrae el componente del logger name."""
        if "." in logger_name:
            parts = logger_name.split(".")
            # Usar la parte más específica como componente
            return parts[-1]
        return logger_name


class ASCIIConsoleHandler(logging.StreamHandler):
    """Handler que maneja encoding Windows de forma segura."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            # Convertir caracteres problemáticos para Windows console
            safe_msg = msg.encode("ascii", errors="replace").decode("ascii")
            stream = self.stream
            stream.write(safe_msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)


def create_rotating_file_handler(
    log_file: Path, max_bytes: int = 10 * 1024 * 1024, backup_count: int = 5  # 10MB
) -> logging.handlers.RotatingFileHandler:
    """Crea un RotatingFileHandler con configuración enterprise."""
    log_file.parent.mkdir(parents=True, exist_ok=True)

    handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    return handler


def create_timed_file_handler(
    log_file: Path, when: str = "D", interval: int = 1, backup_count: int = 30  # Daily
) -> logging.handlers.TimedRotatingFileHandler:
    """Crea un TimedRotatingFileHandler para logs por tiempo."""
    log_file.parent.mkdir(parents=True, exist_ok=True)

    handler = logging.handlers.TimedRotatingFileHandler(
        log_file, when=when, interval=interval, backupCount=backup_count, encoding="utf-8"
    )
    return handler


def setup_logging(
    run_id: str | None = None,
    level: str = "INFO",
    format_type: str = "enterprise",  # enterprise|json|text
    log_file: str | Path | None = None,
    console_enabled: bool = True,
    file_enabled: bool = True,
    rotation: str = "size",  # size|time|none
    max_file_size: str = "10MB",
    max_files: int = 5,
    service_name: str = "keyword-finder",
) -> None:
    """
    Configura el sistema de logging enterprise.

    Args:
        run_id: ID único para correlacionar logs de esta ejecución
        level: Nivel de logging (DEBUG, INFO, WARNING, ERROR)
        format_type: Tipo de formato (enterprise, json, text)
        log_file: Archivo para guardar logs (opcional)
        console_enabled: Si habilitar logging en consola
        file_enabled: Si habilitar logging en archivo
        rotation: Tipo de rotación (size, time, none)
        max_file_size: Tamaño máximo por archivo (ej: "10MB")
        max_files: Número máximo de archivos de backup
        service_name: Nombre del servicio para logs enterprise
    """
    # Establecer run_id globalmente
    if run_id:
        set_run_id(run_id)

    # Limpiar handlers existentes
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Configurar nivel
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    root_logger.setLevel(numeric_level)

    # Seleccionar formatter
    formatter: logging.Formatter
    if format_type == "enterprise":
        formatter = EnterpriseJSONFormatter(run_id, service_name)
    elif format_type == "json":
        formatter = JSONFormatter(run_id)
    else:
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Handler para consola
    if console_enabled:
        console_handler = ASCIIConsoleHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # Handler para archivo si se especifica
    if file_enabled and log_file:
        log_path = Path(log_file)

        # Seleccionar tipo de handler según rotación
        file_handler: logging.Handler
        if rotation == "size":
            size_bytes = _parse_size(max_file_size)
            file_handler = create_rotating_file_handler(log_path, size_bytes, max_files)
        elif rotation == "time":
            file_handler = create_timed_file_handler(log_path, backup_count=max_files)
        else:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_path, encoding="utf-8")

        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def _parse_size(size_str: str) -> int:
    """Parsea string de tamaño a bytes (ej: '10MB' -> 10485760)."""
    size_str = size_str.upper()
    if size_str.endswith("MB"):
        return int(size_str[:-2]) * 1024 * 1024
    elif size_str.endswith("KB"):
        return int(size_str[:-2]) * 1024
    elif size_str.endswith("GB"):
        return int(size_str[:-2]) * 1024 * 1024 * 1024
    else:
        return int(size_str)  # Asume bytes


def setup_logging_from_config(config: dict[str, Any], run_id: str | None = None) -> None:
    """Configura logging desde diccionario de configuración."""
    logging_config = config.get("logging", {})

    # Extraer configuraciones con defaults
    level = logging_config.get("level", "INFO")
    format_type = logging_config.get("format", "enterprise")
    console_enabled = logging_config.get("console_enabled", True)
    file_enabled = logging_config.get("file_enabled", True)

    # Configuración de archivo
    log_file = None
    if file_enabled:
        logs_dir = config.get("io", {}).get("logs_dir", "logs")
        run_id_part = run_id or get_run_id()
        log_file = Path(logs_dir) / f"{run_id_part}.jsonl"

    # Configuración de rotación
    rotation = logging_config.get("rotation", "size")
    max_file_size = logging_config.get("max_file_size", "10MB")
    max_files = logging_config.get("max_files", 5)

    # Nombre del servicio
    service_name = config.get("project", {}).get("name", "keyword-finder")

    setup_logging(
        run_id=run_id,
        level=level,
        format_type=format_type,
        log_file=log_file,
        console_enabled=console_enabled,
        file_enabled=file_enabled,
        rotation=rotation,
        max_file_size=max_file_size,
        max_files=max_files,
        service_name=service_name,
    )


def get_logger(name: str) -> logging.Logger:
    """Obtiene un logger configurado para el módulo especificado."""
    return logging.getLogger(name)


def log_with_context(logger: logging.Logger, level: int, message: str, **context: Any) -> None:
    """Log con contexto adicional como campos extra."""
    logger.log(level, message, extra=context)


def log_operation_start(logger: logging.Logger, operation: str, **context: Any) -> None:
    """Log inicio de operación enterprise."""
    log_with_context(
        logger,
        logging.INFO,
        f"Operation started: {operation}",
        operation=operation,
        status="started",
        **context,
    )


def log_operation_end(
    logger: logging.Logger, operation: str, duration_ms: float, success: bool = True, **context: Any
) -> None:
    """Log fin de operación enterprise."""
    status = "completed" if success else "failed"
    log_with_context(
        logger,
        logging.INFO if success else logging.ERROR,
        f"Operation {status}: {operation}",
        operation=operation,
        status=status,
        duration_ms=duration_ms,
        **context,
    )


def log_metric(
    logger: logging.Logger, metric_name: str, value: Any, unit: str = "", **context: Any
) -> None:
    """Log métrica enterprise."""
    log_with_context(
        logger,
        logging.INFO,
        f"Metric: {metric_name}={value}{unit}",
        metric_name=metric_name,
        metric_value=value,
        metric_unit=unit,
        **context,
    )
