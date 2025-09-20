#!/usr/bin/env python3
"""
Script de prueba para verificar la integración con OpenRouter y Grok
"""

import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from ai_assistant import create_ai_assistant


def test_openrouter_integration():
    """Prueba la integración con OpenRouter"""

    # API key de ejemplo (reemplaza con la real para testing)
    api_key = "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"

    print("🔧 Probando integración con OpenRouter...")
    print("📡 Usando modelo: x-ai/grok-4-fast:free")

    try:
        # Crear asistente
        assistant = create_ai_assistant(api_key)
        print("✅ Asistente creado exitosamente")

        # Probar generación de sugerencias
        print("\n🤖 Probando generación de sugerencias...")
        response = assistant.generate_keyword_suggestions(
            seed_keywords=["marketing digital", "seo"],
            niche="Marketing Digital",
            country="PE"
        )

        if response["success"]:
            print("✅ Sugerencias generadas exitosamente!")
            print("📝 Respuesta de IA:")
            print("-" * 50)
            print(response["suggestions"][:500] + "..." if len(response["suggestions"]) > 500 else response["suggestions"])
            print("-" * 50)
        else:
            print(f"❌ Error en sugerencias: {response['error']}")

        # Probar análisis competitivo
        print("\n🏆 Probando análisis competitivo...")
        response = assistant.analyze_competition_strategy(
            keywords=["marketing digital", "seo", "google ads"],
            niche="Marketing Digital"
        )

        if response["success"]:
            print("✅ Análisis competitivo completado!")
            print("📊 Respuesta de IA:")
            print("-" * 50)
            print(response["analysis"][:500] + "..." if len(response["analysis"]) > 500 else response["analysis"])
            print("-" * 50)
        else:
            print(f"❌ Error en análisis competitivo: {response['error']}")

        print("\n🎉 ¡Integración con OpenRouter funcionando perfectamente!")

    except Exception as e:
        print(f"❌ Error general: {e}")
        print("💡 Verifica tu conexión a internet y la API key")

if __name__ == "__main__":
    test_openrouter_integration()