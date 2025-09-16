import asyncio
import logging
import random
import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import quote_plus

import brotli
import httpx
from selectolax.parser import HTMLParser

from ..platform.rate_limiter import AdaptiveRateLimiter, RateLimitConfig, ThrottledSession


class GeoConfig:
    """Configuration for geo-targeting in different countries"""

    # Country configurations
    COUNTRIES = {
        "PE": {"name": "Peru", "hl": "es-PE", "gl": "PE", "lr": "lang_es"},
        "ES": {"name": "Spain", "hl": "es-ES", "gl": "ES", "lr": "lang_es"},
        "MX": {"name": "Mexico", "hl": "es-MX", "gl": "MX", "lr": "lang_es"},
        "AR": {"name": "Argentina", "hl": "es-AR", "gl": "AR", "lr": "lang_es"},
        "CO": {"name": "Colombia", "hl": "es-CO", "gl": "CO", "lr": "lang_es"},
        "CL": {"name": "Chile", "hl": "es-CL", "gl": "CL", "lr": "lang_es"},
        "US": {"name": "United States", "hl": "en-US", "gl": "US", "lr": "lang_en"},
        "GLOBAL": {"name": "Global", "hl": "es", "gl": "", "lr": "lang_es"},
    }

    def __init__(self, country_code: str = "PE"):
        self.country_code = country_code.upper()
        if self.country_code not in self.COUNTRIES:
            logging.warning(f"Country {country_code} not supported, defaulting to PE")
            self.country_code = "PE"

        self.config = self.COUNTRIES[self.country_code]
        logging.info(f"Geo-targeting configured for {self.config['name']} ({self.country_code})")

    @property
    def hl(self) -> str:
        """Host language parameter"""
        return self.config["hl"]

    @property
    def gl(self) -> str:
        """Geographic location parameter"""
        return self.config["gl"]

    @property
    def lr(self) -> str:
        """Language restrict parameter"""
        return self.config["lr"]

    def get_query_params(self) -> dict[str, str]:
        """Get all geo parameters as dict"""
        params = {"hl": self.hl, "lr": self.lr}
        if self.gl:  # Only add gl if not empty (for GLOBAL)
            params["gl"] = self.gl
        return params


