import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
from pytrends.request import TrendReq


class GoogleTrendsAnalyzer:
    """Analizador de Google Trends para obtener datos de volumen y tendencias"""

    def __init__(self, hl: str = "es", tz: int = 360):
        """
        Inicializa el analizador de trends

        Args:
            hl: Idioma (por defecto español)
            tz: Timezone offset en minutos (360 = UTC-6)
        """
        self.hl = hl
        self.tz = tz
        self.pytrends = None
        self._init_pytrends()
        logging.info("GoogleTrendsAnalyzer initialized")

    def _init_pytrends(self) -> None:
        """Inicializa la conexión con PyTrends"""
        try:
            self.pytrends = TrendReq(hl=self.hl, tz=self.tz, timeout=10)  # Reducido de 20 a 10
            logging.info("PyTrends connection established")
        except Exception as e:
            logging.error(f"Failed to initialize PyTrends: {e}")
            self.pytrends = None

    async def get_trend_data_async(
        self, keywords: list[str], timeframe: str = "today 12-m", geo: str = "ES"
    ) -> dict[str, dict]:
        """
        Obtiene datos de trends para una lista de keywords usando procesamiento paralelo

        Args:
            keywords: Lista de keywords a analizar
            timeframe: Periodo de tiempo ('today 12-m', 'today 3-m', etc.)
            geo: Código de país ('ES', 'US', etc.)

        Returns:
            Dict con datos de cada keyword
        """
        if not self.pytrends:
            logging.error("PyTrends not initialized")
            return {}

        # PyTrends tiene límite de 5 keywords por request
        batch_size = 5
        batches = [keywords[i : i + batch_size] for i in range(0, len(keywords), batch_size)]

        # Procesar batches en paralelo con control de concurrencia
        semaphore = asyncio.Semaphore(2)  # Máximo 2 requests concurrentes
        results = {}

        async def process_batch_with_semaphore(batch: list[str]) -> dict[str, dict]:
            async with semaphore:
                return await self._process_keyword_batch_async(batch, timeframe, geo)

        # Crear tareas para todos los batches
        tasks = [process_batch_with_semaphore(batch) for batch in batches]

        # Ejecutar todas las tareas
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Procesar resultados
        for i, result in enumerate(batch_results):
            if isinstance(result, Exception):
                logging.error(f"Error processing batch {i}: {result}")
                # Retornar datos vacíos para este batch
                batch_keywords = batches[i]
                for kw in batch_keywords:
                    results[kw] = self._empty_trend_data()
            elif isinstance(result, dict):
                results.update(result)

        return results

    def get_trend_data(
        self, keywords: list[str], timeframe: str = "today 12-m", geo: str = "ES"
    ) -> dict[str, dict]:
        """
        Obtiene datos de trends para una lista de keywords (wrapper síncrono)

        Args:
            keywords: Lista de keywords a analizar
            timeframe: Periodo de tiempo ('today 12-m', 'today 3-m', etc.)
            geo: Código de país ('ES', 'US', etc.)

        Returns:
            Dict con datos de cada keyword
        """
        # Ejecutar la versión async en un event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Si ya hay un loop corriendo, usar ThreadPoolExecutor
                with ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run, self.get_trend_data_async(keywords, timeframe, geo)
                    )
                    return future.result()
            else:
                return loop.run_until_complete(self.get_trend_data_async(keywords, timeframe, geo))
        except RuntimeError:
            # No hay loop, crear uno nuevo
            return asyncio.run(self.get_trend_data_async(keywords, timeframe, geo))

    async def _process_keyword_batch_async(
        self, keywords: list[str], timeframe: str, geo: str
    ) -> dict[str, dict]:
        """Procesa un batch de keywords de manera asíncrona"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._process_keyword_batch, keywords, timeframe, geo
        )

    def _process_keyword_batch(
        self, keywords: list[str], timeframe: str, geo: str
    ) -> dict[str, dict]:
        """Procesa un batch de keywords"""
        if not self.pytrends:
            logging.error("PyTrends not initialized")
            return {kw: self._empty_trend_data() for kw in keywords}
        try:
            # Construir payload para PyTrends
            self.pytrends.build_payload(keywords, timeframe=timeframe, geo=geo)

            # Obtener datos de interés a lo largo del tiempo
            interest_over_time = self.pytrends.interest_over_time()

            # Procesar resultados para cada keyword de manera más eficiente
            results = {}
            for keyword in keywords:
                if keyword in interest_over_time.columns:
                    results[keyword] = self._analyze_keyword_trends_fast(
                        keyword, interest_over_time
                    )
                else:
                    results[keyword] = self._empty_trend_data()

            logging.info(f"Processed trends for {len(keywords)} keywords")
            return results

        except Exception as e:
            logging.error(f"Error processing keyword batch {keywords}: {e}")
            # Retornar datos vacíos para cada keyword
            return {kw: self._empty_trend_data() for kw in keywords}

    def _analyze_keyword_trends_fast(self, keyword: str, interest_data: pd.DataFrame) -> dict:
        """Analiza los datos de trends de manera optimizada para velocidad"""
        try:
            trend_data = {
                "keyword": keyword,
                "trend_score": 0.0,
                "volume_estimate": 0,
                "growth_rate": 0.0,
                "seasonality": "stable",
                "regional_interest": {},
                "related_keywords": [],
                "data_source": "trends",
                "data_quality": "high",
            }

            if keyword in interest_data.columns:
                values = interest_data[keyword].dropna()
                if len(values) > 0 and values.sum() > 0:
                    # Cálculos simplificados para velocidad
                    trend_data["trend_score"] = float(values.mean())
                    trend_data["volume_estimate"] = int(values.max() * 100)

                    # Growth rate simplificado
                    if len(values) >= 2:
                        try:
                            recent = values.iloc[-1] if len(values) >= 1 else values.mean()
                            older = values.iloc[0] if len(values) >= 1 else values.mean()
                            if older > 0:
                                growth_rate = ((recent - older) / older) * 100
                                trend_data["growth_rate"] = round(float(growth_rate), 2)
                        except (ZeroDivisionError, TypeError):
                            trend_data["growth_rate"] = 0.0

            return trend_data

        except Exception as e:
            logging.warning(f"Error in fast analysis for {keyword}: {e}")
            return self._empty_trend_data()

    def _analyze_keyword_trends(  # noqa: C901
        self,
        keyword: str,
        interest_data: pd.DataFrame,
        regional_data: pd.DataFrame,
        related_queries: dict,
    ) -> dict:
        """Analiza los datos de trends para una keyword específica con manejo robusto de errores"""
        try:
            trend_data = {
                "keyword": keyword,
                "trend_score": 0.0,
                "volume_estimate": 0,
                "growth_rate": 0.0,
                "seasonality": "stable",
                "regional_interest": {},
                "related_keywords": [],
                "data_source": "heurístico",  # default, will update below
                "data_quality": "low",  # will update based on real data availability
            }

            # Validación robusta para interest_data
            has_interest_data = (
                interest_data is not None
                and hasattr(interest_data, "empty")
                and hasattr(interest_data, "columns")
                and not interest_data.empty
                and keyword in interest_data.columns
            )

            if has_interest_data:
                try:
                    values = interest_data[keyword].dropna()
                    if len(values) > 0 and values.sum() > 0:  # Ensure we have meaningful data
                        trend_data["trend_score"] = float(values.mean())
                        trend_data["volume_estimate"] = int(
                            values.max() * 100
                        )  # Scale for better estimates

                        # Growth rate calculation with error handling
                        if len(values) >= 2:
                            try:
                                recent_avg = values[-4:].mean() if len(values) >= 4 else values[-1]
                                older_avg = values[:4].mean() if len(values) >= 4 else values[0]
                                if older_avg > 0:
                                    growth_rate = ((recent_avg - older_avg) / older_avg) * 100
                                    trend_data["growth_rate"] = round(float(growth_rate), 2)
                            except (ZeroDivisionError, TypeError) as e:
                                logging.warning(f"Error calculating growth rate for {keyword}: {e}")
                                trend_data["growth_rate"] = 0.0

                        trend_data["seasonality"] = self._determine_seasonality(values)
                        trend_data["data_source"] = "trends"
                        trend_data["data_quality"] = "high"

                except Exception as e:
                    logging.warning(f"Error processing interest data for {keyword}: {e}")
            else:
                logging.debug(f"No valid interest data for {keyword}")

            # Validación robusta para regional_data
            has_regional_data = (
                regional_data is not None
                and hasattr(regional_data, "empty")
                and hasattr(regional_data, "columns")
                and not regional_data.empty
                and keyword in regional_data.columns
            )

            if has_regional_data:
                try:
                    regional_series = regional_data[keyword].dropna()
                    if len(regional_series) > 0:
                        regional_interest = regional_series.to_dict()
                        trend_data["regional_interest"] = {
                            str(k): float(v) for k, v in regional_interest.items() if v > 0
                        }
                except Exception as e:
                    logging.warning(f"Error processing regional data for {keyword}: {e}")

            # Validación robusta para related_queries
            if isinstance(related_queries, dict) and keyword in related_queries:
                try:
                    related = related_queries[keyword]
                    if (
                        related
                        and isinstance(related, dict)
                        and "top" in related
                        and related["top"] is not None
                        and hasattr(related["top"], "empty")
                        and not related["top"].empty
                        and "query" in related["top"].columns
                    ):
                        related_kws = related["top"]["query"].head(5).tolist()
                        trend_data["related_keywords"] = [str(kw) for kw in related_kws if kw]
                except Exception as e:
                    logging.warning(f"Error processing related queries for {keyword}: {e}")

            return trend_data

        except Exception as e:
            logging.error(f"Error analyzing trends for {keyword}: {e}")
            # Return safe fallback data
            return {
                "keyword": keyword,
                "trend_score": 0.0,
                "volume_estimate": 0,
                "growth_rate": 0.0,
                "seasonality": "unknown",
                "regional_interest": {},
                "related_keywords": [],
                "data_source": "heurístico",
                "data_quality": "error",
            }

    def _determine_seasonality(self, values: pd.Series) -> str:
        """Determina el patrón de estacionalidad de una keyword"""
        try:
            if len(values) < 12:  # Necesitamos al menos 12 puntos
                return "insufficient_data"

            # Calcular variabilidad
            std_dev = values.std()
            mean_val = values.mean()

            if mean_val == 0:
                return "no_data"

            coefficient_variation = std_dev / mean_val

            # Clasificar basado en variabilidad
            if coefficient_variation < 0.2:
                return "stable"
            elif coefficient_variation < 0.5:
                return "moderate_seasonal"
            else:
                return "highly_seasonal"

        except Exception:
            return "unknown"

    def _empty_trend_data(self) -> dict:
        """Retorna estructura vacía de datos de trends"""
        return {
            "keyword": "",
            "trend_score": 0.0,
            "volume_estimate": 0,
            "growth_rate": 0.0,
            "seasonality": "no_data",
            "regional_interest": {},
            "related_keywords": [],
            "data_source": "heurístico",
            "data_quality": "no_data",
        }

    def get_trending_keywords(self, category: int = 0, geo: str = "ES") -> list[str]:
        """
        Obtiene keywords que están en tendencia actualmente

        Args:
            category: Categoría de Google Trends (0 = todas)
            geo: Código de país

        Returns:
            Lista de keywords trending
        """
        try:
            if not self.pytrends:
                return []

            # Obtener trending searches
            trending = self.pytrends.trending_searches(pn=geo)

            if not trending.empty:
                keywords = trending[0].head(20).tolist()
                logging.info(f"Found {len(keywords)} trending keywords")
                return keywords

        except Exception as e:
            logging.error(f"Error getting trending keywords: {e}")

        return []

    def compare_keywords(self, keywords: list[str], timeframe: str = "today 3-m") -> dict:
        """
        Compara múltiples keywords para ver cuál tiene mejor performance

        Args:
            keywords: Lista de keywords a comparar (máximo 5)
            timeframe: Periodo de comparación

        Returns:
            Dict con ranking y métricas comparativas
        """
        if len(keywords) > 5:
            keywords = keywords[:5]
            logging.warning("Limited comparison to first 5 keywords")

        try:
            if not self.pytrends:
                logging.error("PyTrends not initialized")
                return {}
            self.pytrends.build_payload(keywords, timeframe=timeframe)
            interest_data = self.pytrends.interest_over_time()

            if interest_data.empty:
                return {}

            # Calcular métricas para cada keyword
            comparison = {}
            for keyword in keywords:
                if keyword in interest_data.columns:
                    values = interest_data[keyword].dropna()
                    comparison[keyword] = {
                        "avg_interest": float(values.mean()) if len(values) > 0 else 0,
                        "max_interest": float(values.max()) if len(values) > 0 else 0,
                        "consistency": (
                            1 - (float(values.std()) / float(values.mean()))
                            if values.mean() > 0
                            else 0
                        ),
                    }

            # Ranking por interés promedio
            ranked = sorted(comparison.items(), key=lambda x: x[1]["avg_interest"], reverse=True)

            return {"ranking": [kw for kw, _ in ranked], "metrics": comparison}

        except Exception as e:
            logging.error(f"Error comparing keywords: {e}")
            return {}

    def get_keyword_suggestions(self, seed_keyword: str) -> list[str]:
        """
        Obtiene sugerencias de keywords relacionadas usando PyTrends

        Args:
            seed_keyword: Keyword base para generar sugerencias

        Returns:
            Lista de keywords sugeridas
        """
        try:
            if not self.pytrends:
                return []

            self.pytrends.build_payload([seed_keyword])

            # Obtener suggestions
            suggestions = self.pytrends.suggestions(keyword=seed_keyword)

            if suggestions:
                keywords = [s["title"] for s in suggestions if "title" in s]
                return keywords[:10]  # Limitar a 10 sugerencias

        except Exception as e:
            logging.error(f"Error getting suggestions for {seed_keyword}: {e}")

        return []
