#!/usr/bin/env python3
"""
Keyword Finder - Punto de entrada principal
Sistema automatizado de investigación de keywords
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))


def main():
    """Función principal del CLI"""
    print("🚀 Keyword Finder v1.0.0")
    print("Sistema automatizado de investigación de keywords")
    print("=" * 60)

    if len(sys.argv) < 2:
        print("Uso: python -m keyword_finder <comando>")
        print("\nComandos disponibles:")
        print("  demo          - Ejecutar demo rápida")
        print("  workflow      - Ejecutar workflow completo")
        print("  interactive   - Ejecutar modo interactivo")
        print("  test          - Ejecutar tests del sistema")
        return

    command = sys.argv[1]

    if command == "demo":
        from scripts.demo import main as demo_main

        asyncio.run(demo_main())
    elif command == "workflow":
        from src.keyword_finder.workflows.automated_workflow import run_automated_workflow

        # Keywords de ejemplo
        seeds = ["marketing digital", "agencia marketing", "seo"]
        asyncio.run(run_automated_workflow(seeds))
    elif command == "interactive":
        from src.keyword_finder.workflows.ejemplo_workflow import main as interactive_main

        asyncio.run(interactive_main())
    elif command == "test":
        from scripts.test_system import run_quick_test

        asyncio.run(run_quick_test())
    else:
        print(f"❌ Comando desconocido: {command}")
        print("Use: python -m keyword_finder --help para ver comandos disponibles")


if __name__ == "__main__":
    main()