class GoogleScraper:
    """Scraper para obtener keywords de Google Autocomplete y Related Searches"""

    def __init__(
        self,
        delay_range: tuple = (1, 3),
        max_retries: int = 3,
        geo_config: GeoConfig | None = None,
        rate_limit_config: RateLimitConfig | None = None,
    ):
        self.delay_range = delay_range
        self.max_retries = max_retries
        self.geo_config = geo_config or GeoConfig("PE")  # Default to Peru

        # Initialize rate limiter
        self.rate_limiter: AdaptiveRateLimiter | None
        if rate_limit_config:
            self.rate_limiter = AdaptiveRateLimiter(rate_limit_config)
            # Override delay_range with rate limiter config
            self.delay_range = rate_limit_config.get_delay_range()
            self.max_retries = rate_limit_config.retry_limit
            logging.info(
                f"Rate limiter enabled: {rate_limit_config.min_delay}-{rate_limit_config.max_delay}s delays, max {rate_limit_config.max_concurrent} concurrent"
            )
        else:
            self.rate_limiter = None
            logging.info("Rate limiter disabled, using basic delays")

        # User agents para rotar
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        ]

        # Configurar sesión HTTP
        timeout = rate_limit_config.request_timeout if rate_limit_config else 30.0
        max_connections = rate_limit_config.max_concurrent if rate_limit_config else 10

        self.session = httpx.AsyncClient(
            timeout=timeout,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=max_connections),
            follow_redirects=True,
            headers={"Accept-Encoding": "gzip, deflate, br"},  # Enable brotli
            http2=True,  # Enable HTTP/2 support
        )

        logging.info(f"GoogleScraper initialized for {self.geo_config.config['name']}")

    def _get_random_headers(self) -> dict[str, str]:
        """Genera headers aleatorios para evitar detección"""
        geo_params = self.geo_config.get_query_params()

        headers = {
            "User-Agent": random.choice(self.user_agents),  # noqa: S311
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": f"{geo_params['hl']},es;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",  # Enable brotli compression
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
        }

        # Add geo parameters to headers if available
        if self.geo_config.gl:
            headers["X-Geo-Location"] = self.geo_config.gl

        return headers

    async def _make_request(self, url: str) -> str:
        """Hace una request HTTP con reintentos y rate limiting avanzado"""
        for attempt in range(self.max_retries):
            try:
                if self.rate_limiter:
                    # Use advanced rate limiter
                    async with ThrottledSession(self.session, self.rate_limiter) as throttled:
                        headers = self._get_random_headers()
                        response = await throttled.get(url, headers=headers)
                        response.raise_for_status()
                else:
                    # Use basic rate limiting
                    await asyncio.sleep(random.uniform(*self.delay_range))  # noqa: S311
                    headers = self._get_random_headers()
                    response = await self.session.get(url, headers=headers)
                    response.raise_for_status()

                # Manejar decompresión (ahora httpx maneja brotli automáticamente)
                content = response.content
                encoding = response.headers.get("content-encoding", "").lower()

                # httpx should handle decompression automatically with http2=True
                # but keep fallback for edge cases
                if encoding == "br" and hasattr(brotli, "decompress"):
                    try:
                        content = brotli.decompress(content)
                    except Exception as e:
                        logging.warning(f"Manual brotli decompression failed: {e}")
                        # Let httpx handle it
                        pass

                # Decodificar texto
                text = str(content.decode("utf-8", errors="ignore"))

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
            # URL de Google Autocomplete API with geo-targeting
            encoded_query = quote_plus(query)
            geo_params = self.geo_config.get_query_params()

            # Build URL with geo parameters
            url = (
                f"http://suggestqueries.google.com/complete/search?client=chrome&q={encoded_query}"
            )
            for key, value in geo_params.items():
                if value:  # Only add non-empty values
                    url += f"&{key}={value}"

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

    async def get_related_searches(self, query: str, use_real_related: bool = True) -> list[str]:
        """Obtiene búsquedas relacionadas de Google SERP"""
        try:
            encoded_query = quote_plus(query)
            geo_params = self.geo_config.get_query_params()

            # Build URL with geo parameters
            url = f"https://www.google.com/search?q={encoded_query}"
            for key, value in geo_params.items():
                if value:  # Only add non-empty values
                    url += f"&{key}={value}"

            html = await self._make_request(url)
            if not html:
                return []

            parser = HTMLParser(html)
            related_searches = []

            if use_real_related:
                # Try to parse real "Related searches" section
                related_searches.extend(self._parse_real_related_searches(parser))

            # Fallback: extract variations from result titles (if real related searches fail)
            if len(related_searches) < 3:
                related_searches.extend(self._extract_title_variations(parser, query))

            # Always add common variations as backup
            base_variations = self._generate_base_variations(query)
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

    def _parse_real_related_searches(self, parser: HTMLParser) -> list[str]:
        """Parse real 'Related searches' section from Google SERP"""
        related_searches = []

        # Multiple selectors for "Related searches" (Google changes these frequently)
        related_selectors = [
            'div[data-sgrd="true"] a',  # Current format
            ".s75CSd a",  # Alternative format
            ".k8XOCe a",  # Another format
            "[data-sgrd] a",  # Generic data-sgrd
            ".related-question-pair a",  # Questions format
        ]

        for selector in related_selectors:
            elements = parser.css(selector)
            for element in elements:
                text = element.text(strip=True)
                if text and len(text) > 3 and len(text) < 100:
                    related_searches.append(text)

            if related_searches:  # Stop at first successful selector
                logging.info(
                    f"Found {len(related_searches)} real related searches using selector: {selector}"
                )
                break

        return related_searches

    def _extract_title_variations(self, parser: HTMLParser, query: str) -> list[str]:
        """Extract keyword variations from search result titles (fallback method)"""
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

        return related_searches

    def _generate_base_variations(self, query: str) -> list[str]:
        """Generate common variations as backup"""
        return [
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

    async def get_youtube_suggestions(self, query: str) -> list[str]:
        """Obtiene sugerencias de YouTube Autocomplete con geo-targeting"""
        try:
            encoded_query = quote_plus(query)
            geo_params = self.geo_config.get_query_params()

            # Build URL with geo parameters for YouTube
            url = f"https://suggestqueries.google.com/complete/search?client=chrome&ds=yt&q={encoded_query}"
            for key, value in geo_params.items():
                if value:  # Only add non-empty values
                    url += f"&{key}={value}"

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
        """Filtra y limpia lista de keywords con deduplicación avanzada"""
        if not keywords:
            return []

        # Primera pasada: limpieza básica
        cleaned = []
        basic_seen = set()

        for keyword in keywords:
            if not keyword:
                continue

            # Limpiar keyword
            clean_keyword = self._clean_keyword(keyword)

            # Validar keyword básica
            if self._is_valid_keyword(clean_keyword) and clean_keyword.lower() not in basic_seen:
                cleaned.append(clean_keyword)
                basic_seen.add(clean_keyword.lower())

        # Segunda pasada: deduplicación semántica fuzzy
        return self._fuzzy_dedup(cleaned)

    def _fuzzy_dedup(self, keywords: list[str], similarity_threshold: float = 0.85) -> list[str]:
        """Deduplicación fuzzy usando similaridad semántica"""
        if len(keywords) <= 1:
            return keywords

        unique_keywords: list[str] = []

        for keyword in keywords:
            normalized_keyword = self._normalize_for_dedup(keyword)
            is_duplicate = False

            # Comparar con keywords ya aceptadas
            for existing in unique_keywords:
                normalized_existing = self._normalize_for_dedup(existing)

                # Calcular similaridad usando SequenceMatcher
                similarity = SequenceMatcher(None, normalized_keyword, normalized_existing).ratio()

                if similarity >= similarity_threshold:
                    # Es muy similar, considerarlo duplicado
                    is_duplicate = True

                    # Elegir la keyword más "representativa" (más corta y común)
                    if len(keyword) < len(existing) and keyword.count(" ") <= existing.count(" "):
                        # Reemplazar la existente con la nueva (más corta)
                        idx = unique_keywords.index(existing)
                        unique_keywords[idx] = keyword

                    break

            if not is_duplicate:
                unique_keywords.append(keyword)

        logging.debug(f"Fuzzy dedup: {len(keywords)} -> {len(unique_keywords)} keywords")
        return unique_keywords

    def _advanced_similarity_check(self, kw1: str, kw2: str) -> float:
        """Verificación de similitud más avanzada"""
        # Normalizar ambas keywords
        norm1 = self._normalize_for_dedup(kw1)
        norm2 = self._normalize_for_dedup(kw2)

        # Si son idénticas tras normalización -> 100% similares
        if norm1 == norm2:
            return 1.0

        # Calcular similaridad de secuencia
        seq_similarity = SequenceMatcher(None, norm1, norm2).ratio()

        # Calcular similaridad de palabras (Jaccard)
        words1 = set(norm1.split())
        words2 = set(norm2.split())

        if not words1 and not words2:
            return 1.0

        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        jaccard_similarity = intersection / union if union > 0 else 0.0

        # Combinar ambas métricas (más peso a Jaccard para keywords)
        combined_similarity = (seq_similarity * 0.3) + (jaccard_similarity * 0.7)

        return combined_similarity

    def _clean_keyword(self, keyword: str) -> str:
        """Limpia una keyword individual con normalización avanzada"""
        if not keyword:
            return ""

        # Normalización Unicode NFKD (descomponer caracteres acentuados)
        normalized = unicodedata.normalize("NFKD", keyword)

        # Remover caracteres no deseados pero mantener acentos
        keyword = re.sub(r"[^\w\s\-áéíóúñüÁÉÍÓÚÑÜ]", "", normalized, flags=re.IGNORECASE)

        # Filtrar años si no son útiles (opcional)
        keyword = re.sub(r"\b20\d{2}\b", "", keyword)

        # Colapsar espacios y guiones múltiples
        keyword = re.sub(r"\s+", " ", keyword)  # Múltiples espacios -> uno
        keyword = re.sub(r"-+", "-", keyword)  # Múltiples guiones -> uno
        keyword = re.sub(r"\s*-\s*", " ", keyword)  # Espacios alrededor de guiones

        # Remover espacios al inicio/final
        keyword = keyword.strip()

        # Convertir a lowercase para consistencia
        return keyword.lower()

    def _normalize_for_dedup(self, keyword: str) -> str:
        """Normalización especial para detección de duplicados"""
        if not keyword:
            return ""

        # Aplicar limpieza básica
        normalized = self._clean_keyword(keyword)

        # Remover acentos para comparación
        no_accents = unicodedata.normalize("NFKD", normalized)
        no_accents = "".join(c for c in no_accents if not unicodedata.combining(c))

        # Remover plurales simples (muy básico)
        no_accents = re.sub(r"\bs$", "", no_accents)  # Plurales en 's'
        no_accents = re.sub(r"\bes$", "", no_accents)  # Plurales en 'es'

        # Remover palabras muy comunes que no aportan
        stop_words = ["de", "la", "el", "en", "y", "a", "para", "con", "del", "las", "los"]
        words = no_accents.split()
        filtered_words = [w for w in words if w not in stop_words]

        return " ".join(filtered_words).strip()

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

    async def expand_keywords(  # noqa: C901
        self,
        seed_keywords: list[str],
        max_concurrent: int = 3,
        include_alphabet_soup: bool = False,
        soup_chars: str | None = None,
    ) -> dict[str, list[str]]:
        """Expande una lista de keywords semilla usando autocomplete y related searches con paralelismo optimizado"""
        results = {}
        # Semaphore para limitar requests concurrentes
        request_semaphore = asyncio.Semaphore(max_concurrent)

        for seed in seed_keywords:
            logging.info(f"Expanding keyword: {seed}")
            # Variaciones optimizadas basadas en análisis de datos reales
            variations = list(
                {
                    seed,  # Original
                    f"curso {seed}",  # ✅ EXCELENTE (generó 45 keywords en test)
                    f"{seed} curso",  # ✅ BUENO
                    f"como hacer {seed}",  # ✅ EXCELENTE (scores altos: 51.17)
                    f"que es {seed}",  # ✅ EXCELENTE (scores altos: 50.89)
                    f"mejor {seed}",  # 🆕 Intent comercial
                    f"{seed} precio",  # 🆕 Intent transaccional
                    f"{seed} 2025",  # 🆕 Términos actuales
                    f"{seed} peru",  # 🆕 Geo-targeting (detectado en datos)
                    f"{seed} lima",  # 🆕 Geo-targeting específico
                    f"guia {seed}",  # 🆕 Content marketing
                    f"{seed} profesional",  # 🆕 Calidad/premium
                    f"herramientas {seed}",  # ✅ Mantener (efectivo)
                    f"{seed} online",  # ✅ Mantener (popular)
                    f"{seed} gratis",  # ⚠️ Mantener pero con menor prioridad
                }
            )

            # Alphabet soup (opcional): agrega sufijos "a-z" y "0-9" para ampliar sugerencias
            if include_alphabet_soup:
                chars = soup_chars or "abcdefghijklmnopqrstuvwxyz0123456789"
                addl = [f"{seed} {ch}" for ch in chars]
                # Limitar para evitar explosión
                variations.extend(addl[: max(0, 36)])

            # Crear tasks para autocomplete suggestions (parallelized)
            autocomplete_tasks = [
                self._get_autocomplete_with_semaphore(v, request_semaphore) for v in variations
            ]

            # Crear tasks para YouTube suggestions (limited to avoid rate limits)
            youtube_tasks = [
                self._get_youtube_with_semaphore(v, request_semaphore)
                for v in variations[:5]  # Limitar para evitar rate limits
            ]

            # Task para related searches
            related_task = self._get_related_with_semaphore(seed, request_semaphore)

            # Ejecutar todas las tasks en paralelo
            try:
                # Gather all autocomplete results
                autocomplete_results = await asyncio.gather(
                    *autocomplete_tasks, return_exceptions=True
                )

                # Gather YouTube results
                youtube_results = await asyncio.gather(*youtube_tasks, return_exceptions=True)

                # Get related searches
                related_results = await related_task

                # Flatten and combine results
                all_keywords = []

                # Process autocomplete results
                for result in autocomplete_results:
                    if isinstance(result, list):
                        all_keywords.extend(result)
                    elif isinstance(result, Exception):
                        logging.warning(f"Autocomplete task failed: {result}")

                # Process YouTube results
                for result in youtube_results:
                    if isinstance(result, list):
                        all_keywords.extend(result)
                    elif isinstance(result, Exception):
                        logging.warning(f"YouTube task failed: {result}")

                # Add related searches
                if isinstance(related_results, list):
                    all_keywords.extend(related_results)

                # Remove duplicates and store
                unique_keywords = list(set(all_keywords))
                results[seed] = unique_keywords

                logging.info(
                    f"Expanded '{seed}' into {len(unique_keywords)} keywords using parallel processing"
                )

            except Exception as e:
                logging.error(f"Error in parallel expansion for '{seed}': {e}")
                # Fallback to sequential processing
                results[seed] = await self._expand_keywords_sequential(seed, variations)

        return results

    async def _get_autocomplete_with_semaphore(
        self, variation: str, semaphore: asyncio.Semaphore
    ) -> list[str]:
        """Get autocomplete suggestions with semaphore rate limiting"""
        async with semaphore:
            try:
                return await self.get_autocomplete_suggestions(variation)
            except Exception as e:
                logging.warning(f"Failed to get autocomplete for '{variation}': {e}")
                return []

    async def _get_youtube_with_semaphore(
        self, variation: str, semaphore: asyncio.Semaphore
    ) -> list[str]:
        """Get YouTube suggestions with semaphore rate limiting"""
        async with semaphore:
            try:
                return await self.get_youtube_suggestions(variation)
            except Exception as e:
                logging.warning(f"Failed to get YouTube suggestions for '{variation}': {e}")
                return []

    async def _get_related_with_semaphore(
        self, seed: str, semaphore: asyncio.Semaphore
    ) -> list[str]:
        """Get related searches with semaphore rate limiting"""
        async with semaphore:
            try:
                return await self.get_related_searches(seed)
            except Exception as e:
                logging.warning(f"Failed to get related searches for '{seed}': {e}")
                return []

    async def _expand_keywords_sequential(self, seed: str, variations: list[str]) -> list[str]:
        """Fallback sequential expansion when parallel fails"""
        logging.info(f"Using sequential fallback for '{seed}'")

        all_keywords = []

        # Obtener autocomplete
        for v in variations:
            ac = await self.get_autocomplete_suggestions(v)
            all_keywords.extend(ac)

        # YouTube suggestions (limited)
        for v in variations[:5]:
            yt = await self.get_youtube_suggestions(v)
            all_keywords.extend(yt)

        # Related searches
        related = await self.get_related_searches(seed)
        all_keywords.extend(related)

        return list(set(all_keywords))

    async def close(self):
        """Cierra la sesión HTTP"""
        await self.session.aclose()

        # Log rate limiter stats if available
        if self.rate_limiter:
            stats = self.rate_limiter.get_stats()
            logging.info(f"Rate limiter stats: {stats}")

        logging.info("GoogleScraper session closed")

    def get_rate_limiter_stats(self) -> dict[str, Any] | None:
        """Get rate limiter statistics if available"""
        if self.rate_limiter:
            return self.rate_limiter.get_stats()
        return None


# Factory functions for easy initialization
def create_scraper(
    country: str = "PE", max_concurrent: int = 3, rate_limit_config: RateLimitConfig | None = None
) -> GoogleScraper:
    """Factory function to create GoogleScraper with geo-targeting and rate limiting

    Args:
        country: Country code (PE, ES, MX, AR, CO, CL, US, GLOBAL)
        max_concurrent: Maximum concurrent requests (overridden by rate_limit_config if provided)
        rate_limit_config: Rate limiting configuration

    Returns:
        Configured GoogleScraper instance
    """
    geo_config = GeoConfig(country)

    # If no rate limit config provided, create a basic one with the max_concurrent parameter
    if rate_limit_config is None and max_concurrent != 3:
        rate_limit_config = RateLimitConfig(max_concurrent=max_concurrent)

    return GoogleScraper(geo_config=geo_config, rate_limit_config=rate_limit_config)


def create_validation_scraper(
    validation_config: dict[str, Any], country: str = "PE"
) -> GoogleScraper:
    """Create a scraper configured for validation with minimal API usage.

    Args:
        validation_config: Configuration from validation.yaml
        country: Country code for geo-targeting

    Returns:
        GoogleScraper configured for validation
    """
    from ..platform.rate_limiter import create_rate_limited_scraper_config

    geo_config = GeoConfig(country)
    rate_config = create_rate_limited_scraper_config(validation_config)

    logging.info(
        f"Creating validation scraper with minimal config: {rate_config.min_delay}-{rate_config.max_delay}s delays"
    )

    return GoogleScraper(geo_config=geo_config, rate_limit_config=rate_config)


class CompetitorScraper:
    """Scraper para analizar títulos y meta tags de competidores"""

    def __init__(
        self, session: httpx.AsyncClient | None = None, scraper: GoogleScraper | None = None
    ):
        self.session = session or httpx.AsyncClient(timeout=20.0)
        self.scraper = scraper  # Reuse shared scraper to avoid memory leaks
        self._owns_scraper = scraper is None

    async def get_competitor_keywords(self, domain: str, max_pages: int = 5) -> list[str]:
        """Extrae keywords de títulos y meta descriptions de un dominio"""
        scraper = None
        try:
            # Buscar páginas del dominio en Google
            query = f"site:{domain}"
            url = f"https://www.google.com/search?q={quote_plus(query)}&num={max_pages}"

            # Use shared scraper or create temporary one
            if self.scraper:
                scraper = self.scraper
                html = await scraper._make_request(url)
            else:
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
        finally:
            # Close scraper if we created it temporarily
            if scraper and self._owns_scraper and scraper != self.scraper:
                await scraper.close()

    async def close(self):
        """Close shared resources"""
        if self.scraper and self._owns_scraper:
            await self.scraper.close()
        if hasattr(self, "session") and self.session:
            await self.session.aclose()


def create_competitor_scraper(shared_scraper: GoogleScraper | None = None):
    """Factory function to create CompetitorScraper

    Args:
        shared_scraper: Optional shared GoogleScraper to avoid memory leaks

    Returns:
        Configured CompetitorScraper instance
    """
    return CompetitorScraper(scraper=shared_scraper)
