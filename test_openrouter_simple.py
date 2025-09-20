#!/usr/bin/env python3
"""
Prueba rápida de la integración con OpenRouter
"""

import requests


def test_openrouter_simple():
    """Prueba simple de conexión con OpenRouter"""

    api_key = "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"

    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://keyword-finder-pro.com",
        "X-Title": "Keyword Finder Pro"
    }

    data = {
        "model": "x-ai/grok-4-fast:free",
        "messages": [
            {
                "role": "user",
                "content": "Hola, ¿puedes confirmar que estás funcionando? Responde con una sola palabra: 'Sí'"
            }
        ],
        "max_tokens": 10
    }

    try:
        print("🔗 Conectando con OpenRouter...")
        response = requests.post(url, headers=headers, json=data, timeout=10)

        print(f"📊 Status Code: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            print(f"🤖 Respuesta de Grok: {content}")
            print("✅ ¡La integración con IA funciona perfectamente!")
            return True
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"📝 Detalles: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return False

if __name__ == "__main__":
    test_openrouter_simple()