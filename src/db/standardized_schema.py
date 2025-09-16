"""
Standardized database schema definitions for keyword-finder.

This module provides enterprise-grade database schema with:
- Proper PRIMARY KEY and FOREIGN KEY constraints
- Optimized indexes for common queries
- UNIQUE constraints to prevent duplicates
- Standardized column names and types
- Full audit trail with timestamps
- Data integrity validation

Schema Version: 2.0.0 (Production Ready)
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List, Optional

import logging

# Standard table definitions with proper constraints and indexes
SCHEMA_DEFINITIONS = {
    "runs": """
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            finished_at TEXT NULL,
            profile TEXT NOT NULL DEFAULT 'development',
            geo TEXT NOT NULL DEFAULT '',
            language TEXT NOT NULL DEFAULT 'en',
            seeds TEXT NOT NULL DEFAULT '[]',  -- JSON array
            total_keywords INTEGER DEFAULT 0,
            total_clusters INTEGER DEFAULT 0,
            processing_time_seconds REAL DEFAULT 0.0,
            config_snapshot TEXT NULL,  -- JSON of config used
            status TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed', 'cancelled')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """,
    
    "keywords": """
        CREATE TABLE IF NOT EXISTS keywords (
            keyword_id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT NOT NULL,
            source TEXT NOT NULL CHECK (source IN ('seed', 'expansion', 'manual')),
            volume INTEGER DEFAULT 0,
            trend_score REAL DEFAULT 0.0,
            competition REAL DEFAULT 0.0,
            score REAL DEFAULT 0.0,
            category TEXT DEFAULT '',
            intent TEXT DEFAULT 'unknown' CHECK (intent IN ('informational', 'transactional', 'navigational', 'commercial', 'unknown')),
            intent_confidence REAL DEFAULT 0.0,
            cluster_id INTEGER NULL,
            cluster_label TEXT DEFAULT '',
            geo TEXT NOT NULL DEFAULT '',
            language TEXT NOT NULL DEFAULT 'en',
            data_source TEXT NOT NULL DEFAULT 'heuristic' CHECK (data_source IN ('ads_volume', 'trends', 'heuristic', 'manual')),
            run_id TEXT NOT NULL,
            data_version INTEGER NOT NULL DEFAULT 2,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            
            -- Composite UNIQUE constraint to prevent duplicates within a run
            UNIQUE(keyword, geo, language, run_id),
            
            -- Foreign key to runs table
            FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
        )
    """,
    
    "clusters": """
        CREATE TABLE IF NOT EXISTS clusters (
            cluster_id INTEGER PRIMARY KEY AUTOINCREMENT,
            cluster_label TEXT NOT NULL,
            run_id TEXT NOT NULL,
            keywords_count INTEGER DEFAULT 0,
            avg_score REAL DEFAULT 0.0,
            avg_volume REAL DEFAULT 0.0,
            dominant_intent TEXT DEFAULT 'unknown' CHECK (dominant_intent IN ('informational', 'transactional', 'navigational', 'commercial', 'unknown')),
            dominant_data_source TEXT DEFAULT 'heuristic' CHECK (dominant_data_source IN ('ads_volume', 'trends', 'heuristic', 'manual')),
            algorithm_used TEXT DEFAULT 'kmeans' CHECK (algorithm_used IN ('hdbscan', 'kmeans', 'manual')),
            algorithm_params TEXT NULL,  -- JSON of parameters used
            silhouette_score REAL DEFAULT 0.0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            
            -- Unique cluster per run
            UNIQUE(cluster_label, run_id),
            
            -- Foreign key to runs table
            FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
        )
    """,
    
    "exports": """
        CREATE TABLE IF NOT EXISTS exports (
            export_id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            export_type TEXT NOT NULL DEFAULT 'csv' CHECK (export_type IN ('csv', 'json', 'excel')),
            filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            records_count INTEGER DEFAULT 0,
            file_size_bytes INTEGER DEFAULT 0,
            export_config TEXT NULL,  -- JSON of export parameters
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            
            -- Foreign key to runs table
            FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
        )
    """
}

# Optimized indexes for common query patterns
INDEX_DEFINITIONS = [
    # Performance indexes for keywords table
    "CREATE INDEX IF NOT EXISTS idx_keywords_run_id ON keywords(run_id)",
    "CREATE INDEX IF NOT EXISTS idx_keywords_geo_lang ON keywords(geo, language)",
    "CREATE INDEX IF NOT EXISTS idx_keywords_score_desc ON keywords(score DESC)",
    "CREATE INDEX IF NOT EXISTS idx_keywords_volume_desc ON keywords(volume DESC)",
    "CREATE INDEX IF NOT EXISTS idx_keywords_cluster ON keywords(cluster_id) WHERE cluster_id IS NOT NULL",
    "CREATE INDEX IF NOT EXISTS idx_keywords_intent ON keywords(intent)",
    "CREATE INDEX IF NOT EXISTS idx_keywords_source ON keywords(source)",
    "CREATE INDEX IF NOT EXISTS idx_keywords_data_source ON keywords(data_source)",
    
    # Compound indexes for common filtering patterns
    "CREATE INDEX IF NOT EXISTS idx_keywords_geo_lang_score ON keywords(geo, language, score DESC)",
    "CREATE INDEX IF NOT EXISTS idx_keywords_run_intent ON keywords(run_id, intent)",
    "CREATE INDEX IF NOT EXISTS idx_keywords_run_cluster ON keywords(run_id, cluster_id)",
    
    # Performance indexes for runs table
    "CREATE INDEX IF NOT EXISTS idx_runs_profile ON runs(profile)",
    "CREATE INDEX IF NOT EXISTS idx_runs_geo_lang ON runs(geo, language)",
    "CREATE INDEX IF NOT EXISTS idx_runs_started_at ON runs(started_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status)",
    
    # Performance indexes for clusters table
    "CREATE INDEX IF NOT EXISTS idx_clusters_run_id ON clusters(run_id)",
    "CREATE INDEX IF NOT EXISTS idx_clusters_algorithm ON clusters(algorithm_used)",
    "CREATE INDEX IF NOT EXISTS idx_clusters_score_desc ON clusters(avg_score DESC)",
    
    # Performance indexes for exports table
    "CREATE INDEX IF NOT EXISTS idx_exports_run_id ON exports(run_id)",
    "CREATE INDEX IF NOT EXISTS idx_exports_type ON exports(export_type)",
    "CREATE INDEX IF NOT EXISTS idx_exports_created_at ON exports(created_at DESC)",
]

