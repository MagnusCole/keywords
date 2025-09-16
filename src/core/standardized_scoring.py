"""
Scoring estandarizado v1 para keyword finder.

Implementa la fórmula congelada según PR-04:
score = norm(relevance)*0.45 + norm(volume)*0.35 + (1-norm(competition))*0.10 + norm(trend)*0.10

Con normalización min-max por mercado (geo, language) y re-ranking opcional por intención.
"""

import logging
import re
import statistics
from dataclasses import asdict, dataclass
from typing import Any

from ..platform.exceptions_enterprise import ScoringError, ValidationError

logger = logging.getLogger(__name__)


@dataclass
class ScoringConfig:
    """Configuración del scoring estandarizado v1."""

    # Pesos de la fórmula congelada (suman 1.0)
    relevance_weight: float = 0.45
    volume_weight: float = 0.35
    competition_weight: float = 0.10
    trend_weight: float = 0.10

    # Intent classifier settings
    intent_enabled: bool = False
    intent_base_multiplier: float = 0.9  # Base multiplier
    intent_boost_factor: float = 0.2  # Additional boost for transactional

    # Validation
    def __post_init__(self):
        """Validate that weights sum to 1.0"""
        total = (
            self.relevance_weight + self.volume_weight + self.competition_weight + self.trend_weight
        )
        if abs(total - 1.0) > 0.001:
            raise ValidationError(f"Scoring weights must sum to 1.0, got {total:.3f}")


@dataclass
class MarketNorms:
    """Normalization parameters for a specific market (geo, language)."""

    geo: str
    language: str

    # Min-max normalization parameters
    relevance_min: float = 0.0
    relevance_max: float = 100.0
    volume_min: float = 0.0
    volume_max: float = 100000.0
    competition_min: float = 0.0
    competition_max: float = 1.0
    trend_min: float = 0.0
    trend_max: float = 100.0

    # Sample size for statistics
    sample_size: int = 0


@dataclass
class ScoringMetadata:
    """Metadata about scoring calculation for transparency."""

    config: ScoringConfig
    market_norms: MarketNorms
    keywords_processed: int
    intent_reranked: int = 0
    run_id: str = ""
    version: str = "v1.0.0"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return {
            "config": asdict(self.config),
            "market_norms": asdict(self.market_norms),
            "keywords_processed": self.keywords_processed,
            "intent_reranked": self.intent_reranked,
            "run_id": self.run_id,
            "version": self.version,
        }


