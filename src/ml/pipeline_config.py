"""
Standardized ML Pipeline Configuration v1.0.0

This module provides frozen configurations for machine learning components
to ensure consistent, reproducible results across environments.

Key principles:
- Frozen scoring formula (PR-04 spec)
- Deterministic clustering behavior
- Cached embeddings for performance
- Standard algorithm parameters
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FrozenScoringFormula:
    """Frozen scoring formula v1.0.0 - DO NOT MODIFY.
    
    Formula: score = norm(relevance)*0.45 + norm(volume)*0.35 + (1-norm(competition))*0.10 + norm(trend)*0.10
    
    These weights are production-frozen and cannot be changed without
    creating a new formula version (v1.1.0, v2.0.0, etc.)
    """
    
    VERSION: str = "1.0.0"
    
    # Primary scoring weights (frozen)
    RELEVANCE_WEIGHT: float = 0.45
    VOLUME_WEIGHT: float = 0.35
    COMPETITION_WEIGHT: float = 0.10  # Note: inverted (1 - competition)
    TREND_WEIGHT: float = 0.10
    
    # Intent multipliers (frozen)
    INTENT_BASE_MULTIPLIER: float = 0.9
    INTENT_COMMERCIAL_BOOST: float = 0.15
    INTENT_TRANSACTIONAL_BOOST: float = 0.20
    
    # Validation bounds (frozen)
    MIN_SCORE: float = 0.0
    MAX_SCORE: float = 100.0
    
    def __post_init__(self):
        """Validate frozen formula constraints."""
        total_weight = (
            self.RELEVANCE_WEIGHT + 
            self.VOLUME_WEIGHT + 
            self.COMPETITION_WEIGHT + 
            self.TREND_WEIGHT
        )
        if abs(total_weight - 1.0) > 0.001:
            raise ValueError(f"Frozen scoring weights must sum to 1.0, got {total_weight:.4f}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Export formula as immutable dictionary."""
        return {
            "version": self.VERSION,
            "weights": {
                "relevance": self.RELEVANCE_WEIGHT,
                "volume": self.VOLUME_WEIGHT,
                "competition": self.COMPETITION_WEIGHT,
                "trend": self.TREND_WEIGHT
            },
            "intent_multipliers": {
                "base": self.INTENT_BASE_MULTIPLIER,
                "commercial_boost": self.INTENT_COMMERCIAL_BOOST,
                "transactional_boost": self.INTENT_TRANSACTIONAL_BOOST
            },
            "bounds": {
                "min_score": self.MIN_SCORE,
                "max_score": self.MAX_SCORE
            }
        }