# Database schema validation queries
VALIDATION_QUERIES = [
    "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('runs', 'keywords', 'clusters', 'exports')",
    "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'",
    "PRAGMA table_info(keywords)",
    "PRAGMA foreign_key_list(keywords)",
    "PRAGMA index_list(keywords)",
]


class StandardizedSchema:
    """Manages standardized database schema creation and migration."""
    
    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self.schema_version = "2.0.0"
        
    def initialize_database(self) -> None:
        """Initialize database with standardized schema."""
        logging.info(f"Initializing standardized database schema v{self.schema_version}")
        
        with sqlite3.connect(self.db_path) as conn:
            # Enable foreign key constraints
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Apply performance pragmas
            self._apply_pragmas(conn)
            
            # Create all tables
            self._create_tables(conn)
            
            # Create all indexes
            self._create_indexes(conn)
            
            # Validate schema
            self._validate_schema(conn)
            
            logging.info("Standardized database schema initialized successfully")
    
    def _apply_pragmas(self, conn: sqlite3.Connection) -> None:
        """Apply SQLite pragmas for optimal performance."""
        pragmas = [
            "PRAGMA journal_mode=WAL",
            "PRAGMA synchronous=NORMAL", 
            "PRAGMA busy_timeout=5000",
            "PRAGMA cache_size=-64000",  # 64MB cache
            "PRAGMA temp_store=MEMORY",
            "PRAGMA mmap_size=268435456",  # 256MB mmap
            "PRAGMA optimize"
        ]
        
        for pragma in pragmas:
            try:
                conn.execute(pragma)
            except sqlite3.Error as e:
                logging.warning(f"Failed to apply pragma '{pragma}': {e}")
    
    def _create_tables(self, conn: sqlite3.Connection) -> None:
        """Create all standardized tables."""
        for table_name, table_sql in SCHEMA_DEFINITIONS.items():
            try:
                conn.execute(table_sql)
                logging.debug(f"Created table: {table_name}")
            except sqlite3.Error as e:
                logging.error(f"Failed to create table {table_name}: {e}")
                raise
    
    def _create_indexes(self, conn: sqlite3.Connection) -> None:
        """Create all performance indexes."""
        for index_sql in INDEX_DEFINITIONS:
            try:
                conn.execute(index_sql)
            except sqlite3.Error as e:
                logging.warning(f"Failed to create index: {e}")
    
    def _validate_schema(self, conn: sqlite3.Connection) -> None:
        """Validate that schema was created correctly."""
        try:
            # Check all required tables exist
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('runs', 'keywords', 'clusters', 'exports')"
            )
            tables = {row[0] for row in cursor.fetchall()}
            required_tables = {"runs", "keywords", "clusters", "exports"}
            
            if tables != required_tables:
                missing = required_tables - tables
                raise ValueError(f"Missing required tables: {missing}")
            
            # Check foreign key constraints are enabled
            cursor = conn.execute("PRAGMA foreign_keys")
            fk_enabled = cursor.fetchone()[0]
            if not fk_enabled:
                logging.warning("Foreign key constraints are not enabled")
            
            # Check indexes exist
            cursor = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'")
            index_count = cursor.fetchone()[0]
            if index_count < 10:  # We expect at least 10 indexes
                logging.warning(f"Only {index_count} indexes found, expected more for optimal performance")
            
            logging.info(f"Schema validation passed: {len(tables)} tables, {index_count} indexes")
            
        except sqlite3.Error as e:
            logging.error(f"Schema validation failed: {e}")
            raise


def get_schema_info(db_path: Path | str) -> dict:
    """Get comprehensive schema information for debugging."""
    info = {
        "tables": {},
        "indexes": [],
        "foreign_keys": {},
        "pragmas": {}
    }
    
    with sqlite3.connect(db_path) as conn:
        # Get table info
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        for (table_name,) in cursor.fetchall():
            cursor2 = conn.execute(f"PRAGMA table_info({table_name})")
            info["tables"][table_name] = cursor2.fetchall()
        
        # Get index info
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'")
        info["indexes"] = [row[0] for row in cursor.fetchall()]
        
        # Get foreign key info
        for table in info["tables"]:
            cursor = conn.execute(f"PRAGMA foreign_key_list({table})")
            fks = cursor.fetchall()
            if fks:
                info["foreign_keys"][table] = fks
        
        # Get pragma info
        pragmas_to_check = ["foreign_keys", "journal_mode", "synchronous", "cache_size"]
        for pragma in pragmas_to_check:
            try:
                cursor = conn.execute(f"PRAGMA {pragma}")
                info["pragmas"][pragma] = cursor.fetchone()[0]
            except sqlite3.Error:
                info["pragmas"][pragma] = "unknown"
    
    return info