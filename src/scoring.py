import logging
import math
import re
from collections import defaultdict
from datetime import datetime
from difflib import SequenceMatcher

from sklearn.preprocessing import MinMaxScaler


class KeywordScorer:
    """Sistema de scoring para keywords basado en múltiples factores"""

    def __init__(
        self, trend_weight: float = 0.4, volume_weight: float = 0.4, competition_weight: float = 0.2
    ):
        """
        Inicializa el scorer con pesos configurables

        Args:
            trend_weight: Peso para el score de tendencia (0-1)
            volume_weight: Peso para el volumen estimado (0-1)
            competition_weight: Peso para la competencia (0-1)
        """
        self.trend_weight = trend_weight
        self.volume_weight = volume_weight
        self.competition_weight = competition_weight

        # Validar que los pesos sumen 1.0
        total_weight = trend_weight + volume_weight + competition_weight
        if abs(total_weight - 1.0) > 0.01:
            logging.warning(f"Weights sum to {total_weight}, normalizing...")
            self.trend_weight = trend_weight / total_weight
            self.volume_weight = volume_weight / total_weight
            self.competition_weight = competition_weight / total_weight

        self.scaler = MinMaxScaler()
        logging.info(
            f"KeywordScorer initialized with weights: T={self.trend_weight:.2f}, V={self.volume_weight:.2f}, C={self.competition_weight:.2f}"
        )

    def calculate_score(
        self, trend_score: float, volume: int, competition: float, keyword_text: str = ""
    ) -> float:
        """
        Calcula el score final de una keyword usando la fórmula:
        score = (trend_score * trend_weight) + (volume_norm * volume_weight) + ((1 - competition) * competition_weight)

        Args:
            trend_score: Score de tendencia (0-100)
            volume: Volumen estimado
            competition: Nivel de competencia (0-1)
            keyword_text: Texto de la keyword para análisis adicional

        Returns:
            Score final (0-100)
        """
        try:
            # Normalizar trend_score (0-100 a 0-1)
            norm_trend = max(0, min(100, trend_score)) / 100.0

            # Normalizar volumen usando escala logarítmica
            norm_volume = self._normalize_volume(volume)

            # Normalizar competencia (invertir: menor competencia = mejor score)
            norm_competition = 1.0 - max(0, min(1, competition))

            # Aplicar bonificaciones por características de la keyword
            keyword_bonus = self._calculate_keyword_bonus(keyword_text)

            # Calcular score base
            base_score = (
                norm_trend * self.trend_weight
                + norm_volume * self.volume_weight
                + norm_competition * self.competition_weight
            )

            # Aplicar bonus y convertir a escala 0-100
            final_score = min(100, (base_score + keyword_bonus) * 100)

            logging.debug(
                f"Score calculation - Trend: {norm_trend:.3f}, Volume: {norm_volume:.3f}, "
                f"Competition: {norm_competition:.3f}, Bonus: {keyword_bonus:.3f}, Final: {final_score:.2f}"
            )

            return round(final_score, 2)

        except Exception as e:
            logging.error(f"Error calculating score: {e}")
            return 0.0

    def _normalize_volume(self, volume: int) -> float:
        """Normaliza el volumen usando escala logarítmica"""
        if volume <= 0:
            return 0.0

        # Usar log para manejar rangos amplios de volumen
        # Asumir rango típico de 1 a 1,000,000
        log_volume = math.log10(max(1, volume))
        log_max = math.log10(1000000)  # 1M como máximo

        return min(1.0, log_volume / log_max)

    def estimate_volume(self, keyword: str) -> int:
        """
        Estima volumen de búsquedas basado en características del keyword
        cuando no hay datos de Google Trends disponibles
        """
        if not keyword:
            return 0

        keyword_lower = keyword.lower().strip()
        word_count = len(keyword_lower.split())

        # Base según longitud (palabras más específicas = menos volumen)
        if word_count == 1:
            base_volume = 10000  # Términos genéricos altos
        elif word_count == 2:
            base_volume = 5000  # Términos de nivel medio
        elif word_count <= 4:
            base_volume = 2000  # Long-tail moderado
        else:
            base_volume = 500  # Very long-tail bajo

        # Modificadores basados en intención
        multiplier = 1.0

        # Términos informativos (más volumen)
        info_terms = ["que es", "qué es", "como", "cómo", "cuando", "cuándo", "donde", "dónde"]
        if any(keyword_lower.startswith(term) for term in info_terms):
            multiplier *= 1.5

        # Términos comerciales (volumen moderado-alto)
        commercial_terms = ["curso", "gratis", "online", "precio", "costo", "barato", "mejor"]
        if any(term in keyword_lower for term in commercial_terms):
            multiplier *= 1.3

        # Términos de marca/localización (menos volumen)
        location_terms = ["lima", "peru", "perú", "madrid", "mexico"]
        if any(term in keyword_lower for term in location_terms):
            multiplier *= 0.7

        # Términos muy específicos (menos volumen)
        specific_terms = ["herramientas de", "estrategia de", "plan de"]
        if any(term in keyword_lower for term in specific_terms):
            multiplier *= 0.6

        estimated = int(base_volume * multiplier)
        return max(10, min(100000, estimated))  # Entre 10 y 100k

    def estimate_competition(self, keyword: str) -> float:
        """
        Estima nivel de competencia basado en características del keyword
        """
        if not keyword:
            return 0.5

        keyword_lower = keyword.lower().strip()
        word_count = len(keyword_lower.split())

        # Base según longitud (más palabras = menos competencia)
        if word_count == 1:
            base_competition = 0.9  # Muy competitivo
        elif word_count == 2:
            base_competition = 0.7  # Alto
        elif word_count <= 4:
            base_competition = 0.5  # Medio
        else:
            base_competition = 0.3  # Bajo

        # Modificadores
        modifier = 0.0

        # Términos comerciales aumentan competencia
        commercial_terms = ["curso", "precio", "comprar", "mejor", "top", "gratis"]
        commercial_count = sum(1 for term in commercial_terms if term in keyword_lower)
        modifier += commercial_count * 0.1

        # Términos informativos reducen competencia
        info_terms = ["que es", "qué es", "como hacer", "cómo hacer"]
        if any(keyword_lower.startswith(term) for term in info_terms):
            modifier -= 0.15

        # Localización reduce competencia
        location_terms = ["lima", "peru", "perú", "madrid", "mexico"]
        if any(term in keyword_lower for term in location_terms):
            modifier -= 0.1

        final_competition = base_competition + modifier
        return max(0.1, min(0.9, final_competition))

    def categorize_keyword(self, keyword: str) -> str:
        """
        Categoriza automáticamente el keyword según su contenido
        """
        if not keyword:
            return "otros"

        keyword_lower = keyword.lower().strip()

        # Priorizar términos comerciales (orden importa)
        if any(term in keyword_lower for term in ["precio", "costo", "gratis", "barato"]):
            return "comercial"
        elif any(term in keyword_lower for term in ["seo", "posicionamiento", "google"]):
            return "seo"
        elif any(
            term in keyword_lower
            for term in ["redes sociales", "facebook", "instagram", "tiktok", "twitter"]
        ):
            return "redes_sociales"
        elif any(term in keyword_lower for term in ["curso", "aprender", "estudiar", "tutorial"]):
            return "educacion"
        elif any(term in keyword_lower for term in ["contenido", "blog", "articulo", "redaccion"]):
            return "contenidos"
        elif any(
            term in keyword_lower
            for term in ["herramientas", "software", "aplicacion", "plataforma"]
        ):
            return "herramientas"
        elif any(term in keyword_lower for term in ["agencia", "empresa", "negocio", "pymes"]):
            return "servicios"
        elif any(term in keyword_lower for term in ["digital", "online", "internet"]):
            return "digital"
        else:
            return "marketing_general"

    def classify_intent(self, keyword: str) -> str:
        """
        Clasifica la intención del keyword en: Informational, Commercial, Transactional
        """
        if not keyword:
            return "unknown"

        keyword_lower = keyword.lower().strip()

        # Informational intent patterns
        info_patterns = [
            r"\b(qué es|que es|cómo|como)\b",
            r"\b(guía|tutorial|ejemplo|pasos)\b",
            r"\b(aprende|aprender|definición)\b",
        ]

        # Commercial intent patterns
        commercial_patterns = [
            r"\b(mejor|top|vs|comparar)\b",
            r"\b(precio|costo|barato|gratis)\b",
            r"\b(curso|diplomado|clase)\b",
            r"\b(reseña|review|opinión)\b",
        ]

        # Transactional intent patterns
        transactional_patterns = [
            r"\b(agencia|empresa|consultor)\b",
            r"\b(servicio|contratar|comprar)\b",
            r"\b(lima|perú|madrid)\b",  # Geographic = service intent
            r"\b(para pymes|para empresas)\b",
        ]

        # Check patterns in order of priority
        for pattern in transactional_patterns:
            if re.search(pattern, keyword_lower):
                return "transactional"

        for pattern in commercial_patterns:
            if re.search(pattern, keyword_lower):
                return "commercial"

        for pattern in info_patterns:
            if re.search(pattern, keyword_lower):
                return "informational"

        return "informational"  # Default for most queries

    def create_heuristic_clusters(self, keywords_data: list[dict]) -> dict[str, list[dict]]:
        """
        Crea clusters heurísticos basados en patrones de keywords
        Implementa la estrategia del plan de mejora
        """
        clusters = defaultdict(list)

        # Define clustering patterns (orden importa)
        cluster_patterns = {
            "cursos_formacion": [
                r"\b(curso|clase|diplomado|certificado|capacitación)\b",
                r"\b(aprender|estudiar|enseñar)\b",
            ],
            "como_hacer_howto": [
                r"\b(cómo|como) (hacer|crear|desarrollar)\b",
                r"\b(pasos|guía|tutorial)\b",
            ],
            "que_es_conceptos": [r"\b(qué es|que es|definición)\b", r"\b(significado|concepto)\b"],
            "servicios_lima_local": [
                r"\b(agencia|empresa|consultor)\b.*\b(lima|perú)\b",
                r"\b(lima|perú)\b.*\b(agencia|empresa|consultor)\b",
                r"\b(publicidad|marketing).*lima\b",
            ],
            "pymes_empresas": [
                r"\b(pymes|empresas|negocios)\b",
                r"\bpara (pequeñas|medianas) empresas\b",
            ],
            "redes_sociales": [
                r"\b(redes sociales|facebook|instagram|tiktok|twitter)\b",
                r"\b(social media|community manager)\b",
            ],
            "seo_posicionamiento": [r"\b(seo|posicionamiento)\b", r"\b(google|buscador|ranking)\b"],
            "marketing_contenidos": [
                r"\b(contenido|contenidos|blog)\b",
                r"\b(copywriting|redacción)\b",
            ],
            "herramientas_software": [
                r"\b(herramientas|software|aplicación|plataforma)\b",
                r"\b(automatización|crm)\b",
            ],
            "digital_online": [r"\b(digital|online|internet)\b", r"\b(ecommerce|tienda online)\b"],
        }

        # Classify each keyword into clusters
        for kw_data in keywords_data:
            keyword = kw_data.get("keyword", "")
            keyword_lower = keyword.lower()

            # Find best cluster match
            assigned = False
            for cluster_name, patterns in cluster_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, keyword_lower):
                        clusters[cluster_name].append(
                            {
                                **kw_data,
                                "cluster_id": cluster_name,
                                "intent": self.classify_intent(keyword),
                            }
                        )
                        assigned = True
                        break
                if assigned:
                    break

            # Default cluster for unmatched keywords
            if not assigned:
                clusters["marketing_general"].append(
                    {
                        **kw_data,
                        "cluster_id": "marketing_general",
                        "intent": self.classify_intent(keyword),
                    }
                )

        return dict(clusters)

    def identify_canonical_keywords(self, cluster_data: list[dict]) -> str:
        """
        Identifica la keyword canónica (representativa) del cluster
        Basado en mayor volumen y menor competencia
        """
        if not cluster_data:
            return ""

        # Calculate opportunity score for each keyword
        best_keyword = ""
        best_score = 0

        for kw_data in cluster_data:
            volume = kw_data.get("volume", 0)
            competition = kw_data.get("competition", 0.5)

            # Simple opportunity formula
            opp_score = volume * (1 - competition)

            if opp_score > best_score:
                best_score = opp_score
                best_keyword = kw_data.get("keyword", "")

        return best_keyword

    def calculate_opportunity_score(
        self, volume: int, competition: float, keyword: str = ""
    ) -> float:
        """
        Calcula el opportunity score según el plan de mejora:
        opp_score = norm(volume) * (1 - competition) * trend_boost * cluster_focus
        """
        if volume <= 0:
            return 0.0

        # Normalize volume (simple approach)
        norm_volume = min(volume / 10000.0, 1.0)  # Cap at 10k

        # Base opportunity score
        base_score = norm_volume * (1 - competition)

        # Trend boost (1.0 for now, can add trends data later)
        trend_boost = 1.0

        # Cluster focus boost for geographic/commercial terms
        cluster_focus = 1.0
        keyword_lower = keyword.lower() if keyword else ""

        # Boost for Peru/Lima focus
        if any(term in keyword_lower for term in ["lima", "perú", "peru"]):
            cluster_focus *= 1.2

        # Boost for PYMES focus
        if any(term in keyword_lower for term in ["pymes", "empresas", "negocios"]):
            cluster_focus *= 1.1

        # Boost for commercial intent
        if any(term in keyword_lower for term in ["curso", "precio", "servicio", "agencia"]):
            cluster_focus *= 1.05

        return base_score * trend_boost * cluster_focus

    def _calculate_keyword_bonus(self, keyword: str) -> float:
        """Calcula bonificaciones basadas en características de la keyword"""
        if not keyword:
            return 0.0

        bonus = 0.0
        keyword_lower = keyword.lower().strip()

        # Bonus por long-tail (más palabras = más específico)
        word_count = len(keyword_lower.split())
        if word_count >= 3:
            bonus += 0.05  # 5% bonus para long-tail
        if word_count >= 5:
            bonus += 0.03  # 3% adicional para very long-tail

        # Penalización fuerte por una sola palabra (demasiado genérica)
        if word_count == 1:
            bonus -= 0.15  # -15%

        # Bonus por palabras comerciales
        commercial_terms = [
            "comprar",
            "precio",
            "costo",
            "barato",
            "ofertas",
            "descuento",
            "tienda",
            "venta",
            "mejor",
            "top",
            "review",
            "comparar",
            "gratis",
            "curso",
            "guía",
            "como",
            "tutorial",
        ]
        commercial_bonus = sum(0.02 for term in commercial_terms if term in keyword_lower)
        bonus += min(0.1, commercial_bonus)  # Máximo 10% por términos comerciales

        # Bonus por palabras de localización
        location_terms = [
            "madrid",
            "barcelona",
            "valencia",
            "sevilla",
            "españa",
            "mexico",
            "argentina",
            "colombia",
            "chile",
            "peru",
            "cerca",
            "local",
            "zona",
        ]
        location_bonus = sum(0.03 for term in location_terms if term in keyword_lower)
        bonus += min(0.08, location_bonus)  # Máximo 8% por localización

        # Bonus por preguntas (priorizar intención informativa útil)
        question_terms = [
            "que",
            "qué",
            "como",
            "cómo",
            "cuando",
            "cuándo",
            "donde",
            "dónde",
            "por qué",
            "para qué",
        ]
        if any(keyword_lower.startswith(term + " ") for term in question_terms):
            bonus += 0.05  # +5%

        return max(-0.2, min(0.25, bonus))  # Limitar bonus entre -20% y +25%

    def score_keywords_batch(self, keywords_data: list[dict]) -> list[dict]:
        """
        Calcula scores para un lote de keywords

        Args:
            keywords_data: Lista de diccionarios con datos de keywords
                          Cada dict debe tener: keyword, trend_score, volume, competition

        Returns:
            Lista de keywords con scores calculados
        """
        scored_keywords = []

        for kw_data in keywords_data:
            try:
                score = self.calculate_score(
                    trend_score=kw_data.get("trend_score", 0),
                    volume=kw_data.get("volume", 0),
                    competition=kw_data.get("competition", 0.5),
                    keyword_text=kw_data.get("keyword", ""),
                )

                # Agregar score al diccionario
                kw_data_scored = kw_data.copy()
                kw_data_scored["score"] = score
                kw_data_scored["scored_at"] = datetime.now().isoformat()

                scored_keywords.append(kw_data_scored)

            except Exception as e:
                logging.error(f"Error scoring keyword {kw_data.get('keyword', 'unknown')}: {e}")
                continue

        # Ordenar por score descendente
        scored_keywords.sort(key=lambda x: x.get("score", 0), reverse=True)

        logging.info(f"Scored {len(scored_keywords)} keywords")
        return scored_keywords

    def deduplicate_keywords(
        self, keywords_data: list[dict], similarity_threshold: float = 0.85
    ) -> list[dict]:
        """
        Elimina keywords duplicados y muy similares

        Args:
            keywords_data: Lista de keywords con datos
            similarity_threshold: Umbral de similitud (0.85 = 85% similar)

        Returns:
            Lista de keywords deduplicada
        """
        if not keywords_data:
            return []

        unique_keywords: list[dict] = []

        for kw_data in keywords_data:
            keyword = kw_data.get("keyword", "").strip().lower()
            if not keyword:
                continue

            # Normalizar para comparación
            normalized = self._normalize_keyword_for_comparison(keyword)

            # Verificar si ya tenemos algo muy similar
            is_duplicate = False

            for existing in unique_keywords:
                existing_keyword = existing.get("keyword", "").strip().lower()
                existing_normalized = self._normalize_keyword_for_comparison(existing_keyword)

                # Calcular similitud
                similarity = self._calculate_similarity(normalized, existing_normalized)

                if similarity >= similarity_threshold:
                    is_duplicate = True
                    # Conservar el de mayor score
                    if kw_data.get("score", 0) > existing.get("score", 0):
                        unique_keywords.remove(existing)
                        unique_keywords.append(kw_data)
                    break

            if not is_duplicate:
                unique_keywords.append(kw_data)

        logging.info(f"Deduplication: {len(keywords_data)} -> {len(unique_keywords)} keywords")
        return unique_keywords

    def _normalize_keyword_for_comparison(self, keyword: str) -> str:
        """Normaliza keyword para comparación de similitud"""
        # Remover acentos, espacios extra, palabras de stop menores
        import re

        normalized = re.sub(r"\s+", " ", keyword.strip().lower())

        # Remover artículos comunes que no afectan el significado
        stop_words = ["el", "la", "los", "las", "un", "una", "de", "del", "en", "y", "o"]
        words = normalized.split()
        filtered_words = [word for word in words if word not in stop_words]

        return " ".join(filtered_words)

    def _calculate_similarity(self, keyword1: str, keyword2: str) -> float:
        """Calcula similitud entre dos keywords usando SequenceMatcher"""
        return SequenceMatcher(None, keyword1, keyword2).ratio()

    def rank_keywords(self, keywords_data: list[dict], filters: dict | None = None) -> list[dict]:
        """
        Rankea keywords aplicando filtros opcionales

        Args:
            keywords_data: Lista de keywords con scores
            filters: Filtros opcionales (min_score, max_competition, etc.)

        Returns:
            Lista rankeada y filtrada
        """
        filtered_keywords = keywords_data.copy()

        if filters:
            # Aplicar filtro de score mínimo
            if "min_score" in filters:
                filtered_keywords = [
                    kw for kw in filtered_keywords if kw.get("score", 0) >= filters["min_score"]
                ]

            # Aplicar filtro de competencia máxima
            if "max_competition" in filters:
                filtered_keywords = [
                    kw
                    for kw in filtered_keywords
                    if kw.get("competition", 1) <= filters["max_competition"]
                ]

            # Aplicar filtro de volumen mínimo
            if "min_volume" in filters:
                filtered_keywords = [
                    kw for kw in filtered_keywords if kw.get("volume", 0) >= filters["min_volume"]
                ]

            # Aplicar filtro de longitud de keyword
            if "min_words" in filters:
                min_words = filters["min_words"]
                filtered_keywords = [
                    kw
                    for kw in filtered_keywords
                    if len(kw.get("keyword", "").split()) >= min_words
                ]

        # Agregar ranking position
        for i, keyword in enumerate(filtered_keywords):
            keyword["rank"] = i + 1

        logging.info(f"Ranked {len(filtered_keywords)} keywords after filtering")
        return filtered_keywords

    def get_keyword_insights(self, keyword_data: dict) -> dict:
        """
        Genera insights detallados para una keyword específica

        Args:
            keyword_data: Datos de la keyword

        Returns:
            Dict con insights y recomendaciones
        """
        insights = {
            "keyword": keyword_data.get("keyword", ""),
            "score": keyword_data.get("score", 0),
            "category": self._categorize_keyword(keyword_data),
            "strengths": [],
            "weaknesses": [],
            "recommendations": [],
        }

        trend_score = keyword_data.get("trend_score", 0)
        volume = keyword_data.get("volume", 0)
        competition = keyword_data.get("competition", 0.5)

        # Analizar fortalezas
        if trend_score > 70:
            insights["strengths"].append("Alta tendencia de búsqueda")
        if volume > 1000:
            insights["strengths"].append("Buen volumen de búsquedas")
        if competition < 0.3:
            insights["strengths"].append("Baja competencia")

        # Analizar debilidades
        if trend_score < 20:
            insights["weaknesses"].append("Tendencia de búsqueda baja")
        if volume < 100:
            insights["weaknesses"].append("Volumen limitado")
        if competition > 0.8:
            insights["weaknesses"].append("Alta competencia")

        # Generar recomendaciones
        insights["recommendations"] = self._generate_recommendations(keyword_data)

        return insights

    def _categorize_keyword(self, keyword_data: dict) -> str:
        """Categoriza una keyword basada en sus métricas"""
        score = keyword_data.get("score", 0)

        if score >= 80:
            return "excelente"
        elif score >= 60:
            return "buena"
        elif score >= 40:
            return "promedio"
        elif score >= 20:
            return "baja"
        else:
            return "muy_baja"

    def _generate_recommendations(self, keyword_data: dict) -> list[str]:
        """Genera recomendaciones específicas para una keyword"""
        recommendations = []

        trend_score = keyword_data.get("trend_score", 0)
        volume = keyword_data.get("volume", 0)
        competition = keyword_data.get("competition", 0.5)
        keyword = keyword_data.get("keyword", "")

        # Recomendaciones basadas en métricas
        if trend_score > 50 and competition < 0.5:
            recommendations.append(
                "Keyword ideal para contenido nuevo - alta tendencia, baja competencia"
            )

        if volume > 1000 and competition > 0.7:
            recommendations.append("Considerar variaciones long-tail para reducir competencia")

        if len(keyword.split()) < 3:
            recommendations.append("Explorar versiones long-tail más específicas")

        if trend_score < 30:
            recommendations.append("Monitorear tendencias estacionales antes de invertir recursos")

        if competition > 0.8:
            recommendations.append("Focalizar en contenido de muy alta calidad para competir")

        return recommendations[:3]  # Limitar a 3 recomendaciones
