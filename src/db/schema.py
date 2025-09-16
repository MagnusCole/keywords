"""
Enhanced data schema with full traceability and run tracking.

This module provides enterprise-grade data schema with:
- Complete run traceability with run_id 
- Data source tracking (ads, trends, heuristic)
- Intent classification with confidence scores
- Clustering information
- Data versioning for schema evolution
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class DataSource(Enum):
    """Data source types for keyword information."""

    ADS_VOLUME = "ads_volume"
    TRENDS = "trends"
    HEURISTIC = "heuristic"
    MANUAL = "manual"


class IntentType(Enum):
    """Keyword intent classification types."""

    INFORMATIONAL = "informational"
    TRANSACTIONAL = "transactional"
    NAVIGATIONAL = "navigational"
    COMMERCIAL = "commercial"
    UNKNOWN = "unknown"


@dataclass
class RunMetadata:
    """Metadata for a complete pipeline run."""

    run_id: str = field(
        default_factory=lambda: f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    )
    started_at: datetime = field(default_factory=datetime.now)
    finished_at: datetime | None = None
    profile: str = "development"
    geo: str = ""
    language: str = ""
    seeds: list[str] = field(default_factory=list)
    config_hash: str | None = None  # Hash of config for reproducibility

    # Pipeline statistics
    keywords_discovered: int = 0
    keywords_filtered: int = 0
    keywords_clustered: int = 0
    clusters_created: int = 0

    # Timing information
    duration_seconds: float | None = None

    # Data source usage
    sources_used: list[DataSource] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "run_id": self.run_id,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "profile": self.profile,
            "geo": self.geo,
            "language": self.language,
            "seeds": self.seeds,
            "config_hash": self.config_hash,
            "keywords_discovered": self.keywords_discovered,
            "keywords_filtered": self.keywords_filtered,
            "keywords_clustered": self.keywords_clustered,
            "clusters_created": self.clusters_created,
            "duration_seconds": self.duration_seconds,
            "sources_used": [s.value for s in self.sources_used],
        }


@dataclass
class EnhancedKeyword:
    """Enhanced keyword data structure with full traceability."""

    # Core keyword data
    keyword: str
    source: str  # Where this specific keyword came from (e.g., "expansion", "seed")

    # Scoring components
    volume: int = 0
    trend_score: float = 0.0
    competition: float = 0.0
    score: float = 0.0

    # Classification
    category: str = ""
    intent: IntentType = IntentType.UNKNOWN
    intent_prob: float = 0.0  # Confidence score for intent classification

    # Clustering information
    cluster_id: int | None = None
    cluster_label: str | None = None

    # Geographic and language context
    geo: str = ""
    language: str = ""

    # Data provenance - ENTERPRISE TRACEABILITY
    data_source: DataSource = DataSource.HEURISTIC  # Primary data source
    run_id: str = ""  # Which pipeline run generated this
    data_version: int = 1  # Schema version for migration handling

    # Scoring weights (for reproducibility)
    trend_weight: float = 0.4
    volume_weight: float = 0.4
    competition_weight: float = 0.2

    # Temporal tracking
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage and export."""
        return {
            "keyword": self.keyword,
            "source": self.source,
            "volume": self.volume,
            "trend_score": self.trend_score,
            "competition": self.competition,
            "score": self.score,
            "category": self.category,
            "intent": self.intent.value,
            "intent_prob": self.intent_prob,
            "cluster_id": self.cluster_id,
            "cluster_label": self.cluster_label,
            "geo": self.geo,
            "language": self.language,
            "data_source": self.data_source.value,
            "run_id": self.run_id,
            "data_version": self.data_version,
            "trend_weight": self.trend_weight,
            "volume_weight": self.volume_weight,
            "competition_weight": self.competition_weight,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_seen": self.last_seen.isoformat(),
        }

    @classmethod
    def from_legacy_keyword(cls, keyword_dict: dict[str, Any], run_id: str = "") -> EnhancedKeyword:
        """Convert from legacy keyword format to enhanced format."""
        intent = IntentType.UNKNOWN
        if "intent" in keyword_dict and keyword_dict["intent"]:
            try:
                intent = IntentType(keyword_dict["intent"])
            except ValueError:
                intent = IntentType.UNKNOWN

        data_source = DataSource.HEURISTIC
        if "data_source" in keyword_dict and keyword_dict["data_source"]:
            try:
                data_source = DataSource(keyword_dict["data_source"])
            except ValueError:
                data_source = DataSource.HEURISTIC

        return cls(
            keyword=keyword_dict.get("keyword", ""),
            source=keyword_dict.get("source", ""),
            volume=keyword_dict.get("volume", 0),
            trend_score=keyword_dict.get("trend_score", 0.0),
            competition=keyword_dict.get("competition", 0.0),
            score=keyword_dict.get("score", 0.0),
            category=keyword_dict.get("category", ""),
            intent=intent,
            intent_prob=keyword_dict.get("intent_prob", 0.0),
            cluster_id=keyword_dict.get("cluster_id"),
            cluster_label=keyword_dict.get("cluster_label"),
            geo=keyword_dict.get("geo", ""),
            language=keyword_dict.get("language", ""),
            data_source=data_source,
            run_id=run_id or keyword_dict.get("run_id", ""),
            data_version=keyword_dict.get("data_version", 1),
            trend_weight=keyword_dict.get("trend_weight", 0.4),
            volume_weight=keyword_dict.get("volume_weight", 0.4),
            competition_weight=keyword_dict.get("competition_weight", 0.2),
        )


