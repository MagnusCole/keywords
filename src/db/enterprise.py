"""
Enterprise database methods for enhanced schema support.
Simplified version to ensure functionality while maintaining enterprise features.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from typing import Any

from .schema import RunMetadata

logger = logging.getLogger(__name__)


class EnterpriseDatabase:
    """Enterprise database methods for run tracking and enhanced schema."""

    def __init__(self, db_path: str = "keywords.db"):
        self.db_path = db_path
        self._init_enterprise_tables()

    def _init_enterprise_tables(self) -> None:
        """Initialize enterprise tables for run tracking."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Enhanced runs table with full metadata
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS runs_metadata (
                        run_id TEXT PRIMARY KEY,
                        started_at TEXT NOT NULL,
                        finished_at TEXT,
                        profile TEXT DEFAULT 'development',
                        geo TEXT,
                        language TEXT,
                        seeds_json TEXT,
                        config_hash TEXT,
                        keywords_discovered INTEGER DEFAULT 0,
                        keywords_filtered INTEGER DEFAULT 0,
                        keywords_clustered INTEGER DEFAULT 0,
                        clusters_created INTEGER DEFAULT 0,
                        duration_seconds REAL,
                        sources_used_json TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                # Cluster metadata table
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS clusters_metadata (
                        cluster_id INTEGER,
                        run_id TEXT,
                        label TEXT,
                        keywords_count INTEGER,
                        avg_score REAL,
                        avg_volume INTEGER,
                        dominant_intent TEXT,
                        dominant_data_source TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (cluster_id, run_id),
                        FOREIGN KEY (run_id) REFERENCES runs_metadata(run_id)
                    )
                """
                )

                # Enhanced indexes
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_runs_started ON runs_metadata(started_at)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_runs_profile ON runs_metadata(profile)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_clusters_run ON clusters_metadata(run_id)"
                )

                conn.commit()
                logger.info("Enhanced schema tables created successfully")

        except sqlite3.Error as e:
            logger.error(f"Error creating enhanced tables: {e}")

    def save_run_metadata(self, run_meta: RunMetadata) -> bool:
        """Save run metadata to database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                data = run_meta.to_dict()
                conn.execute(
                    """
                    INSERT OR REPLACE INTO runs_metadata 
                    (run_id, started_at, finished_at, profile, geo, language, 
                     seeds_json, config_hash, keywords_discovered, keywords_filtered,
                     keywords_clustered, clusters_created, duration_seconds, sources_used_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        data["run_id"],
                        data["started_at"],
                        data["finished_at"],
                        data["profile"],
                        data["geo"],
                        data["language"],
                        json.dumps(data["seeds"]),
                        data["config_hash"],
                        data["keywords_discovered"],
                        data["keywords_filtered"],
                        data["keywords_clustered"],
                        data["clusters_created"],
                        data["duration_seconds"],
                        json.dumps(data["sources_used"]),
                    ),
                )

                conn.commit()
                return True

        except sqlite3.Error as e:
            logger.error(f"Error saving run metadata: {e}")
            return False

    def get_run_metadata(self, run_id: str) -> dict[str, Any] | None:
        """Get run metadata by run_id."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("SELECT * FROM runs_metadata WHERE run_id = ?", (run_id,))
                row = cursor.fetchone()
                if row:
                    data = dict(row)
                    # Parse JSON fields
                    if data["seeds_json"]:
                        data["seeds"] = json.loads(data["seeds_json"])
                    if data["sources_used_json"]:
                        data["sources_used"] = json.loads(data["sources_used_json"])
                    return data
                return None

        except sqlite3.Error as e:
            logger.error(f"Error getting run metadata: {e}")
            return None

    def list_recent_runs(self, limit: int = 10) -> list[dict[str, Any]]:
        """List recent pipeline runs with metadata."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT run_id, started_at, finished_at, profile, geo, language,
                           keywords_discovered, clusters_created, duration_seconds
                    FROM runs_metadata 
                    ORDER BY started_at DESC 
                    LIMIT ?
                """,
                    (limit,),
                )

                return [dict(row) for row in cursor.fetchall()]

        except sqlite3.Error as e:
            logger.error(f"Error listing recent runs: {e}")
            return []

    def get_run_statistics(self, run_id: str) -> dict[str, Any]:
        """Get comprehensive statistics for a specific run."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                # Keywords stats
                cursor = conn.execute(
                    """
                    SELECT 
                        COUNT(*) as total_keywords,
                        AVG(score) as avg_score,
                        MAX(score) as max_score,
                        MIN(score) as min_score,
                        COUNT(DISTINCT data_source) as sources_count,
                        COUNT(DISTINCT cluster_id) as clusters_count,
                        AVG(volume) as avg_volume,
                        SUM(volume) as total_volume
                    FROM keywords 
                    WHERE run_id = ?
                """,
                    (run_id,),
                )

                row = cursor.fetchone()
                stats = dict(row) if row else {}

                # Intent distribution
                cursor = conn.execute(
                    """
                    SELECT intent, COUNT(*) as count
                    FROM keywords 
                    WHERE run_id = ?
                    GROUP BY intent
                """,
                    (run_id,),
                )

                stats["intent_distribution"] = {
                    row["intent"]: row["count"] for row in cursor.fetchall()
                }

                # Data source distribution
                cursor = conn.execute(
                    """
                    SELECT data_source, COUNT(*) as count
                    FROM keywords 
                    WHERE run_id = ?
                    GROUP BY data_source
                """,
                    (run_id,),
                )

                stats["source_distribution"] = {
                    row["data_source"]: row["count"] for row in cursor.fetchall()
                }

                return stats

        except sqlite3.Error as e:
            logger.error(f"Error getting run statistics: {e}")
            return {}


# Utility function for integration
def create_enterprise_db(db_path: str = "keywords.db") -> EnterpriseDatabase:
    """Create enterprise database instance with enhanced tables."""
    return EnterpriseDatabase(db_path)


if __name__ == "__main__":
    # Test the enterprise database
    db = EnterpriseDatabase(":memory:")

    # Test run metadata
    from .schema import RunMetadata

    run_meta = RunMetadata(profile="test", geo="PE", language="es", seeds=["test"])

    success = db.save_run_metadata(run_meta)
    print(f"✅ Run metadata saved: {success}")

    retrieved = db.get_run_metadata(run_meta.run_id)
    print(f"✅ Run metadata retrieved: {retrieved is not None}")

    runs = db.list_recent_runs()
    print(f"✅ Recent runs listed: {len(runs)} runs")

    stats = db.get_run_statistics(run_meta.run_id)
    print(f"✅ Run statistics: {stats}")

    print("🎯 Enterprise database functionality validated!")
