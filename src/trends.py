import logging
import time

import pandas as pd
from pytrends.request import TrendReq


class TrendsAnalyzer:
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
        logging.info("TrendsAnalyzer initialized")

    def _init_pytrends(self) -> None:
        """Inicializa la conexión con PyTrends"""
        try:
            self.pytrends = TrendReq(hl=self.hl, tz=self.tz, timeout=20)
            logging.info("PyTrends connection established")
        except Exception as e:
            logging.error(f"Failed to initialize PyTrends: {e}")
            self.pytrends = None

    def get_trend_data(
        self, keywords: list[str], timeframe: str = "today 12-m", geo: str = "ES"
    ) -> dict[str, dict]:
        """
        Obtiene datos de trends para una lista de keywords

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

        results = {}

        # PyTrends tiene límite de 5 keywords por request
        batch_size = 5
        for i in range(0, len(keywords), batch_size):
            batch = keywords[i : i + batch_size]
            batch_results = self._process_keyword_batch(batch, timeframe, geo)
            results.update(batch_results)

            # Rate limiting entre batches
            if i + batch_size < len(keywords):
                time.sleep(2)

        return results

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

            # Obtener datos regionales si están disponibles
            try:
                regional_data = self.pytrends.interest_by_region()
            except Exception:
                regional_data = pd.DataFrame()

            # Obtener related queries
            try:
                related_queries = self.pytrends.related_queries()
            except Exception:
                related_queries = {}

            # Procesar resultados para cada keyword
            results = {}
            for keyword in keywords:
                results[keyword] = self._analyze_keyword_trends(
                    keyword, interest_over_time, regional_data, related_queries
                )

            logging.info(f"Processed trends for {len(keywords)} keywords")
            return results

        except Exception as e:
            logging.error(f"Error processing keyword batch {keywords}: {e}")
            # Retornar datos vacíos para cada keyword
            return {kw: self._empty_trend_data() for kw in keywords}

    def _analyze_keyword_trends(
        self,
        keyword: str,
        interest_data: pd.DataFrame,
        regional_data: pd.DataFrame,
        related_queries: dict,
    ) -> dict:
        """Analiza los datos de trends para una keyword específica"""
        try:
            trend_data = {
                "keyword": keyword,
                "trend_score": 0.0,
                "volume_estimate": 0,
                "growth_rate": 0.0,
                "seasonality": "stable",
                "regional_interest": {},
                "related_keywords": [],
            }

            # Analizar interés a lo largo del tiempo
            if not interest_data.empty and keyword in interest_data.columns:
                values = interest_data[keyword].dropna()

                if len(values) > 0:
                    # Calcular score de tendencia (0-100)
                    trend_data["trend_score"] = float(values.mean())

                    # Estimar volumen relativo
                    trend_data["volume_estimate"] = int(values.max())

                    # Calcular tasa de crecimiento
                    if len(values) >= 2:
                        recent_avg = values[-4:].mean() if len(values) >= 4 else values[-1]
                        older_avg = values[:4].mean() if len(values) >= 4 else values[0]

                        if older_avg > 0:
                            growth_rate = ((recent_avg - older_avg) / older_avg) * 100
                            trend_data["growth_rate"] = round(growth_rate, 2)

                    # Determinar estacionalidad
                    trend_data["seasonality"] = self._determine_seasonality(values)

            # Analizar datos regionales
            if not regional_data.empty and keyword in regional_data.columns:
                regional_interest = regional_data[keyword].dropna().to_dict()
                trend_data["regional_interest"] = {
                    k: v for k, v in regional_interest.items() if v > 0
                }

            # Extraer keywords relacionadas
            if keyword in related_queries:
                related = related_queries[keyword]
                if related and "top" in related and not related["top"].empty:
                    related_kws = related["top"]["query"].head(5).tolist()
                    trend_data["related_keywords"] = related_kws

            return trend_data

        except Exception as e:
            logging.error(f"Error analyzing trends for {keyword}: {e}")
            return self._empty_trend_data()

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