@dataclass
class ClusterMetadata:
    """Metadata for keyword clusters."""

    cluster_id: int
    label: str
    run_id: str
    keywords_count: int
    avg_score: float
    avg_volume: int
    dominant_intent: IntentType
    dominant_data_source: DataSource
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "cluster_id": self.cluster_id,
            "label": self.label,
            "run_id": self.run_id,
            "keywords_count": self.keywords_count,
            "avg_score": self.avg_score,
            "avg_volume": self.avg_volume,
            "dominant_intent": self.dominant_intent.value,
            "dominant_data_source": self.dominant_data_source.value,
            "created_at": self.created_at.isoformat(),
        }


def generate_run_id(profile: str = "dev") -> str:
    """Generate a unique run ID with timestamp and profile."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    return f"{profile}_{timestamp}_{unique_id}"


def create_run_metadata(config: dict[str, Any]) -> RunMetadata:
    """Create run metadata from configuration."""
    return RunMetadata(
        profile=config.get("project", {}).get("environment", "development"),
        geo=config.get("run", {}).get("geo", ""),
        language=config.get("run", {}).get("language", ""),
        seeds=config.get("run", {}).get("seeds", []),
    )


# Export standardized column order for CSV outputs
STANDARD_CSV_COLUMNS = [
    "keyword",
    "score",
    "volume",
    "trend_score",
    "competition",
    "intent",
    "intent_prob",
    "cluster_id",
    "cluster_label",
    "category",
    "source",
    "data_source",
    "geo",
    "language",
    "run_id",
    "data_version",
    "created_at",
    "updated_at",
]


if __name__ == "__main__":
    # Test the enhanced schema
    run_meta = RunMetadata(profile="test", geo="PE", language="es", seeds=["marketing"])
    print(f"Generated run ID: {run_meta.run_id}")

    keyword = EnhancedKeyword(
        keyword="marketing digital",
        source="expansion",
        volume=1000,
        intent=IntentType.INFORMATIONAL,
        intent_prob=0.85,
        data_source=DataSource.TRENDS,
        run_id=run_meta.run_id,
    )

    print(f"Enhanced keyword: {keyword.keyword}")
    print(f"Data dict: {keyword.to_dict()}")
    print(f"Standard columns: {STANDARD_CSV_COLUMNS}")
