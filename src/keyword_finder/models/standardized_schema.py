"""
Standardized database schema management for Keyword Finder.
"""

import logging
import sqlite3
from pathlib import Path
from typing import Any


class StandardizedSchema:
    """Manages standardized database schema v2.0.0."""

    SCHEMA_VERSION = "2.0.0"

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)

    def initialize_database(self) -> None:
        """Initialize database with standardized schema."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                self._apply_pragmas(conn)
                self._create_tables(conn)
                self._create_indexes(conn)
                conn.commit()
                self.logger.info(f"Database initialized with schema v{self.SCHEMA_VERSION}")
        except sqlite3.Error as e:
            self.logger.error(f"Error initializing database: {e}")
            raise

    def _apply_pragmas(self, conn: sqlite3.Connection) -> None:
        """Apply SQLite pragmas for better performance."""
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA busy_timeout=5000;")
            conn.execute("PRAGMA foreign_keys=ON;")
        except sqlite3.Error:
            pass  # Best effort

    def _create_tables(self, conn: sqlite3.Connection) -> None:
        """Create standardized tables."""
        # Keywords table with full schema
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT NOT NULL,
                geo TEXT NOT NULL DEFAULT '',
                language TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL,
                volume INTEGER DEFAULT 0,
                trend_score REAL DEFAULT 0.0,
                competition REAL DEFAULT 0.0,
                score REAL DEFAULT 0.0,
                category TEXT DEFAULT '',
                intent TEXT DEFAULT '',
                cluster_id INTEGER,
                cluster_label TEXT,
                data_source TEXT DEFAULT 'heurístico',
                run_id TEXT,
                data_version INTEGER DEFAULT 1,
                trend_weight REAL DEFAULT 0.4,
                volume_weight REAL DEFAULT 0.4,
                competition_weight REAL DEFAULT 0.2,
                intent_prob REAL DEFAULT 0.0,
                last_seen TEXT NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(keyword, geo, language)
            )
        """
        )

        # Runs table for execution tracking
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                geo TEXT,
                language TEXT,
                seeds_json TEXT,
                seeds_count INTEGER,
                keywords_found INTEGER,
                rejected_count INTEGER,
                trend_weight REAL,
                volume_weight REAL,
                competition_weight REAL,
                duration_ms INTEGER
            )
        """
        )

        # Schema version tracking
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_version (
                version TEXT PRIMARY KEY,
                applied_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Record schema version
        conn.execute(
            "INSERT OR IGNORE INTO schema_version (version) VALUES (?)", (self.SCHEMA_VERSION,)
        )

    def _create_indexes(self, conn: sqlite3.Connection) -> None:
        """Create optimized indexes."""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_geo_lang_score ON keywords(geo, language, score DESC)",
            "CREATE INDEX IF NOT EXISTS idx_last_seen ON keywords(last_seen)",
            "CREATE INDEX IF NOT EXISTS idx_source ON keywords(source)",
            "CREATE INDEX IF NOT EXISTS idx_intent ON keywords(intent)",
            "CREATE INDEX IF NOT EXISTS idx_data_source ON keywords(data_source)",
            "CREATE INDEX IF NOT EXISTS idx_score ON keywords(score DESC)",
            "CREATE INDEX IF NOT EXISTS idx_volume ON keywords(volume DESC)",
            "CREATE INDEX IF NOT EXISTS idx_cluster_id ON keywords(cluster_id)",
            "CREATE INDEX IF NOT EXISTS idx_runs_started ON runs(started_at)",
        ]

        for index_sql in indexes:
            conn.execute(index_sql)


def get_schema_info() -> dict[str, Any]:
    """Get information about the current schema."""
    return {
        "version": StandardizedSchema.SCHEMA_VERSION,
        "description": "Standardized schema v2.0.0 with enhanced metadata support",
        "features": [
            "Composite unique constraints",
            "Foreign key relationships",
            "Optimized indexes",
            "Schema versioning",
            "Enhanced metadata tracking",
        ],
    }
