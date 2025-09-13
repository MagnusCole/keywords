import asyncio
import logging
import random
import re
from urllib.parse import quote_plus

import brotli
import httpx
from selectolax.parser import HTMLParser


class GoogleScraper:
    """Scraper para obtener keywords de Google Autocomplete y Related Searches"""

    def __init__(self, delay_range: tuple = (1, 3), max_retries: int = 3):
        self.delay_range = delay_range
        self.max_retries = max_retries

        # User agents para rotar
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        ]

        # Configurar sesión HTTP
        self.session = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            follow_redirects=True,
            headers={"Accept-Encoding": "gzip, deflate"},  # Evitar brotli compression
        )

        logging.info("GoogleScraper initialized")

    def _get_random_headers(self) -> dict[str, str]:
        """Genera headers aleatorios para evitar detección"""
        return {
            "User-Agent": random.choice(self.user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",  # Solo gzip y deflate, sin brotli
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
        }

    async def _make_request(self, url: str) -> str:
        """Hace una request HTTP con reintentos y rate limiting"""
        for attempt in range(self.max_retries):
            try:
                # Rate limiting
                await asyncio.sleep(random.uniform(*self.delay_range))

                headers = self._get_random_headers()
                response = await self.session.get(url, headers=headers)
                response.raise_for_status()

                # Manejar decompresión manual si es necesario
                content = response.content
                encoding = response.headers.get("content-encoding", "").lower()

                if encoding == "br":
                    try:
                        content = brotli.decompress(content)
                    except Exception as e:
                        logging.warning(f"Failed to decompress brotli content: {e}")
                        # Intentar usar el contenido sin descomprimir
                        pass

                # Decodificar texto
                text = content.decode("utf-8", errors="ignore")

                logging.debug(f"Request successful to {url}")
                return text

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:  # Rate limited
                    wait_time = 2**attempt
                    logging.warning(
                        f"Rate limited, waiting {wait_time}s before retry {attempt + 1}"
                    )
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    logging.error(f"HTTP error {e.response.status_code} for {url}")

            except Exception as e:
                logging.error(f"Request failed for {url}: {e}")

            if attempt < self.max_retries - 1:
                await asyncio.sleep(2**attempt)

        logging.error(f"All retries failed for {url}")
        return ""

    async def get_autocomplete_suggestions(self, query: str) -> list[str]:
        """Obtiene sugerencias de Google Autocomplete"""
        try:
            # URL de Google Autocomplete API
            encoded_query = quote_plus(query)
            url = f"http://suggestqueries.google.com/complete/search?client=chrome&q={encoded_query}&hl=es"

            response_text = await self._make_request(url)
            if not response_text:
                return []

            # Parsear respuesta JSON del autocomplete
            import json

            try:
                logging.debug(f"Autocomplete response for {query}: {response_text[:200]}...")
                data = json.loads(response_text)
                if len(data) >= 2 and isinstance(data[1], list):
                    suggestions = data[1]
                    # Filtrar y limpiar sugerencias
                    filtered = self._filter_keywords(suggestions)
                    logging.info(f"Got {len(filtered)} autocomplete suggestions for '{query}'")
                    return filtered
                else:
                    logging.warning(f"Unexpected autocomplete format for {query}: {data}")
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse autocomplete JSON for {query}: {e}")
                logging.debug(f"Raw response: {response_text[:500]}")

        except Exception as e:
            logging.error(f"Error getting autocomplete for {query}: {e}")

        return []

    async def get_related_searches(self, query: str) -> list[str]:
        """Obtiene búsquedas relacionadas de Google SERP"""
        try:
            encoded_query = quote_plus(query)
            url = f"https://www.google.com/search?q={encoded_query}&hl=es&gl=es"

            html = await self._make_request(url)
            if not html:
                return []

            parser = HTMLParser(html)
            related_searches = []

            # Buscar en títulos de resultados que contengan el query
            result_titles = parser.css("h3 a, .g h3, [data-ved] h3, .LC20lb")
            for title in result_titles:
                text = title.text(strip=True)
                if text and len(text) > 3 and query.lower() in text.lower():
                    # Extraer variaciones del keyword base
                    words = text.split()
                    for i, word in enumerate(words):
                        if word.lower() == query.lower():
                            # Agregar palabra siguiente
                            if i < len(words) - 1:
                                next_word = words[i + 1]
                                combined = f"{query} {next_word}"
                                if len(combined) < 50:
                                    related_searches.append(combined)
                            # Agregar palabra anterior
                            if i > 0:
                                prev_word = words[i - 1]
                                combined = f"{prev_word} {query}"
                                if len(combined) < 50:
                                    related_searches.append(combined)

            # Buscar variaciones comunes agregando prefijos/sufijos
            base_variations = [
                f"curso {query}",
                f"{query} online",
                f"{query} gratis",
                f"{query} digital",
                f"que es {query}",
                f"{query} curso",
                f"como hacer {query}",
                f"{query} profesional",
                f"herramientas {query}",
                f"{query} estrategia",
            ]

            related_searches.extend(base_variations)

            # Filtrar y limpiar
            filtered = self._filter_keywords(related_searches)
            # Limitar a las mejores sugerencias
            filtered = list(set(filtered))[:8]

            logging.info(f"Got {len(filtered)} related searches for '{query}'")
            return filtered

        except Exception as e:
            logging.error(f"Error getting related searches for {query}: {e}")
            return []

    async def get_youtube_suggestions(self, query: str) -> list[str]:
        """Obtiene sugerencias de YouTube Autocomplete (client=chrome, hl=es).

        Usa el endpoint de suggestqueries para YouTube y devuelve una lista filtrada.
        """
        try:
            encoded_query = quote_plus(query)
            url = f"https://suggestqueries.google.com/complete/search?client=chrome&ds=yt&q={encoded_query}&hl=es"
            response_text = await self._make_request(url)
            if not response_text:
                return []
            import json

            data = json.loads(response_text)
            if len(data) >= 2 and isinstance(data[1], list):
                suggestions = data[1]
                filtered = self._filter_keywords(suggestions)
                return filtered
        except Exception as e:
            logging.error(f"Error getting YouTube suggestions for {query}: {e}")
        return []

    def _filter_keywords(self, keywords: list[str]) -> list[str]:
        """Filtra y limpia lista de keywords"""
        filtered = []
        seen = set()

        for keyword in keywords:
            if not keyword:
                continue

            # Limpiar keyword
            clean_keyword = self._clean_keyword(keyword)

            # Validar keyword
            if self._is_valid_keyword(clean_keyword) and clean_keyword.lower() not in seen:
                filtered.append(clean_keyword)
                seen.add(clean_keyword.lower())

        return filtered

    def _clean_keyword(self, keyword: str) -> str:
        """Limpia una keyword individual"""
        # Remover caracteres no deseados
        keyword = re.sub(r"[^\w\s\-áéíóúñü]", "", keyword, flags=re.IGNORECASE)

        # Normalizar espacios
        keyword = " ".join(keyword.split())

        # Capitalizar apropiadamente
        return keyword.strip().lower()

    def _is_valid_keyword(self, keyword: str) -> bool:
        """Valida si una keyword es útil"""
        if not keyword or len(keyword) < 3:
            return False

        # Rechazar keywords que son solo números
        if keyword.isdigit():
            return False

        # Rechazar keywords muy cortas o muy largas
        if len(keyword) < 3 or len(keyword) > 100:
            return False

        # Rechazar keywords con caracteres sospechosos
        if any(char in keyword for char in ["http", "www", ".com", "@"]):
            return False

        return True

    async def expand_keywords(self, seed_keywords: list[str]) -> dict[str, list[str]]:
        """Expande una lista de keywords semilla usando autocomplete y related searches"""
        results = {}

        for seed in seed_keywords:
            logging.info(f"Expanding keyword: {seed}")
            # Variaciones base para ampliar el abanico
            variations = list(
                {
                    seed,
                    f"curso {seed}",
                    f"{seed} curso",
                    f"{seed} online",
                    f"{seed} gratis",
                    f"herramientas {seed}",
                    f"{seed} para pymes",
                    f"como hacer {seed}",
                    f"que es {seed}",
                }
            )

            # Obtener autocomplete
            autocomplete: list[str] = []
            for v in variations:
                ac = await self.get_autocomplete_suggestions(v)
                autocomplete.extend(ac)

            # YouTube suggestions
            youtube: list[str] = []
            for v in variations[:5]:  # limitar para no exceder rate limit
                yt = await self.get_youtube_suggestions(v)
                youtube.extend(yt)

            # Obtener related searches
            related = await self.get_related_searches(seed)

            # Combinar resultados
            all_keywords = list(set(autocomplete + related + youtube))
            results[seed] = all_keywords

            logging.info(f"Expanded '{seed}' into {len(all_keywords)} keywords")

        return results

    async def close(self):
        """Cierra la sesión HTTP"""
        await self.session.aclose()
        logging.info("GoogleScraper session closed")


class CompetitorScraper:
    """Scraper para analizar títulos y meta tags de competidores"""

    def __init__(self, session: httpx.AsyncClient | None = None):
        self.session = session or httpx.AsyncClient(timeout=20.0)

    async def get_competitor_keywords(self, domain: str, max_pages: int = 5) -> list[str]:
        """Extrae keywords de títulos y meta descriptions de un dominio"""
        try:
            # Buscar páginas del dominio en Google
            query = f"site:{domain}"
            url = f"https://www.google.com/search?q={quote_plus(query)}&num={max_pages}"

            scraper = GoogleScraper()
            html = await scraper._make_request(url)

            if not html:
                return []

            parser = HTMLParser(html)
            keywords = []

            # Extraer títulos de resultados
            title_elements = parser.css("h3, .LC20lb")
            for element in title_elements:
                title = element.text(strip=True)
                if title:
                    words = re.findall(r"\b\w+\b", title.lower())
                    keywords.extend(words)

            # Filtrar keywords relevantes
            filtered_keywords = []
            for keyword in keywords:
                if len(keyword) > 2 and keyword.isalpha():
                    filtered_keywords.append(keyword)

            # Remover duplicados
            unique_keywords = list(set(filtered_keywords))
            logging.info(f"Extracted {len(unique_keywords)} keywords from {domain}")

            return unique_keywords

        except Exception as e:
            logging.error(f"Error scraping competitor {domain}: {e}")
            return []
