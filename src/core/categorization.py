import logging
import os
import re


class KeywordCategorizer:
    """Categorización automática de keywords por intención y tipo de negocio"""

    def __init__(self, target_geo: str = "PE", target_business: str = "services"):
        self.target_geo = os.getenv("SCORING_TARGET_GEO", target_geo).lower()
        self.target_business = target_business.lower()

        # Patrones por intención de búsqueda
        self.intent_patterns = {
            "transactional": [
                r"\b(agencia|empresa|consultor|servicio|especialista)\b",
                r"\b(contratar|comprar|solicitar|cotizar|presupuesto)\b",
                r"\b(profesional|experto|certificado)\b",
                r"\bpara (pymes|empresas|negocios|startups)\b",
            ],
            "commercial": [
                r"\b(precio|costo|mejor|top|comparar|vs)\b",
                r"\b(curso|capacitación|diplomado|certificado|online)\b",
                r"\b(herramientas|software|plataforma|saas)\b",
                r"\b(gratis|gratuito|barato|económico|oferta)\b",
                r"\b(review|reseña|opinión)\b",
            ],
            "informational": [
                r"\b(qué es|cómo|para qué|por qué|cuándo)\b",
                r"\b(guía|tutorial|manual|tips|consejos)\b",
                r"\b(definición|concepto|significado)\b",
                r"\b(ejemplos|tipos|ventajas|desventajas)\b",
                r"\b(tendencias|futuro|estadísticas)\b",
            ],
        }

        # Categorías de servicios específicos
        self.service_categories = {
            "digital_marketing": [
                r"\b(marketing digital|publicidad online|social media)\b",
                r"\b(facebook ads|google ads|instagram)\b",
                r"\b(influencer|community manager)\b",
            ],
            "seo_sem": [
                r"\b(seo|posicionamiento web|sem)\b",
                r"\b(google|buscadores|ranking)\b",
                r"\b(palabras clave|keywords|backlinks)\b",
            ],
            "web_development": [
                r"\b(página web|sitio web|desarrollo web)\b",
                r"\b(diseño web|programación|ecommerce)\b",
                r"\b(wordpress|shopify|html)\b",
            ],
            "data_analytics": [
                r"\b(analytics|google analytics|datos)\b",
                r"\b(métricas|kpi|conversión)\b",
                r"\b(business intelligence|dashboard)\b",
            ],
            "automation": [
                r"\b(automatización|chatbot|crm)\b",
                r"\b(workflows|integración|api)\b",
                r"\b(zapier|make|hubspot)\b",
            ],
        }

        logging.info(
            f"KeywordCategorizer initialized for {self.target_geo} {self.target_business} business"
        )

    def categorize_intent(self, keyword: str) -> str:
        """
        Categoriza la intención de una keyword

        Returns:
            'transactional', 'commercial', o 'informational'
        """
        if not keyword:
            return "informational"

        keyword_lower = keyword.lower()

        # Check transactional first (highest value)
        for pattern in self.intent_patterns["transactional"]:
            if re.search(pattern, keyword_lower):
                return "transactional"

        # Check commercial
        for pattern in self.intent_patterns["commercial"]:
            if re.search(pattern, keyword_lower):
                return "commercial"

        return "informational"

    def intent_probability(self, keyword: str) -> float:
        """Estimate probability that the intent is transactional/commercial.

        Simple heuristic: transactional 0.85, commercial 0.6, informational 0.3,
        with small boost if a specific service category is detected.
        """
        intent = self.categorize_intent(keyword)
        base = {"transactional": 0.85, "commercial": 0.6, "informational": 0.3}.get(intent, 0.3)
        service_type = self.categorize_service_type(keyword)
        if service_type != "general":
            base = min(1.0, base + 0.05)
        return base

    def categorize_service_type(self, keyword: str) -> str:
        """
        Categoriza el tipo de servicio de una keyword

        Returns:
            Categoría del servicio o 'general'
        """
        if not keyword:
            return "general"

        keyword_lower = keyword.lower()

        for category, patterns in self.service_categories.items():
            for pattern in patterns:
                if re.search(pattern, keyword_lower):
                    return category

        return "general"

    def is_business_relevant(self, keyword: str) -> tuple[bool, str]:
        """
        Determina si una keyword es relevante para el negocio objetivo

        Returns:
            (is_relevant, reason)
        """
        if not keyword:
            return False, "empty_keyword"

        keyword_lower = keyword.lower()

        # Términos irrelevantes para servicios profesionales
        irrelevant_terms = [
            "curso",
            "clases",
            "universidad",
            "carrera",
            "estudiar",
            "gratis",
            "gratuito",
            "barato",
            "económico",
            "tutorial básico",
            "principiantes",
            "para niños",
            "hobby",
            "pasatiempo",
            "diversión",
        ]

        for term in irrelevant_terms:
            if term in keyword_lower:
                return False, f"irrelevant_term: {term}"

        # Términos demasiado genéricos (solo una palabra común)
        single_words = ["marketing", "publicidad", "diseño", "web", "digital"]
        if keyword_lower.strip() in single_words:
            return False, "too_generic"

        # Términos de la competencia directa
        competitor_terms = [
            "platzi",
            "crehana",
            "domestika",
            "udemy",
            "coursera",
            "semrush",
            "ahrefs",
            "moz",
            "hubspot",  # Evitar keywords de marcas
        ]

        for term in competitor_terms:
            if term in keyword_lower:
                return False, f"competitor_brand: {term}"

        return True, "relevant"

    def get_priority_score(self, keyword: str) -> float:
        """
        Calcula score de prioridad basado en categorización

        Returns:
            Score 0.0-1.0 donde 1.0 es máxima prioridad
        """
        if not keyword:
            return 0.0

        # Base score por relevancia
        is_relevant, reason = self.is_business_relevant(keyword)
        if not is_relevant:
            return 0.1  # Penalización fuerte

        base_score = 0.6

        # Bonus por intención
        intent = self.categorize_intent(keyword)
        intent_bonus = {"transactional": 0.3, "commercial": 0.2, "informational": 0.0}
        base_score += intent_bonus.get(intent, 0.0)

        # Bonus por categoría de servicio
        service_type = self.categorize_service_type(keyword)
        if service_type != "general":
            base_score += 0.1

        return min(1.0, base_score)

    def filter_keywords(
        self, keywords: list[dict], min_priority: float = 0.4
    ) -> tuple[list[dict], list[dict]]:
        """
        Filtra keywords por relevancia y prioridad

        Args:
            keywords: Lista de keywords con datos
            min_priority: Score mínimo de prioridad para incluir

        Returns:
            (keywords_filtered, keywords_rejected)
        """
        filtered = []
        rejected = []

        for kw_data in keywords:
            keyword = kw_data.get("keyword", "")
            priority = self.get_priority_score(keyword)

            # Agregar metadatos de categorización
            kw_data["intent"] = self.categorize_intent(keyword)
            kw_data["intent_prob"] = self.intent_probability(keyword)
            kw_data["service_category"] = self.categorize_service_type(keyword)
            kw_data["priority_score"] = priority

            is_relevant, reason = self.is_business_relevant(keyword)
            kw_data["relevance_reason"] = reason

            if priority >= min_priority and is_relevant:
                filtered.append(kw_data)
            else:
                rejected.append(kw_data)

        logging.info(f"Filtered {len(filtered)} relevant keywords, rejected {len(rejected)}")
        return filtered, rejected


# Función de utilidad para inicializar el categorizador
def create_categorizer(
    target_geo: str = "PE", target_business: str = "services"
) -> KeywordCategorizer:
    """Factory function para crear categorizador"""
    return KeywordCategorizer(target_geo=target_geo, target_business=target_business)