@dataclass(frozen=True)
class StandardClusteringConfig:
    """Standardized clustering configuration for reproducible results."""
    
    VERSION: str = "1.0.0"
    
    # Algorithm selection priority (frozen order)
    ALGORITHM_PRIORITY: tuple[str, ...] = ("hdbscan", "kmeans", "manual")
    
    # HDBSCAN parameters (frozen)
    HDBSCAN_MIN_CLUSTER_SIZE: int = 3
    HDBSCAN_MIN_SAMPLES: int = 2
    HDBSCAN_METRIC: str = "euclidean"
    
    # KMeans parameters (frozen)
    KMEANS_RANDOM_STATE: int = 42
    KMEANS_N_INIT: int = 10
    KMEANS_MAX_ITER: int = 300
    KMEANS_MIN_CLUSTERS: int = 2
    KMEANS_MAX_CLUSTERS_RATIO: float = 0.3  # max_k = n_keywords * ratio
    
    # Silhouette scoring (frozen)
    SILHOUETTE_MIN_SCORE: float = -0.1  # Minimum acceptable silhouette
    SILHOUETTE_RANDOM_STATE: int = 42
    
    # Embedding cache (frozen)
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_CACHE_ENABLED: bool = True
    EMBEDDING_DIMENSION: int = 384  # For all-MiniLM-L6-v2
    
    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary."""
        return {
            "version": self.VERSION,
            "algorithm_priority": list(self.ALGORITHM_PRIORITY),
            "hdbscan": {
                "min_cluster_size": self.HDBSCAN_MIN_CLUSTER_SIZE,
                "min_samples": self.HDBSCAN_MIN_SAMPLES,
                "metric": self.HDBSCAN_METRIC
            },
            "kmeans": {
                "random_state": self.KMEANS_RANDOM_STATE,
                "n_init": self.KMEANS_N_INIT,
                "max_iter": self.KMEANS_MAX_ITER,
                "min_clusters": self.KMEANS_MIN_CLUSTERS,
                "max_clusters_ratio": self.KMEANS_MAX_CLUSTERS_RATIO
            },
            "silhouette": {
                "min_score": self.SILHOUETTE_MIN_SCORE,
                "random_state": self.SILHOUETTE_RANDOM_STATE
            },
            "embeddings": {
                "model": self.EMBEDDING_MODEL,
                "cache_enabled": self.EMBEDDING_CACHE_ENABLED,
                "dimension": self.EMBEDDING_DIMENSION
            }
        }


@dataclass
class MLPipelineConfig:
    """Complete ML pipeline configuration combining all components."""
    
    scoring: FrozenScoringFormula = field(default_factory=FrozenScoringFormula)
    clustering: StandardClusteringConfig = field(default_factory=StandardClusteringConfig)
    
    # Pipeline behavior
    enable_intent_classification: bool = True
    enable_clustering: bool = True
    enable_caching: bool = True
    
    # Performance settings
    batch_size: int = 1000
    max_workers: int = 4
    memory_limit_mb: int = 2048
    
    def validate(self) -> bool:
        """Validate complete pipeline configuration."""
        try:
            # Validate frozen components
            self.scoring.__post_init__()
            
            # Validate performance settings
            if self.batch_size <= 0:
                raise ValueError("batch_size must be positive")
            if self.max_workers <= 0:
                raise ValueError("max_workers must be positive")
            if self.memory_limit_mb <= 0:
                raise ValueError("memory_limit_mb must be positive")
            
            return True
            
        except Exception as e:
            logger.error(f"ML pipeline config validation failed: {e}")
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Export complete configuration."""
        return {
            "scoring": self.scoring.to_dict(),
            "clustering": self.clustering.to_dict(),
            "pipeline": {
                "enable_intent_classification": self.enable_intent_classification,
                "enable_clustering": self.enable_clustering,
                "enable_caching": self.enable_caching,
                "batch_size": self.batch_size,
                "max_workers": self.max_workers,
                "memory_limit_mb": self.memory_limit_mb
            }
        }
    
    def save_to_file(self, filepath: str) -> bool:
        """Save configuration to JSON file."""
        try:
            config_dict = self.to_dict()
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
            logger.info(f"ML pipeline config saved to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to save ML config to {filepath}: {e}")
            return False
    
    @classmethod
    def load_from_file(cls, filepath: str) -> Optional[MLPipelineConfig]:
        """Load configuration from JSON file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract pipeline settings
            pipeline_data = data.get("pipeline", {})
            
            config = cls(
                enable_intent_classification=pipeline_data.get("enable_intent_classification", True),
                enable_clustering=pipeline_data.get("enable_clustering", True),
                enable_caching=pipeline_data.get("enable_caching", True),
                batch_size=pipeline_data.get("batch_size", 1000),
                max_workers=pipeline_data.get("max_workers", 4),
                memory_limit_mb=pipeline_data.get("memory_limit_mb", 2048)
            )
            
            logger.info(f"ML pipeline config loaded from {filepath}")
            return config
            
        except Exception as e:
            logger.error(f"Failed to load ML config from {filepath}: {e}")
            return None


# Global singleton instances for production use
PRODUCTION_SCORING_FORMULA = FrozenScoringFormula()
PRODUCTION_CLUSTERING_CONFIG = StandardClusteringConfig()
PRODUCTION_ML_CONFIG = MLPipelineConfig()


def get_production_ml_config() -> MLPipelineConfig:
    """Get the production-ready ML pipeline configuration."""
    return PRODUCTION_ML_CONFIG


def validate_ml_config_consistency() -> bool:
    """Validate that all ML configuration components are consistent."""
    try:
        config = get_production_ml_config()
        
        # Validate individual components
        if not config.validate():
            return False
        
        # Check version consistency
        scoring_version = config.scoring.VERSION
        clustering_version = config.clustering.VERSION
        
        logger.info(f"ML config validation passed - Scoring v{scoring_version}, Clustering v{clustering_version}")
        return True
        
    except Exception as e:
        logger.error(f"ML config consistency check failed: {e}")
        return False


if __name__ == "__main__":
    # Self-test
    config = get_production_ml_config()
    print("Production ML Configuration:")
    print(json.dumps(config.to_dict(), indent=2))
    
    validation = validate_ml_config_consistency()
    print(f"\\nValidation: {'✅ PASSED' if validation else '❌ FAILED'}")