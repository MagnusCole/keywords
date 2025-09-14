import logging
import math
import re
import statistics
from datetime import datetime


# Legacy compatibility: alias para el scorer básico
class BasicKeywordScorer:
    """Scoring básico de keywords basado en trend y datos base (legacy)"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def calculate_score(self, keywords_data: list[dict]) -> list[dict]:
        """Calcula score básico para keywords"""
        try:
            for keyword_data in keywords_data:
                # Score básico basado solo en trend_score
                trend = keyword_data.get("trend_score", 50)
                volume = keyword_data.get("volume", 0)
                competition = keyword_data.get("competition", 0.5)

                # Fórmula simple
                base_score = trend * 0.6 + (volume / 1000) * 0.3 + (1 - competition) * 0.1
                keyword_data["score"] = min(100, max(0, base_score))

            # Ordenar por score
            return sorted(keywords_data, key=lambda x: x.get("score", 0), reverse=True)

        except Exception as e:
            self.logger.error(f"Error calculating basic scores: {e}")
            return keywords_data


# Alias para compatibilidad con código existente
def create_basic_scorer():
    """Factory para crear scorer básico (legacy compatibility)"""
    return BasicKeywordScorer()


class AdvancedKeywordScorer:
    """Sistema de scoring avanzado con diseño por capas y percentile ranking"""

    def __init__(self, target_geo: str = "PE", target_intent: str = "transactional"):
        """
        Inicializa el scorer avanzado

        Args:
            target_geo: País objetivo (PE, ES, MX, etc.)
            target_intent: Intención objetivo (transactional, commercial, informational)
        """
        self.target_geo = target_geo.lower()
        self.target_intent = target_intent.lower()

        # Intent weights basados en valor de conversión
        self.intent_weights = {
            "transactional": 1.0,  # Lo que realmente convierte
            "commercial": 0.7,  # Medio-alto valor
            "informational": 0.4,  # Bajo valor para servicios
        }

        # Geo terms por país
        self.geo_terms = {
            "pe": ["lima", "perú", "peru", "arequipa", "trujillo", "cusco"],
            "es": ["madrid", "barcelona", "valencia", "sevilla", "españa"],
            "mx": ["mexico", "méxico", "cdmx", "guadalajara", "monterrey"],
            "ar": ["argentina", "buenos aires", "córdoba", "rosario"],
            "co": ["colombia", "bogotá", "medellín", "cali"],
            "cl": ["chile", "santiago", "valparaíso", "concepción"],
        }

        # Pesos del ensamble (suman 1.0)
        self.weights = {
            "trend": 0.28,
            "volume": 0.22,
            "serp_opportunity": 0.15,
            "cluster_centrality": 0.12,
            "intent": 0.10,
            "geo": 0.08,
            "freshness": 0.05,
        }

        logging.info(
            f"AdvancedKeywordScorer initialized for {target_geo} targeting {target_intent} intent"
        )

    def calculate_advanced_score(self, keywords_batch: list[dict]) -> list[dict]:
        """
        Calcula scores avanzados usando percentile ranking para un lote de keywords

        Args:
            keywords_batch: Lista de keywords con datos base

        Returns:
            Keywords con scores avanzados calculados
        """
        if not keywords_batch:
            return []

        # 1. Calcular señales base y nuevas para todo el lote
        enriched_keywords = []

        for kw_data in keywords_batch:
            enriched = self._calculate_signals(kw_data)
            enriched_keywords.append(enriched)

        # 2. Calcular percentiles para normalización
        signal_percentiles = self._calculate_percentiles(enriched_keywords)

        # 3. Calcular scores finales usando percentiles
        for kw_data in enriched_keywords:
            kw_data["advanced_score"] = self._calculate_final_score(kw_data, signal_percentiles)

        # 4. Aplicar guardrails y polish
        polished_keywords = self._apply_guardrails(enriched_keywords)

        # 5. Ordenar por score final
        polished_keywords.sort(key=lambda x: x.get("advanced_score", 0), reverse=True)

        logging.info(f"Calculated advanced scores for {len(polished_keywords)} keywords")
        return polished_keywords

    def _calculate_signals(self, kw_data: dict) -> dict:
        """Calcula todas las señales (base + nuevas) para una keyword"""
        keyword = kw_data.get("keyword", "")
        enriched = kw_data.copy()

        # Señales base (ya existentes)
        enriched["trend_norm"] = self._normalize_trend(kw_data.get("trend_score", 0))
        enriched["volume_norm"] = self._normalize_volume_log(kw_data.get("volume", 0))
        enriched["competition_norm"] = 1.0 - min(1.0, kw_data.get("competition", 0.5))

        # Señales nuevas
        enriched["intent_weight"] = self._calculate_intent_weight(keyword)
        enriched["geo_weight"] = self._calculate_geo_weight(keyword)
        enriched["serp_difficulty"] = self._estimate_serp_difficulty(keyword)
        enriched["cluster_centrality"] = self._estimate_cluster_centrality(keyword, kw_data)
        enriched["freshness_boost"] = self._calculate_freshness_boost(keyword)

        return enriched

    def _normalize_trend(self, trend_score: float) -> float:
        """Normaliza trend score a 0-1"""
        return max(0, min(100, trend_score)) / 100.0

    def _normalize_volume_log(self, volume: int) -> float:
        """Normaliza volumen usando escala logarítmica mejorada"""
        if volume <= 0:
            return 0.0

        # Usar log para manejar rangos amplios
        log_volume = math.log10(max(1, volume))
        log_max = math.log10(100000)  # 100k como máximo razonable

        return min(1.0, log_volume / log_max)

    def _calculate_intent_weight(self, keyword: str) -> float:
        """Calcula peso por intención de búsqueda"""
        if not keyword:
            return 0.4  # Default informational

        keyword_lower = keyword.lower()

        # Transactional patterns (valor alto)
        transactional_patterns = [
            r"\b(agencia|empresa|consultor|servicio)\b",
            r"\b(contratar|comprar|solicitar)\b",
            r"\b(lima|perú|madrid)\b.*\b(marketing|seo|publicidad)\b",
            r"\bpara (pymes|empresas|negocios)\b",
        ]

        # Commercial patterns (valor medio)
        commercial_patterns = [
            r"\b(precio|costo|mejor|top|comparar)\b",
            r"\b(curso|clase|diplomado|certificado)\b",
            r"\b(herramientas|software|plataforma)\b",
            r"\b(gratis|barato|oferta)\b",
        ]

        # Check patterns
        for pattern in transactional_patterns:
            if re.search(pattern, keyword_lower):
                return self.intent_weights["transactional"]

        for pattern in commercial_patterns:
            if re.search(pattern, keyword_lower):
                return self.intent_weights["commercial"]

        return self.intent_weights["informational"]

    def _calculate_geo_weight(self, keyword: str) -> float:
        """Calcula peso geográfico basado en términos locales"""
        if not keyword:
            return 0.6

        keyword_lower = keyword.lower()
        target_terms = self.geo_terms.get(self.target_geo, [])

        # Buscar términos geográficos del país objetivo
        for term in target_terms:
            if term in keyword_lower:
                return 1.0  # Boost completo para geo-targeting

        return 0.6  # Peso reducido sin geo-targeting

    def _estimate_serp_difficulty(self, keyword: str) -> float:
        """Estima dificultad SERP de manera rápida y barata"""
        if not keyword:
            return 0.5

        keyword_lower = keyword.lower()
        word_count = len(keyword_lower.split())

        # Base difficulty por longitud (más palabras = más fácil)
        if word_count == 1:
            base_difficulty = 0.9  # Muy difícil
        elif word_count == 2:
            base_difficulty = 0.7  # Difícil
        elif word_count <= 4:
            base_difficulty = 0.5  # Medio
        else:
            base_difficulty = 0.3  # Más fácil

        # Ajustes por patrones conocidos
        # Marcas fuertes aumentan dificultad
        strong_brands = ["google", "facebook", "amazon", "microsoft", "adobe", "hubspot"]
        if any(brand in keyword_lower for brand in strong_brands):
            base_difficulty += 0.1

        # Keywords comerciales aumentan dificultad
        commercial_terms = ["curso", "precio", "mejor", "top", "gratis"]
        commercial_count = sum(1 for term in commercial_terms if term in keyword_lower)
        base_difficulty += commercial_count * 0.05

        # Geo-targeting reduce dificultad
        target_terms = self.geo_terms.get(self.target_geo, [])
        if any(term in keyword_lower for term in target_terms):
            base_difficulty -= 0.1

        return max(0.1, min(0.9, base_difficulty))

    def _estimate_cluster_centrality(self, keyword: str, kw_data: dict) -> float:
        """Estima centralidad en cluster (simplicado sin embeddings por ahora)"""
        if not keyword:
            return 0.5

        # Approximación simple: keywords más "genéricas" tienen mayor centralidad
        keyword_lower = keyword.lower()
        word_count = len(keyword_lower.split())

        # Keywords con 2-3 palabras tienden a ser más centrales
        if word_count == 2:
            base_centrality = 0.8
        elif word_count == 3:
            base_centrality = 0.7
        elif word_count == 1:
            base_centrality = 0.9  # Muy central pero muy genérico
        else:
            base_centrality = 0.4  # Long-tail menos central

        # Ajustar por términos core del dominio
        core_terms = ["marketing", "seo", "publicidad", "digital", "online"]
        if any(term in keyword_lower for term in core_terms):
            base_centrality += 0.1

        return max(0.1, min(1.0, base_centrality))

    def _calculate_freshness_boost(self, keyword: str) -> float:
        """Calcula boost por frescura/estacionalidad (simplificado)"""
        if not keyword:
            return 0.0

        keyword_lower = keyword.lower()

        # Boost para términos actuales
        current_year = str(datetime.now().year)
        if current_year in keyword_lower:
            return 0.15  # Máximo boost para año actual

        # Boost para términos trendy
        trendy_terms = ["ia", "inteligencia artificial", "automation", "chatbot", "saas"]
        if any(term in keyword_lower for term in trendy_terms):
            return 0.10

        # Boost para términos de temporada (Q4)
        if datetime.now().month >= 10:  # Q4
            seasonal_terms = ["navidad", "año nuevo", "black friday", "cyber monday"]
            if any(term in keyword_lower for term in seasonal_terms):
                return 0.12

        return 0.0

    def _calculate_percentiles(self, keywords_batch: list[dict]) -> dict:
        """Calcula percentiles para todas las señales en el lote"""
        signals = [
            "trend_norm",
            "volume_norm",
            "competition_norm",
            "serp_difficulty",
            "cluster_centrality",
        ]
        percentiles = {}

        for signal in signals:
            values = [kw.get(signal, 0) for kw in keywords_batch]
            if values:
                # Crear función de percentil para esta señal
                sorted_values = sorted(values)
                percentiles[signal] = sorted_values
            else:
                percentiles[signal] = [0]

        return percentiles

    def _get_percentile_rank(self, value: float, sorted_values: list[float]) -> float:
        """Calcula percentile rank de un valor en una lista ordenada"""
        if not sorted_values:
            return 0.0

        if value <= sorted_values[0]:
            return 0.0
        if value >= sorted_values[-1]:
            return 1.0

        # Buscar posición del valor
        for i, v in enumerate(sorted_values):
            if value <= v:
                return i / len(sorted_values)

        return 1.0

    def _calculate_final_score(self, kw_data: dict, signal_percentiles: dict) -> float:
        """Calcula score final usando percentile ranking"""

        # Obtener percentiles para señales principales
        trend_pct = self._get_percentile_rank(
            kw_data.get("trend_norm", 0), signal_percentiles.get("trend_norm", [0])
        )

        volume_pct = self._get_percentile_rank(
            kw_data.get("volume_norm", 0), signal_percentiles.get("volume_norm", [0])
        )

        serp_opportunity_pct = self._get_percentile_rank(
            1.0 - kw_data.get("serp_difficulty", 0.5),  # Invertir difficulty
            signal_percentiles.get("serp_difficulty", [0]),
        )

        cluster_centrality_pct = self._get_percentile_rank(
            kw_data.get("cluster_centrality", 0.5),
            signal_percentiles.get("cluster_centrality", [0]),
        )

        # Aplicar fórmula del ensamble
        score = (
            self.weights["trend"] * trend_pct
            + self.weights["volume"] * volume_pct
            + self.weights["serp_opportunity"] * serp_opportunity_pct
            + self.weights["cluster_centrality"] * cluster_centrality_pct
            + self.weights["intent"] * kw_data.get("intent_weight", 0.4)
            + self.weights["geo"] * kw_data.get("geo_weight", 0.6)
            + self.weights["freshness"] * kw_data.get("freshness_boost", 0.0)
        )

        # Convertir a escala 0-100
        return round(score * 100, 2)

    def _apply_guardrails(self, keywords_batch: list[dict]) -> list[dict]:
        """Aplica guardrails para evitar falsos positivos"""
        polished = []

        for kw_data in keywords_batch:
            keyword = kw_data.get("keyword", "")
            keyword_lower = keyword.lower()
            score = kw_data.get("advanced_score", 0)

            # Guardrail 1: Penalizar informational sin geo-targeting
            intent_weight = kw_data.get("intent_weight", 0.4)
            geo_weight = kw_data.get("geo_weight", 0.6)

            if intent_weight <= 0.4 and geo_weight <= 0.6:  # Informational sin geo
                score -= 8
                kw_data["guardrail_penalty"] = "informational_no_geo"

            # Guardrail 2: Long-tail mínimo
            word_count = len(keyword_lower.split())
            if word_count == 1:
                score -= 10  # Penalización fuerte para términos genéricos
                kw_data["guardrail_penalty"] = "too_generic"
            elif 3 <= word_count <= 5:
                score += 3  # Bonus para long-tail óptimo
                kw_data["guardrail_bonus"] = "optimal_longtail"

            # Guardrail 3: Stopwords locales irrelevantes
            irrelevant_terms = {
                "pe": ["sepe", "santander", "utn", "sena"],  # No relevantes para PE
                "es": ["conacyt", "unam", "ipn"],  # No relevantes para ES
                "mx": ["sunat", "reniec", "essalud"],  # No relevantes para MX
            }

            target_irrelevant = irrelevant_terms.get(self.target_geo, [])
            if any(term in keyword_lower for term in target_irrelevant):
                score -= 6
                kw_data["guardrail_penalty"] = "irrelevant_local_terms"

            # Aplicar score final
            kw_data["advanced_score"] = max(0, score)
            polished.append(kw_data)

        return polished

    def validate_improvements(self, old_results: list[dict], new_results: list[dict]) -> dict:
        """
        Valida que las mejoras del scoring son efectivas

        Args:
            old_results: Keywords con scoring anterior
            new_results: Keywords con nuevo scoring avanzado

        Returns:
            Dict con métricas de validación
        """
        top_50_old = old_results[:50]
        top_50_new = new_results[:50]

        metrics = {
            "transactional_intent": {
                "old": self._calculate_intent_percentage(top_50_old, "transactional"),
                "new": self._calculate_intent_percentage(top_50_new, "transactional"),
                "target": 50.0,  # Meta ≥ 50%
            },
            "geo_targeting": {
                "old": self._calculate_geo_percentage(top_50_old),
                "new": self._calculate_geo_percentage(top_50_new),
                "target": 40.0,  # Meta ≥ 40%
            },
            "score_variance": {
                "old": self._calculate_score_variance(top_50_old),
                "new": self._calculate_score_variance(top_50_new),
                "improvement": "lower_is_better",  # Más estabilidad
            },
            "avg_word_count": {
                "old": self._calculate_avg_word_count(top_50_old),
                "new": self._calculate_avg_word_count(top_50_new),
                "target": 3.0,  # Meta 2-4 palabras promedio
            },
        }

        # Calcular mejoras
        metrics["improvements"] = {
            "transactional_lift": metrics["transactional_intent"]["new"]
            - metrics["transactional_intent"]["old"],
            "geo_lift": metrics["geo_targeting"]["new"] - metrics["geo_targeting"]["old"],
            "variance_reduction": metrics["score_variance"]["old"]
            - metrics["score_variance"]["new"],
            "meets_targets": self._check_targets_met(metrics),
        }

        return metrics

    def _calculate_intent_percentage(self, keywords: list[dict], target_intent: str) -> float:
        """Calcula porcentaje de keywords con intención específica"""
        if not keywords:
            return 0.0

        count = 0
        for kw in keywords:
            intent_weight = kw.get("intent_weight", 0.4)
            if target_intent == "transactional" and intent_weight >= 0.9:
                count += 1
            elif target_intent == "commercial" and 0.6 <= intent_weight < 0.9:
                count += 1
            elif target_intent == "informational" and intent_weight < 0.6:
                count += 1

        return (count / len(keywords)) * 100

    def _calculate_geo_percentage(self, keywords: list[dict]) -> float:
        """Calcula porcentaje de keywords con geo-targeting"""
        if not keywords:
            return 0.0

        geo_count = sum(1 for kw in keywords if kw.get("geo_weight", 0.6) >= 0.9)
        return (geo_count / len(keywords)) * 100

    def _calculate_score_variance(self, keywords: list[dict]) -> float:
        """Calcula varianza de scores (estabilidad)"""
        if not keywords:
            return 0.0

        scores = [kw.get("advanced_score", kw.get("score", 0)) for kw in keywords]
        if len(scores) < 2:
            return 0.0

        return statistics.variance(scores)

    def _calculate_avg_word_count(self, keywords: list[dict]) -> float:
        """Calcula promedio de palabras por keyword"""
        if not keywords:
            return 0.0

        word_counts = []
        for kw in keywords:
            keyword = kw.get("keyword", "")
            word_counts.append(len(keyword.split()))

        return statistics.mean(word_counts) if word_counts else 0.0

    def _check_targets_met(self, metrics: dict) -> dict:
        """Verifica si se cumplen las metas establecidas"""
        return {
            "transactional_target": metrics["transactional_intent"]["new"]
            >= metrics["transactional_intent"]["target"],
            "geo_target": metrics["geo_targeting"]["new"] >= metrics["geo_targeting"]["target"],
            "variance_improved": metrics["score_variance"]["new"]
            < metrics["score_variance"]["old"],
            "optimal_length": 2.0 <= metrics["avg_word_count"]["new"] <= 4.0,
        }


# Mantener compatibilidad con KeywordScorer original
class KeywordScorer(AdvancedKeywordScorer):
    """Wrapper para mantener compatibilidad con la API original"""

    def __init__(
        self, trend_weight: float = 0.4, volume_weight: float = 0.4, competition_weight: float = 0.2
    ):
        # Inicializar con configuración por defecto
        super().__init__(target_geo="PE", target_intent="transactional")

        # Mantener pesos originales para métodos legacy
        self.trend_weight = trend_weight
        self.volume_weight = volume_weight
        self.competition_weight = competition_weight

        logging.info("KeywordScorer (legacy) initialized with advanced backend")

    def calculate_score(
        self, trend_score: float, volume: int, competition: float, keyword_text: str = ""
    ) -> float:
        """Método de compatibilidad que usa el sistema avanzado por detrás"""
        try:
            # Preparar datos para el scorer avanzado
            keyword_data = [
                {
                    "keyword": keyword_text,
                    "trend_score": trend_score,
                    "volume": volume,
                    "competition": competition,
                }
            ]

            # Usar el sistema avanzado
            results = self.calculate_advanced_score(keyword_data)

            if results:
                return results[0].get("advanced_score", 0.0)
            else:
                return 0.0

        except Exception as e:
            logging.error(f"Error in legacy calculate_score: {e}")
            return 0.0
