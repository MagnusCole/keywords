import logging
import math
from typing import List, Dict, Tuple, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import MinMaxScaler
import numpy as np
from datetime import datetime

class KeywordScorer:
    """Sistema de scoring para keywords basado en múltiples factores"""
    
    def __init__(self, trend_weight: float = 0.4, volume_weight: float = 0.4, 
                 competition_weight: float = 0.2):
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
        logging.info(f"KeywordScorer initialized with weights: T={self.trend_weight:.2f}, V={self.volume_weight:.2f}, C={self.competition_weight:.2f}")
    
    def calculate_score(self, trend_score: float, volume: int, 
                       competition: float, keyword_text: str = "") -> float:
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
                norm_trend * self.trend_weight +
                norm_volume * self.volume_weight +
                norm_competition * self.competition_weight
            )
            
            # Aplicar bonus y convertir a escala 0-100
            final_score = min(100, (base_score + keyword_bonus) * 100)
            
            logging.debug(f"Score calculation - Trend: {norm_trend:.3f}, Volume: {norm_volume:.3f}, "
                         f"Competition: {norm_competition:.3f}, Bonus: {keyword_bonus:.3f}, Final: {final_score:.2f}")
            
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
        
        # Bonus por palabras comerciales
        commercial_terms = [
            'comprar', 'precio', 'costo', 'barato', 'ofertas', 'descuento',
            'tienda', 'venta', 'mejor', 'top', 'review', 'comparar',
            'gratis', 'curso', 'guía', 'como', 'tutorial'
        ]
        commercial_bonus = sum(0.02 for term in commercial_terms if term in keyword_lower)
        bonus += min(0.1, commercial_bonus)  # Máximo 10% por términos comerciales
        
        # Bonus por palabras de localización
        location_terms = [
            'madrid', 'barcelona', 'valencia', 'sevilla', 'españa',
            'mexico', 'argentina', 'colombia', 'chile', 'peru',
            'cerca', 'local', 'zona'
        ]
        location_bonus = sum(0.03 for term in location_terms if term in keyword_lower)
        bonus += min(0.08, location_bonus)  # Máximo 8% por localización
        
        # Penalización por keywords muy genéricas
        generic_terms = ['que', 'como', 'donde', 'cuando', 'por', 'para', 'con']
        if any(keyword_lower.startswith(term) for term in generic_terms):
            bonus -= 0.05  # -5% por términos genéricos al inicio
        
        return max(-0.1, min(0.2, bonus))  # Limitar bonus entre -10% y +20%
    
    def score_keywords_batch(self, keywords_data: List[Dict]) -> List[Dict]:
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
                    trend_score=kw_data.get('trend_score', 0),
                    volume=kw_data.get('volume', 0),
                    competition=kw_data.get('competition', 0.5),
                    keyword_text=kw_data.get('keyword', '')
                )
                
                # Agregar score al diccionario
                kw_data_scored = kw_data.copy()
                kw_data_scored['score'] = score
                kw_data_scored['scored_at'] = datetime.now().isoformat()
                
                scored_keywords.append(kw_data_scored)
                
            except Exception as e:
                logging.error(f"Error scoring keyword {kw_data.get('keyword', 'unknown')}: {e}")
                continue
        
        # Ordenar por score descendente
        scored_keywords.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        logging.info(f"Scored {len(scored_keywords)} keywords")
        return scored_keywords
    
    def rank_keywords(self, keywords_data: List[Dict], 
                     filters: Optional[Dict] = None) -> List[Dict]:
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
            if 'min_score' in filters:
                filtered_keywords = [
                    kw for kw in filtered_keywords 
                    if kw.get('score', 0) >= filters['min_score']
                ]
            
            # Aplicar filtro de competencia máxima
            if 'max_competition' in filters:
                filtered_keywords = [
                    kw for kw in filtered_keywords 
                    if kw.get('competition', 1) <= filters['max_competition']
                ]
            
            # Aplicar filtro de volumen mínimo
            if 'min_volume' in filters:
                filtered_keywords = [
                    kw for kw in filtered_keywords 
                    if kw.get('volume', 0) >= filters['min_volume']
                ]
            
            # Aplicar filtro de longitud de keyword
            if 'min_words' in filters:
                min_words = filters['min_words']
                filtered_keywords = [
                    kw for kw in filtered_keywords 
                    if len(kw.get('keyword', '').split()) >= min_words
                ]
        
        # Agregar ranking position
        for i, keyword in enumerate(filtered_keywords):
            keyword['rank'] = i + 1
        
        logging.info(f"Ranked {len(filtered_keywords)} keywords after filtering")
        return filtered_keywords
    
    def get_keyword_insights(self, keyword_data: Dict) -> Dict:
        """
        Genera insights detallados para una keyword específica
        
        Args:
            keyword_data: Datos de la keyword
        
        Returns:
            Dict con insights y recomendaciones
        """
        insights = {
            'keyword': keyword_data.get('keyword', ''),
            'score': keyword_data.get('score', 0),
            'category': self._categorize_keyword(keyword_data),
            'strengths': [],
            'weaknesses': [],
            'recommendations': []
        }
        
        trend_score = keyword_data.get('trend_score', 0)
        volume = keyword_data.get('volume', 0)
        competition = keyword_data.get('competition', 0.5)
        
        # Analizar fortalezas
        if trend_score > 70:
            insights['strengths'].append("Alta tendencia de búsqueda")
        if volume > 1000:
            insights['strengths'].append("Buen volumen de búsquedas")
        if competition < 0.3:
            insights['strengths'].append("Baja competencia")
        
        # Analizar debilidades
        if trend_score < 20:
            insights['weaknesses'].append("Tendencia de búsqueda baja")
        if volume < 100:
            insights['weaknesses'].append("Volumen limitado")
        if competition > 0.8:
            insights['weaknesses'].append("Alta competencia")
        
        # Generar recomendaciones
        insights['recommendations'] = self._generate_recommendations(keyword_data)
        
        return insights
    
    def _categorize_keyword(self, keyword_data: Dict) -> str:
        """Categoriza una keyword basada en sus métricas"""
        score = keyword_data.get('score', 0)
        
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
    
    def _generate_recommendations(self, keyword_data: Dict) -> List[str]:
        """Genera recomendaciones específicas para una keyword"""
        recommendations = []
        
        trend_score = keyword_data.get('trend_score', 0)
        volume = keyword_data.get('volume', 0)
        competition = keyword_data.get('competition', 0.5)
        keyword = keyword_data.get('keyword', '')
        
        # Recomendaciones basadas en métricas
        if trend_score > 50 and competition < 0.5:
            recommendations.append("Keyword ideal para contenido nuevo - alta tendencia, baja competencia")
        
        if volume > 1000 and competition > 0.7:
            recommendations.append("Considerar variaciones long-tail para reducir competencia")
        
        if len(keyword.split()) < 3:
            recommendations.append("Explorar versiones long-tail más específicas")
        
        if trend_score < 30:
            recommendations.append("Monitorear tendencias estacionales antes de invertir recursos")
        
        if competition > 0.8:
            recommendations.append("Focalizar en contenido de muy alta calidad para competir")
        
        return recommendations[:3]  # Limitar a 3 recomendaciones