class StandardizedScorer:
    """
    Scoring estandarizado v1 según especificaciones PR-04.

    Características:
    - Fórmula congelada con pesos fijos
    - Normalización min-max por mercado
    - Re-ranking opcional por intención
    - Trazabilidad completa
    """

    def __init__(self, config: ScoringConfig, run_id: str = ""):
        """
        Initialize standardized scorer.

        Args:
            config: Scoring configuration
            run_id: Run identifier for traceability
        """
        self.config = config
        self.run_id = run_id

        # Intent patterns for relevance scoring
        self._transactional_patterns = [
            r"\b(agencia|empresa|consultor|servicio)\b",
            r"\b(contratar|comprar|solicitar)\b",
            r"\b(lima|perú|madrid)\b.*\b(marketing|seo|publicidad)\b",
            r"\bpara (pymes|empresas|negocios)\b",
        ]

        self._commercial_patterns = [
            r"\b(precio|costo|mejor|top|comparar)\b",
            r"\b(curso|clase|diplomado|certificado)\b",
            r"\b(herramientas|software|plataforma)\b",
            r"\b(gratis|barato|oferta)\b",
        ]

        logger.info(f"StandardizedScorer v1.0.0 initialized for run {run_id}")

    def calculate_relevance_score(self, keyword: str) -> float:
        """
        Calculate relevance score based on keyword patterns.

        Returns:
            Relevance score 0-100
        """
        if not keyword:
            return 0.0

        keyword_lower = keyword.lower().strip()
        base_score = 50.0  # Neutral baseline

        # Transactional intent (high relevance)
        for pattern in self._transactional_patterns:
            if re.search(pattern, keyword_lower):
                base_score += 30.0
                break

        # Commercial intent (medium relevance)
        for pattern in self._commercial_patterns:
            if re.search(pattern, keyword_lower):
                base_score += 15.0
                break

        # Length penalty (very long keywords are usually less relevant)
        word_count = len(keyword_lower.split())
        if word_count > 6:
            base_score -= (word_count - 6) * 5.0

        # Quality indicators
        if len(keyword_lower) >= 3:  # Minimum viable length
            base_score += 5.0

        return max(0.0, min(100.0, base_score))

    def calculate_market_norms(
        self, keywords: list[dict[str, Any]], geo: str, language: str
    ) -> MarketNorms:
        """
        Calculate min-max normalization parameters for market.

        Args:
            keywords: List of keywords with raw values
            geo: Geographic market
            language: Language market

        Returns:
            Market normalization parameters
        """
        if not keywords:
            return MarketNorms(geo=geo, language=language)

        # Extract values for normalization
        relevance_values = []
        volume_values = []
        competition_values = []
        trend_values = []

        for kw in keywords:
            # Calculate relevance score for this keyword
            relevance = self.calculate_relevance_score(kw.get("keyword", ""))
            relevance_values.append(relevance)

            # Extract other values
            volume_values.append(float(kw.get("volume", 0)))
            competition_values.append(float(kw.get("competition", 0.5)))
            trend_values.append(float(kw.get("trend_score", 0)))

        # Calculate min-max for each dimension
        norms = MarketNorms(geo=geo, language=language, sample_size=len(keywords))

        if relevance_values:
            norms.relevance_min = min(relevance_values)
            norms.relevance_max = max(relevance_values)

        if volume_values:
            norms.volume_min = min(volume_values)
            norms.volume_max = max(volume_values)

        if competition_values:
            norms.competition_min = min(competition_values)
            norms.competition_max = max(competition_values)

        if trend_values:
            norms.trend_min = min(trend_values)
            norms.trend_max = max(trend_values)

        logger.info(
            f"Market norms calculated for {geo}-{language}: "
            f"relevance={norms.relevance_min:.1f}-{norms.relevance_max:.1f}, "
            f"volume={norms.volume_min:.0f}-{norms.volume_max:.0f}, "
            f"competition={norms.competition_min:.2f}-{norms.competition_max:.2f}, "
            f"trend={norms.trend_min:.1f}-{norms.trend_max:.1f}"
        )

        return norms

    def normalize_value(self, value: float, min_val: float, max_val: float) -> float:
        """
        Apply min-max normalization to a value.

        Returns:
            Normalized value 0-1
        """
        if max_val <= min_val:
            return 0.5  # Neutral if no variation

        normalized = (value - min_val) / (max_val - min_val)
        return max(0.0, min(1.0, normalized))

    def calculate_standardized_score(
        self, keyword_data: dict[str, Any], market_norms: MarketNorms
    ) -> dict[str, Any]:
        """
        Calculate standardized score for a single keyword.

        Args:
            keyword_data: Keyword data with raw values
            market_norms: Market normalization parameters

        Returns:
            Keyword data with standardized score and components
        """
        result = keyword_data.copy()
        keyword = keyword_data.get("keyword", "")

        # Calculate raw relevance score
        relevance_raw = self.calculate_relevance_score(keyword)

        # Extract raw values
        volume_raw = float(keyword_data.get("volume", 0))
        competition_raw = float(keyword_data.get("competition", 0.5))
        trend_raw = float(keyword_data.get("trend_score", 0))

        # Normalize values using market norms
        relevance_norm = self.normalize_value(
            relevance_raw, market_norms.relevance_min, market_norms.relevance_max
        )
        volume_norm = self.normalize_value(
            volume_raw, market_norms.volume_min, market_norms.volume_max
        )
        competition_norm = self.normalize_value(
            competition_raw, market_norms.competition_min, market_norms.competition_max
        )
        trend_norm = self.normalize_value(trend_raw, market_norms.trend_min, market_norms.trend_max)

        # Apply standardized formula (v1.0.0 frozen)
        score = (
            relevance_norm * self.config.relevance_weight
            + volume_norm * self.config.volume_weight
            + (1.0 - competition_norm)
            * self.config.competition_weight  # Invert competition (lower is better)
            + trend_norm * self.config.trend_weight
        )

        # Convert to 0-100 scale
        score_100 = score * 100.0

        # Store components for transparency
        result.update(
            {
                "score": round(score_100, 2),
                "relevance_raw": relevance_raw,
                "relevance_norm": relevance_norm,
                "volume_norm": volume_norm,
                "competition_norm": competition_norm,
                "trend_norm": trend_norm,
                "scoring_version": "v1.0.0",
            }
        )

        return result

    def apply_intent_reranking(
        self, keywords: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], int]:
        """
        Apply intent-based re-ranking if enabled.

        Args:
            keywords: Keywords with standardized scores

        Returns:
            (Reranked keywords, count of reranked keywords)
        """
        if not self.config.intent_enabled:
            return keywords, 0

        reranked_count = 0
        result = []

        for kw in keywords:
            kw_copy = kw.copy()

            # Get intent probability (if available)
            intent_prob = kw.get("intent_prob_transactional", 0.0)

            if intent_prob > 0.0:
                # Apply re-ranking formula
                original_score = kw.get("score", 0.0)
                multiplier = self.config.intent_base_multiplier + (
                    self.config.intent_boost_factor * intent_prob
                )
                new_score = original_score * multiplier

                kw_copy["score"] = round(new_score, 2)
                kw_copy["intent_multiplier"] = round(multiplier, 3)
                kw_copy["score_before_intent"] = original_score

                reranked_count += 1

            result.append(kw_copy)

        # Re-sort by new scores
        result.sort(key=lambda x: x.get("score", 0), reverse=True)

        if reranked_count > 0:
            logger.info(f"Intent re-ranking applied to {reranked_count} keywords")

        return result, reranked_count

    def score_batch(
        self, keywords: list[dict[str, Any]], geo: str, language: str
    ) -> tuple[list[dict[str, Any]], ScoringMetadata]:
        """
        Score a batch of keywords with full standardized process.

        Args:
            keywords: List of keyword data
            geo: Geographic market
            language: Language market

        Returns:
            (Scored keywords, scoring metadata)
        """
        if not keywords:
            return [], ScoringMetadata(
                config=self.config,
                market_norms=MarketNorms(geo=geo, language=language),
                keywords_processed=0,
                run_id=self.run_id,
            )

        logger.info(
            f"Starting standardized scoring for {len(keywords)} keywords in {geo}-{language}"
        )

        try:
            # 1. Calculate market normalization parameters
            market_norms = self.calculate_market_norms(keywords, geo, language)

            # 2. Calculate standardized scores
            scored_keywords = []
            for kw in keywords:
                scored_kw = self.calculate_standardized_score(kw, market_norms)
                scored_keywords.append(scored_kw)

            # 3. Apply intent re-ranking if enabled
            final_keywords, reranked_count = self.apply_intent_reranking(scored_keywords)

            # 4. Final sort by score
            final_keywords.sort(key=lambda x: x.get("score", 0), reverse=True)

            # 5. Create metadata
            metadata = ScoringMetadata(
                config=self.config,
                market_norms=market_norms,
                keywords_processed=len(keywords),
                intent_reranked=reranked_count,
                run_id=self.run_id,
            )

            score_stats = [kw.get("score", 0) for kw in final_keywords]
            logger.info(
                f"Standardized scoring complete: "
                f"avg={statistics.mean(score_stats):.1f}, "
                f"max={max(score_stats):.1f}, "
                f"min={min(score_stats):.1f}"
            )

            return final_keywords, metadata

        except Exception as e:
            logger.error(f"Error in standardized scoring: {e}")
            # Use ScoringError which is more specific for this operation
            keywords_count = len(keywords) if keywords else 0
            raise ScoringError(
                message=f"Scoring failed: {e}",
                keywords_count=keywords_count,
                algorithm="standardized_scoring",
            ) from e


def create_scoring_config_from_yaml(config_dict: dict[str, Any]) -> ScoringConfig:
    """
    Create ScoringConfig from YAML configuration.

    Args:
        config_dict: Configuration dictionary from YAML

    Returns:
        ScoringConfig instance
    """
    scoring_config = config_dict.get("scoring", {})
    weights = scoring_config.get("weights", {})

    # Extract weights with defaults matching PR-04 spec
    relevance_weight = weights.get("relevance", 0.45)
    volume_weight = weights.get("volume", 0.35)
    competition_weight = weights.get("competition", 0.10)
    trend_weight = weights.get("trend", 0.10)

    # Intent classifier settings
    intent_config = config_dict.get("ml", {}).get("intent_classifier", {})
    intent_enabled = intent_config.get("enabled", False)

    return ScoringConfig(
        relevance_weight=relevance_weight,
        volume_weight=volume_weight,
        competition_weight=competition_weight,
        trend_weight=trend_weight,
        intent_enabled=intent_enabled,
    )
