"""
Schema definitions for Keyword Finder database models.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class EnhancedKeyword:
    """Enhanced keyword data structure with full metadata."""

    keyword: str
    source: str
    volume: int = 0
    trend_score: float = 0.0
    competition: float = 0.0
    score: float = 0.0
    category: str = ""
    geo: str = ""
    language: str = ""
    intent: str = ""
    cluster_id: int | None = None
    cluster_label: str | None = None
    data_source: str = "heurístico"
    run_id: str | None = None
    data_version: int = 1
    trend_weight: float = 0.4
    volume_weight: float = 0.4
    competition_weight: float = 0.2
    intent_prob: float = 0.0
    last_seen: str | None = None
    updated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            "keyword": self.keyword,
            "source": self.source,
            "volume": self.volume,
            "trend_score": self.trend_score,
            "competition": self.competition,
            "score": self.score,
            "category": self.category,
            "geo": self.geo,
            "language": self.language,
            "intent": self.intent,
            "cluster_id": self.cluster_id,
            "cluster_label": self.cluster_label,
            "data_source": self.data_source,
            "run_id": self.run_id,
            "data_version": self.data_version,
            "trend_weight": self.trend_weight,
            "volume_weight": self.volume_weight,
            "competition_weight": self.competition_weight,
            "intent_prob": self.intent_prob,
            "last_seen": self.last_seen,
            "updated_at": self.updated_at,
        }


@dataclass
class ClusterMetadata:
    """Metadata for keyword clusters."""

    cluster_id: int
    run_id: str
    label: str
    keywords_count: int
    avg_score: float
    avg_volume: int
    dominant_intent: str
    dominant_data_source: str
    created_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            "cluster_id": self.cluster_id,
            "run_id": self.run_id,
            "label": self.label,
            "keywords_count": self.keywords_count,
            "avg_score": self.avg_score,
            "avg_volume": self.avg_volume,
            "dominant_intent": self.dominant_intent,
            "dominant_data_source": self.dominant_data_source,
            "created_at": self.created_at,
        }


@dataclass
class RunMetadata:
    """Metadata for keyword research runs."""

    run_id: str
    started_at: str
    finished_at: str | None = None
    profile: str = "development"
    geo: str = ""
    language: str = ""
    seeds: list[str] | None = None
    config_hash: str | None = None
    keywords_discovered: int = 0
    keywords_filtered: int = 0
    keywords_clustered: int = 0
    clusters_created: int = 0
    duration_seconds: float | None = None
    sources_used: list[str] | None = None

    def __post_init__(self):
        if self.seeds is None:
            self.seeds = []
        if self.sources_used is None:
            self.sources_used = []

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            "run_id": self.run_id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
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
            "sources_used": self.sources_used,
        }
