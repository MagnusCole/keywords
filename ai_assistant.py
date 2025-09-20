"""
Módulo de Inteligencia Artificial para Keyword Finder Pro
Usa OpenRouter API con modelo Grok de xAI
"""

import requests
import streamlit as st


class KeywordAIAssistant:
    """Asistente de IA para análisis de keywords usando Grok"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://openrouter.ai/api/v1"
        self.model = "x-ai/grok-4-fast:free"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://keyword-finder-pro.com",
            "X-Title": "Keyword Finder Pro"
        }

    def generate_keyword_suggestions(self, seed_keywords: list[str], niche: str, country: str) -> dict:
        """Genera sugerencias de keywords relacionadas usando IA"""

        prompt = f"""
        Eres un experto en marketing digital y SEO. Analiza estas keywords semilla y genera sugerencias adicionales relevantes.

        Keywords semilla: {', '.join(seed_keywords)}
        Nicho: {niche}
        País: {country}

        Por favor proporciona:
        1. 10-15 keywords relacionadas adicionales
        2. Una breve explicación de por qué estas keywords son relevantes
        3. Sugerencias de estrategia de contenido para estas keywords

        Formato de respuesta:
        **Keywords Sugeridas:**
        - keyword1
        - keyword2
        ...

        **Explicación:**
        [Tu explicación aquí]

        **Estrategia de Contenido:**
        [Tus recomendaciones aquí]
        """

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "max_tokens": 1000,
                    "temperature": 0.7
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                return {
                    "success": True,
                    "suggestions": content,
                    "model": self.model
                }
            else:
                return {
                    "success": False,
                    "error": f"Error API: {response.status_code} - {response.text}",
                    "suggestions": ""
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"Error de conexión: {str(e)}",
                "suggestions": ""
            }

    def analyze_competition_strategy(self, keywords: list[str], niche: str) -> dict:
        """Analiza estrategias de competencia para las keywords"""

        prompt = f"""
        Analiza estas keywords desde una perspectiva de estrategia competitiva:

        Keywords: {', '.join(keywords)}
        Nicho: {niche}

        Proporciona:
        1. Nivel de competencia estimado para cada keyword
        2. Oportunidades de diferenciación
        3. Estrategias de posicionamiento recomendadas

        Formato:
        **Análisis de Competencia:**
        [Tu análisis aquí]

        **Oportunidades:**
        [Oportunidades identificadas]

        **Recomendaciones:**
        [Estrategias específicas]
        """

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "max_tokens": 800,
                    "temperature": 0.6
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                return {
                    "success": True,
                    "analysis": content,
                    "model": self.model
                }
            else:
                return {
                    "success": False,
                    "error": f"Error API: {response.status_code}",
                    "analysis": ""
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"Error de conexión: {str(e)}",
                "analysis": ""
            }

    def generate_content_ideas(self, keyword: str, niche: str) -> dict:
        """Genera ideas de contenido para una keyword específica"""

        prompt = f"""
        Genera ideas creativas de contenido para la keyword: "{keyword}"
        Nicho: {niche}

        Proporciona:
        1. 5 ideas de artículos/blog posts
        2. 3 ideas de videos
        3. 2 ideas de infografías o visuales
        4. Estrategias de promoción

        Formato creativo y actionable.
        """

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "max_tokens": 600,
                    "temperature": 0.8
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                return {
                    "success": True,
                    "ideas": content,
                    "keyword": keyword,
                    "model": self.model
                }
            else:
                return {
                    "success": False,
                    "error": f"Error API: {response.status_code}",
                    "ideas": ""
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"Error de conexión: {str(e)}",
                "ideas": ""
            }

# Función para crear instancia del asistente
def create_ai_assistant(api_key: str) -> KeywordAIAssistant:
    """Crea una instancia del asistente de IA"""
    return KeywordAIAssistant(api_key)

# Función de utilidad para Streamlit
def display_ai_response(response: dict, title: str):
    """Muestra la respuesta de IA en formato Streamlit"""
    if response["success"]:
        st.success(f"✅ {title}")
        st.markdown(response["suggestions"] or response["analysis"] or response["ideas"])
    else:
        st.error(f"❌ Error en {title}: {response['error']}")
        st.info("💡 Verifica tu conexión a internet y la API key")