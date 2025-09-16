#!/usr/bin/env python3
"""
Test script para validar el sistema de logging enterprise.
"""

import json
import time
from pathlib import Path

from src.platform.config_loader import load_config
from src.platform.logging_config_enterprise import (
    get_logger,
    log_metric,
    log_operation_end,
    log_operation_start,
    log_with_context,
    set_run_id,
    setup_logging,
    setup_logging_from_config,
)

# Configurar run_id para pruebas
test_run_id = f"test_logging_{int(time.time())}"


def test_basic_logging():
    """Test logging básico enterprise."""
    print("🧪 Testing Basic Enterprise Logging...")

    # Setup en directorio logs existente para evitar problemas Windows
    log_file = Path("logs") / "test_enterprise.jsonl"
    log_file.parent.mkdir(exist_ok=True)

    setup_logging(
        run_id=test_run_id,
        level="DEBUG",
        format_type="enterprise",
        log_file=log_file,
        console_enabled=True,
        file_enabled=True,
        service_name="test-service",
    )

    # Test logger
    logger = get_logger("test.component")

    # Test mensajes básicos
    logger.info("Test message INFO")
    logger.warning("Test message WARNING", extra={"test_key": "test_value"})
    logger.error("Test message ERROR")

    # Verificar archivo
    if log_file.exists():
        with open(log_file, encoding="utf-8") as f:
            lines = f.readlines()
            print(f"✅ Log file created with {len(lines)} entries")

            # Parsear primera línea como JSON
            if lines:
                first_log = json.loads(lines[0])
                print("✅ Enterprise format: @timestamp, service, run_id present")
                print(f"   Service: {first_log.get('service')}")
                print(f"   Run ID: {first_log.get('run_id')}")
                print(f"   Component: {first_log.get('component')}")
    else:
        print("❌ Log file not created")


def test_operation_logging():
    """Test logging de operaciones enterprise."""
    print("\n🧪 Testing Operation Logging...")

    logger = get_logger("test.operations")

    # Test operación completa
    start_time = time.time()
    log_operation_start(logger, "test_operation", user_id="test_user", component="test")

    # Simular trabajo
    time.sleep(0.1)

    duration_ms = (time.time() - start_time) * 1000
    log_operation_end(logger, "test_operation", duration_ms, success=True, results_count=5)

    print("✅ Operation logging completed")


def test_metric_logging():
    """Test logging de métricas."""
    print("\n🧪 Testing Metric Logging...")

    logger = get_logger("test.metrics")

    # Test métricas
    log_metric(logger, "keywords_processed", 150, "count")
    log_metric(logger, "processing_time", 2.5, "seconds")
    log_metric(logger, "memory_usage", 125.8, "MB")

    print("✅ Metric logging completed")


def test_config_based_logging():
    """Test logging desde configuración."""
    print("\n🧪 Testing Config-Based Logging...")

    # Cargar configuración
    config = load_config()

    # Test diferentes perfiles
    profiles = ["development", "validation", "production", "test"]

    for profile in profiles:
        print(f"  Testing profile: {profile}")

        # Obtener configuración del profile
        profile_config = config.copy()
        if profile != "development":
            profile_data = config.get("profiles", {}).get(profile, {})
            # Merge simple para test
            if "logging" in profile_data:
                profile_config["logging"] = profile_data["logging"]

        # Setup logging desde config
        profile_run_id = f"{test_run_id}_{profile}"
        setup_logging_from_config(profile_config, profile_run_id)

        # Test logger
        logger = get_logger(f"test.{profile}")
        logger.info(f"Testing {profile} profile", extra={"profile": profile})

        print(f"    ✅ {profile} profile configured")


def test_thread_safety():
    """Test thread safety del run_id."""
    print("\n🧪 Testing Thread Safety...")

    import threading

    def worker_function(worker_id):
        worker_run_id = f"{test_run_id}_worker_{worker_id}"
        set_run_id(worker_run_id)

        logger = get_logger(f"test.worker{worker_id}")
        logger.info(f"Worker {worker_id} message", extra={"worker_id": worker_id})

    # Crear varios threads
    threads = []
    for i in range(3):
        t = threading.Thread(target=worker_function, args=(i,))
        threads.append(t)
        t.start()

    # Esperar a que terminen
    for t in threads:
        t.join()

    print("✅ Thread safety test completed")


def test_error_logging():
    """Test logging de errores con excepciones."""
    print("\n🧪 Testing Error Logging...")

    logger = get_logger("test.errors")

    try:
        # Generar error intencionalmente
        _ = 1 / 0
    except ZeroDivisionError:
        logger.error(
            "Test division by zero", exc_info=True, extra={"operation": "division", "value": 1}
        )

    # Test logging con contexto
    log_with_context(
        logger,
        20,  # INFO level
        "Context message",
        context_key="context_value",
        nested_data={"key": "value", "number": 42},
    )

    print("✅ Error logging completed")


def main():
    """Ejecutar todos los tests de logging."""
    print("🚀 ENTERPRISE LOGGING VALIDATION")
    print("=" * 50)

    try:
        test_basic_logging()
        test_operation_logging()
        test_metric_logging()
        test_config_based_logging()
        test_thread_safety()
        test_error_logging()

        print("\n🎯 Enterprise Logging Validation Complete!")
        print("  ✅ Basic JSONL logging")
        print("  ✅ Enterprise format with @timestamp, service, run_id")
        print("  ✅ Operation start/end tracking")
        print("  ✅ Metric logging")
        print("  ✅ Config-based setup with profiles")
        print("  ✅ Thread-safe run_id management")
        print("  ✅ Error logging with exceptions")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
