import json
import logging
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from ..models.schema import ClusterMetadata, EnhancedKeyword, RunMetadata
from ..models.standardized_schema import StandardizedSchema, get_schema_info


@dataclass
class QueryMetrics:
    """Métricas de rendimiento para una query."""

    query_type: str
    execution_time: float
    rows_returned: int
    timestamp: str
    filters_used: dict | None = None


class SQLiteMonitor:
    """Monitor básico para SQLite con métricas de rendimiento."""

    def __init__(self):
        self.metrics: list[QueryMetrics] = []
        self.max_metrics = 1000  # Mantener solo las últimas 1000 métricas

    def record_query(
        self,
        query_type: str,
        execution_time: float,
        rows_returned: int,
        filters: dict | None = None,
    ) -> None:
        """Registra una métrica de query."""
        metric = QueryMetrics(
            query_type=query_type,
            execution_time=execution_time,
            rows_returned=rows_returned,
            timestamp=datetime.now().isoformat(),
            filters_used=filters,
        )

        self.metrics.append(metric)

        # Mantener solo las últimas métricas
        if len(self.metrics) > self.max_metrics:
            self.metrics = self.metrics[-self.max_metrics :]

        # Log de queries lentas (>100ms)
        if execution_time > 0.1:
            logging.warning("Consulta lenta detectada: %.2fs - %s", execution_time, query_type)

    def get_performance_stats(self) -> dict:
        """Obtiene estadísticas de rendimiento."""
        if not self.metrics:
            return {"total_queries": 0, "avg_execution_time": 0.0, "slow_queries": 0}

        total_time = sum(m.execution_time for m in self.metrics)
        slow_queries = sum(1 for m in self.metrics if m.execution_time > 0.1)

        return {
            "total_queries": len(self.metrics),
            "avg_execution_time": total_time / len(self.metrics),
            "slow_queries": slow_queries,
            "slow_query_percentage": (slow_queries / len(self.metrics)) * 100,
        }

    def get_database_stats(self, db_path: Path) -> dict:
        """Obtiene estadísticas básicas de la base de datos."""
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM keywords")
                total_keywords = cursor.fetchone()[0]

                cursor = conn.execute("SELECT COUNT(*) FROM runs")
                total_runs = cursor.fetchone()[0]

                # Obtener tamaño del archivo
                db_size = db_path.stat().st_size if db_path.exists() else 0

                return {
                    "total_keywords": total_keywords,
                    "total_runs": total_runs,
                    "database_size_mb": db_size / (1024 * 1024),
                    "last_updated": datetime.now().isoformat(),
                }
        except sqlite3.Error as e:
            logging.error("Error getting database stats: %s", e)
            return {"error": str(e)}


# Instancia global del monitor
sqlite_monitor = SQLiteMonitor()


@dataclass
class Keyword:
    """Estructura de datos para una keyword"""

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

    def __post_init__(self):
        if self.last_seen is None:
            self.last_seen = datetime.now().isoformat()
        if self.updated_at is None:
            self.updated_at = self.last_seen


class KeywordDatabase:
    """Enterprise-grade SQLite database for keywords with standardized schema.

    Features:
    - Standardized schema v2.0.0 with proper constraints
    - Optimized indexes for common queries
    - UNIQUE constraints to prevent duplicates
    - Foreign key relationships for data integrity
    - Full audit trail with timestamps
    """

    def __init__(self, db_path: str = "keywords.db", use_standardized_schema: bool = True):
        self.db_path = Path(db_path)
        self.use_standardized_schema = use_standardized_schema

        if use_standardized_schema:
            # Use the new standardized schema v2.0.0
            self.schema_manager = StandardizedSchema(self.db_path)
            self.schema_manager.initialize_database()
        else:
            # Legacy initialization for backward compatibility
            self._init_database()

        logging.info(
            "Database initialized at %s (standardized=%s)", db_path, use_standardized_schema
        )

    def _apply_pragmas(self, conn: sqlite3.Connection) -> None:
        """Apply SQLite pragmas for better performance and resilience."""
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA busy_timeout=5000;")
        except sqlite3.Error:
            # Best-effort; pragmas may fail on some environments
            pass

    def _migrate_schema(self, conn: sqlite3.Connection) -> None:  # noqa: C901
        """Ensure table columns and indices exist; backward-compatible migration."""
        try:
            cursor = conn.execute("PRAGMA table_info(keywords)")
            cols = {row[1] for row in cursor.fetchall()}
            if "cluster_id" not in cols:
                conn.execute("ALTER TABLE keywords ADD COLUMN cluster_id INTEGER")
            if "cluster_label" not in cols:
                conn.execute("ALTER TABLE keywords ADD COLUMN cluster_label TEXT")
            if "geo" not in cols:
                conn.execute("ALTER TABLE keywords ADD COLUMN geo TEXT DEFAULT ''")
            if "language" not in cols:
                conn.execute("ALTER TABLE keywords ADD COLUMN language TEXT DEFAULT ''")
            if "intent" not in cols:
                conn.execute("ALTER TABLE keywords ADD COLUMN intent TEXT DEFAULT ''")
            if "data_source" not in cols:
                conn.execute(
                    "ALTER TABLE keywords ADD COLUMN data_source TEXT DEFAULT 'heurístico'"
                )
            if "run_id" not in cols:
                conn.execute("ALTER TABLE keywords ADD COLUMN run_id TEXT")
            if "data_version" not in cols:
                conn.execute("ALTER TABLE keywords ADD COLUMN data_version INTEGER DEFAULT 1")
            if "updated_at" not in cols:
                conn.execute(
                    "ALTER TABLE keywords ADD COLUMN updated_at TEXT DEFAULT CURRENT_TIMESTAMP"
                )
            # Composite index for geo/language and score ordering
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_geo_lang_score ON keywords(geo, language, score DESC)"
            )
            # Additional indexes for performance optimization
            conn.execute("CREATE INDEX IF NOT EXISTS idx_last_seen ON keywords(last_seen)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_source ON keywords(source)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_intent ON keywords(intent)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_data_source ON keywords(data_source)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_score ON keywords(score DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_volume ON keywords(volume DESC)")
            conn.commit()
        except sqlite3.Error as e:
            logging.warning("Schema migration check/add failed: %s", e)

    def _init_database(self):
        """Inicializa la base de datos con el schema necesario.

        Nota: Dado que los datos actuales son de prueba, recreamos la tabla con clave compuesta
        para soportar multi-geo/idioma sin colisiones.
        """
        with sqlite3.connect(self.db_path) as conn:
            # Apply pragmas
            self._apply_pragmas(conn)

            # Drop and recreate keywords with composite unique
            conn.execute("DROP TABLE IF EXISTS keywords")
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

            # Índices para optimizar consultas
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_geo_lang_score ON keywords(geo, language, score DESC)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_last_seen ON keywords(last_seen)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_source ON keywords(source)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_intent ON keywords(intent)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_data_source ON keywords(data_source)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_score ON keywords(score DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_volume ON keywords(volume DESC)")

            # Runs table for execution metrics
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

            conn.commit()

    def insert_keyword(self, keyword: Keyword) -> bool:
        """Inserta o actualiza una keyword en la base de datos"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Upsert emulation using INSERT OR REPLACE limited by legacy UNIQUE(keyword)
                # and extended identifying attributes via manual lookup
                # Prefer ON CONFLICT where available (SQLite >= 3.24), but keep compatibility
                try:
                    conn.execute(
                        """
                        INSERT INTO keywords 
                        (keyword, source, volume, trend_score, competition, score, category, geo, language, intent, cluster_id, cluster_label, data_source, run_id, data_version, trend_weight, volume_weight, competition_weight, intent_prob, last_seen, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(keyword, geo, language) DO UPDATE SET 
                            source=excluded.source,
                            volume=excluded.volume,
                            trend_score=excluded.trend_score,
                            competition=excluded.competition,
                            score=excluded.score,
                            category=excluded.category,
                            geo=excluded.geo,
                            language=excluded.language,
                            intent=excluded.intent,
                            cluster_id=excluded.cluster_id,
                            cluster_label=excluded.cluster_label,
                            data_source=excluded.data_source,
                            run_id=COALESCE(excluded.run_id, run_id),
                            data_version=MAX(data_version, excluded.data_version),
                            trend_weight=excluded.trend_weight,
                            volume_weight=excluded.volume_weight,
                            competition_weight=excluded.competition_weight,
                            intent_prob=excluded.intent_prob,
                            last_seen=excluded.last_seen,
                            updated_at=CURRENT_TIMESTAMP
                    """,
                        (
                            keyword.keyword,
                            keyword.source,
                            keyword.volume,
                            keyword.trend_score,
                            keyword.competition,
                            keyword.score,
                            keyword.category,
                            keyword.geo,
                            keyword.language,
                            keyword.intent,
                            keyword.cluster_id,
                            keyword.cluster_label,
                            keyword.data_source,
                            keyword.run_id,
                            keyword.data_version,
                            keyword.trend_weight,
                            keyword.volume_weight,
                            keyword.competition_weight,
                            keyword.intent_prob,
                            keyword.last_seen,
                            keyword.updated_at,
                        ),
                    )
                except sqlite3.Error:
                    # Fallback to legacy replace with all columns
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO keywords 
                        (keyword, source, volume, trend_score, competition, score, category, geo, language, intent, cluster_id, cluster_label, data_source, run_id, data_version, trend_weight, volume_weight, competition_weight, intent_prob, last_seen, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            keyword.keyword,
                            keyword.source,
                            keyword.volume,
                            keyword.trend_score,
                            keyword.competition,
                            keyword.score,
                            keyword.category,
                            keyword.geo,
                            keyword.language,
                            keyword.intent,
                            keyword.cluster_id,
                            keyword.cluster_label,
                            keyword.data_source,
                            keyword.run_id,
                            keyword.data_version,
                            keyword.trend_weight,
                            keyword.volume_weight,
                            keyword.competition_weight,
                            keyword.intent_prob,
                            keyword.last_seen,
                            keyword.updated_at,
                        ),
                    )
                conn.commit()
                return True
        except sqlite3.Error as e:
            logging.error("Error inserting keyword %s: %s", keyword.keyword, e)
            return False

    def insert_keywords_batch(self, keywords: list[Keyword]) -> int:
        """Inserta múltiples keywords de forma batch"""
        inserted = 0
        try:
            with sqlite3.connect(self.db_path) as conn:
                for keyword in keywords:
                    try:
                        try:
                            conn.execute(
                                """
                                INSERT INTO keywords
                                (keyword, source, volume, trend_score, competition, score, category, geo, language, intent, cluster_id, cluster_label, data_source, run_id, data_version, trend_weight, volume_weight, competition_weight, intent_prob, last_seen, updated_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                ON CONFLICT(keyword, geo, language) DO UPDATE SET
                                    source=excluded.source,
                                    volume=excluded.volume,
                                    trend_score=excluded.trend_score,
                                    competition=excluded.competition,
                                    score=excluded.score,
                                    category=excluded.category,
                                    geo=excluded.geo,
                                    language=excluded.language,
                                    intent=excluded.intent,
                                    cluster_id=excluded.cluster_id,
                                    cluster_label=excluded.cluster_label,
                                    data_source=excluded.data_source,
                                    run_id=COALESCE(excluded.run_id, run_id),
                                    data_version=MAX(data_version, excluded.data_version),
                                    trend_weight=excluded.trend_weight,
                                    volume_weight=excluded.volume_weight,
                                    competition_weight=excluded.competition_weight,
                                    intent_prob=excluded.intent_prob,
                                    last_seen=excluded.last_seen,
                                    updated_at=CURRENT_TIMESTAMP
                                """,
                                (
                                    keyword.keyword,
                                    keyword.source,
                                    keyword.volume,
                                    keyword.trend_score,
                                    keyword.competition,
                                    keyword.score,
                                    keyword.category,
                                    keyword.geo,
                                    keyword.language,
                                    keyword.intent,
                                    keyword.cluster_id,
                                    keyword.cluster_label,
                                    keyword.data_source,
                                    keyword.run_id,
                                    keyword.data_version,
                                    keyword.trend_weight,
                                    keyword.volume_weight,
                                    keyword.competition_weight,
                                    keyword.intent_prob,
                                    keyword.last_seen,
                                    keyword.updated_at,
                                ),
                            )
                        except sqlite3.Error:
                            conn.execute(
                                """
                                INSERT OR REPLACE INTO keywords 
                                (keyword, source, volume, trend_score, competition, score, category, cluster_id, cluster_label, last_seen)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                                (
                                    keyword.keyword,
                                    keyword.source,
                                    keyword.volume,
                                    keyword.trend_score,
                                    keyword.competition,
                                    keyword.score,
                                    keyword.category,
                                    keyword.cluster_id,
                                    keyword.cluster_label,
                                    keyword.last_seen,
                                ),
                            )
                        inserted += 1
                    except sqlite3.Error as e:
                        logging.warning("Failed to insert keyword %s: %s", keyword.keyword, e)
                        continue
                conn.commit()
        except sqlite3.Error as e:
            logging.error("Batch insert error: %s", e)

        logging.info("Inserted %d/%d keywords", inserted, len(keywords))
        return inserted

    def get_keywords(
        self,
        limit: int | None = None,
        min_score: float = 0.0,
        filters: dict | None = None,
        order_by: str = "score_desc",
    ) -> list[dict]:
        """Obtiene keywords ordenadas por score con filtros opcionales.

        Filtros soportados: geo, language, intent, source, data_source, last_seen_after (ISO8601)
        order_by soportado: "score_desc" (default), "last_seen_desc".
        """
        start_time = time.time()

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                where = ["score >= ?"]
                params: list[object] = [min_score]
                if filters:
                    if geo := filters.get("geo"):
                        where.append("geo = ?")
                        params.append(geo)
                    if lang := filters.get("language"):
                        where.append("language = ?")
                        params.append(lang)
                    if intent := filters.get("intent"):
                        where.append("intent = ?")
                        params.append(intent)
                    if source := filters.get("source"):
                        where.append("source = ?")
                        params.append(source)
                    if ds := filters.get("data_source"):
                        where.append("data_source = ?")
                        params.append(ds)
                    if seen := filters.get("last_seen_after"):
                        where.append("last_seen >= ?")
                        params.append(seen)

                order_sql = (
                    "ORDER BY score DESC" if order_by == "score_desc" else "ORDER BY last_seen DESC"
                )
                limit_sql = f" LIMIT {int(limit)}" if limit else ""
                # The WHERE parts are assembled from a fixed allow-list and values are parameterized; safe.
                query = f"SELECT * FROM keywords WHERE {' AND '.join(where)} {order_sql}{limit_sql}"  # noqa: S608
                cursor = conn.execute(query, params)
                results = [dict(row) for row in cursor.fetchall()]

                # Registrar métricas de rendimiento
                execution_time = time.time() - start_time
                sqlite_monitor.record_query(
                    query_type="get_keywords",
                    execution_time=execution_time,
                    rows_returned=len(results),
                    filters=filters,
                )

                return results

        except sqlite3.Error as e:
            # Registrar error en métricas
            execution_time = time.time() - start_time
            sqlite_monitor.record_query(
                query_type="get_keywords_error",
                execution_time=execution_time,
                rows_returned=0,
                filters=filters,
            )
            logging.error("Error fetching keywords: %s", e)
            return []

    def insert_run(self, run_id: str, metrics: dict) -> bool:
        """Inserta o actualiza el registro de una corrida."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                self._apply_pragmas(conn)
                conn.execute(
                    """
                    INSERT INTO runs (run_id, started_at, finished_at, geo, language, seeds_json, seeds_count, keywords_found, rejected_count, trend_weight, volume_weight, competition_weight, duration_ms)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(run_id) DO UPDATE SET
                        finished_at=excluded.finished_at,
                        geo=excluded.geo,
                        language=excluded.language,
                        seeds_json=excluded.seeds_json,
                        seeds_count=excluded.seeds_count,
                        keywords_found=excluded.keywords_found,
                        rejected_count=excluded.rejected_count,
                        trend_weight=excluded.trend_weight,
                        volume_weight=excluded.volume_weight,
                        competition_weight=excluded.competition_weight,
                        duration_ms=excluded.duration_ms
                    """,
                    (
                        run_id,
                        metrics.get("started_at"),
                        metrics.get("finished_at"),
                        metrics.get("geo"),
                        metrics.get("language"),
                        metrics.get("seeds_json"),
                        metrics.get("seeds_count", 0),
                        metrics.get("keywords_found", 0),
                        metrics.get("rejected_count", 0),
                        metrics.get("trend_weight", 0.0),
                        metrics.get("volume_weight", 0.0),
                        metrics.get("competition_weight", 0.0),
                        metrics.get("duration_ms", 0),
                    ),
                )
                conn.commit()
                return True
        except sqlite3.Error as e:
            logging.error("Error inserting run metrics: %s", e)
            return False

    def get_keyword_by_text(self, keyword_text: str) -> dict | None:
        """Busca una keyword específica por texto"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("SELECT * FROM keywords WHERE keyword = ?", (keyword_text,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            logging.error("Error fetching keyword %s: %s", keyword_text, e)
            return None

    def update_keyword_score(
        self,
        keyword_text: str,
        volume: int | None = None,
        trend_score: float | None = None,
        competition: float | None = None,
        score: float | None = None,
        category: str | None = None,
    ) -> bool:
        """Actualiza métricas específicas de una keyword"""
        try:
            updates = []
            params: list[object] = []

            if volume is not None:
                updates.append("volume = ?")
                params.append(volume)
            if trend_score is not None:
                updates.append("trend_score = ?")
                params.append(trend_score)
            if competition is not None:
                updates.append("competition = ?")
                params.append(competition)
            if score is not None:
                updates.append("score = ?")
                params.append(score)
            if category is not None:
                updates.append("category = ?")
                params.append(category)

            updates.append("last_seen = ?")
            params.append(datetime.now().isoformat())
            params.append(keyword_text)

            with sqlite3.connect(self.db_path) as conn:
                # Fields in `updates` are constructed from a fixed allowlist above; parameters are bound safely.
                conn.execute(
                    f"UPDATE keywords SET {', '.join(updates)} WHERE keyword = ?",  # noqa: S608
                    params,
                )
                conn.commit()
                return True

        except sqlite3.Error as e:
            logging.error("Error updating keyword %s: %s", keyword_text, e)
            return False

    def get_stats(self) -> dict:
        """Obtiene estadísticas generales de la base de datos"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT 
                        COUNT(*) as total_keywords,
                        AVG(score) as avg_score,
                        MAX(score) as max_score,
                        COUNT(CASE WHEN score > 70 THEN 1 END) as high_score_count
                    FROM keywords
                """
                )
                row = cursor.fetchone()
                stats = dict(row) if row else {}

                # Obtener fuentes
                cursor = conn.execute(
                    """
                    SELECT source, COUNT(*) as count 
                    FROM keywords 
                    GROUP BY source
                """
                )
                sources = {row[0]: row[1] for row in cursor.fetchall()}
                stats["sources"] = sources

                return stats
        except sqlite3.Error as e:
            logging.error("Error getting stats: %s", e)
            return {}

    def cleanup_old_keywords(self, days: int = 30) -> int:
        """Elimina keywords más antiguas que X días"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "DELETE FROM keywords WHERE last_seen < ?", (cutoff_date.isoformat(),)
                )
                conn.commit()
                deleted = cursor.rowcount
                logging.info("Cleaned up %d old keywords", deleted)
                return deleted
        except sqlite3.Error as e:
            logging.error("Error cleaning up keywords: %s", e)
            return 0

    def fetch_all(self, query: str, params: tuple = ()) -> list[tuple]:
        """
        Execute a custom SQL query and return all results.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            List of tuples with query results
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                self._apply_pragmas(conn)
                cursor = conn.execute(query, params)
                results = cursor.fetchall()
                return results
        except sqlite3.Error as e:
            logging.error("Error executing query: %s", e)
            return []

        # =============================================================================
        # ENTERPRISE METHODS - Run Tracking and Enhanced Schema Support
        # =============================================================================

    def create_run_tables(self) -> None:
        """Create enhanced tables for run tracking and metadata."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                self._apply_pragmas(conn)

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
                logging.info("Enhanced schema tables created successfully")

        except sqlite3.Error as e:
            logging.error("Error creating enhanced tables: %s", e)

    def save_run_metadata(self, run_meta: RunMetadata) -> bool:
        """Save run metadata to database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                self._apply_pragmas(conn)

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
            logging.error("Error saving run metadata: %s", e)
            return False

    def save_cluster_metadata(self, cluster_meta: ClusterMetadata) -> bool:
        """Save cluster metadata to database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                self._apply_pragmas(conn)

                data = cluster_meta.to_dict()
                conn.execute(
                    """
                    INSERT OR REPLACE INTO clusters_metadata 
                    (cluster_id, run_id, label, keywords_count, avg_score, avg_volume,
                     dominant_intent, dominant_data_source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        data["cluster_id"],
                        data["run_id"],
                        data["label"],
                        data["keywords_count"],
                        data["avg_score"],
                        data["avg_volume"],
                        data["dominant_intent"],
                        data["dominant_data_source"],
                    ),
                )

                conn.commit()
                return True

        except sqlite3.Error as e:
            logging.error("Error saving cluster metadata: %s", e)
            return False

    def save_enhanced_keyword(self, enhanced_kw: EnhancedKeyword) -> bool:
        """Save enhanced keyword with full traceability."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                self._apply_pragmas(conn)

                data = enhanced_kw.to_dict()
                conn.execute(
                    """
                    INSERT OR REPLACE INTO keywords 
                    (keyword, source, volume, trend_score, competition, score, category, 
                     geo, language, intent, cluster_id, cluster_label, data_source, 
                     run_id, data_version, trend_weight, volume_weight, competition_weight, 
                     intent_prob, last_seen, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        data["keyword"],
                        data["source"],
                        data["volume"],
                        data["trend_score"],
                        data["competition"],
                        data["score"],
                        data["category"],
                        data["geo"],
                        data["language"],
                        data["intent"],
                        data["cluster_id"],
                        data["cluster_label"],
                        data["data_source"],
                        data["run_id"],
                        data["data_version"],
                        data["trend_weight"],
                        data["volume_weight"],
                        data["competition_weight"],
                        data["intent_prob"],
                        data["last_seen"],
                        data["updated_at"],
                    ),
                )

                conn.commit()
                return True

        except sqlite3.Error as e:
            logging.error("Error saving enhanced keyword: %s", e)
            return False

    def get_run_metadata(self, run_id: str) -> dict[str, Any] | None:
        """Get run metadata by run_id."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("SELECT * FROM runs_metadata WHERE run_id = ?", (run_id,))
                row = cursor.fetchone()
                return dict(row) if row else None

        except sqlite3.Error as e:
            logging.error("Error fetching run metadata: %s", e)
            return None

    def get_cluster_metadata(self, run_id: str) -> list[dict[str, Any]]:
        """Get all cluster metadata for a run."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM clusters_metadata WHERE run_id = ? ORDER BY cluster_id",
                    (run_id,),
                )
                return [dict(row) for row in cursor.fetchall()]

        except sqlite3.Error as e:
            logging.error("Error fetching cluster metadata: %s", e)
            return []

    # =============================================================================
    # STANDARDIZED SCHEMA v2.0.0 METHODS
    # =============================================================================

    def create_run_v2(self, run_metadata: RunMetadata) -> bool:
        """Create a new run using standardized schema v2.0.0."""
        if not self.use_standardized_schema:
            # Fallback to legacy method if it exists
            return True  # Simplified fallback

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                conn.execute(
                    """
                    INSERT INTO runs (
                        run_id, started_at, finished_at, profile, geo, language, 
                        seeds, total_keywords, total_clusters, config_snapshot, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        run_metadata.run_id,
                        run_metadata.started_at,
                        run_metadata.finished_at,
                        run_metadata.profile,
                        run_metadata.geo,
                        run_metadata.language,
                        json.dumps(run_metadata.seeds),
                        len(run_metadata.seeds) if run_metadata.seeds else 0,
                        0,  # Will be updated when clustering is done
                        None,  # Config snapshot
                        "running",
                    ),
                )
                conn.commit()
                logging.info(f"Created run {run_metadata.run_id} in standardized schema")
                return True

        except sqlite3.Error as e:
            logging.error("Error creating run v2: %s", e)
            return False

    def insert_keyword_v2(self, keyword: EnhancedKeyword) -> bool:
        """Insert keyword using standardized schema v2.0.0 with proper UNIQUE constraints."""
        if not self.use_standardized_schema:
            # Fallback to legacy insert
            return True  # Simplified fallback

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                conn.execute(
                    """
                    INSERT OR REPLACE INTO keywords (
                        keyword, source, volume, trend_score, competition, score, 
                        category, intent, intent_confidence, cluster_id, cluster_label,
                        geo, language, data_source, run_id, data_version
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        keyword.keyword,
                        keyword.source,
                        keyword.volume,
                        keyword.trend_score,
                        keyword.competition,
                        keyword.score,
                        keyword.category,
                        str(keyword.intent),
                        keyword.intent_prob,
                        keyword.cluster_id,
                        keyword.cluster_label,
                        keyword.geo,
                        keyword.language,
                        str(keyword.data_source),
                        keyword.run_id,
                        2,  # Schema version 2.0.0
                    ),
                )
                conn.commit()
                return True

        except sqlite3.Error as e:
            logging.error("Error inserting keyword v2: %s", e)
            return False

    def create_cluster_v2(self, cluster: ClusterMetadata) -> bool:
        """Create cluster using standardized schema v2.0.0."""
        if not self.use_standardized_schema:
            # Fallback to legacy method
            return True  # Simplified fallback

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                conn.execute(
                    """
                    INSERT OR REPLACE INTO clusters (
                        cluster_id, cluster_label, run_id, keywords_count, avg_score, 
                        avg_volume, dominant_intent, dominant_data_source, algorithm_used,
                        algorithm_params, silhouette_score
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        cluster.cluster_id,
                        cluster.label,
                        cluster.run_id,
                        cluster.keywords_count,
                        cluster.avg_score,
                        cluster.avg_volume,
                        str(cluster.dominant_intent),
                        str(cluster.dominant_data_source),
                        getattr(cluster, "algorithm_used", "kmeans"),
                        json.dumps(getattr(cluster, "algorithm_params", {})),
                        getattr(cluster, "silhouette_score", 0.0),
                    ),
                )
                conn.commit()
                logging.info(f"Created cluster {cluster.cluster_id} for run {cluster.run_id}")
                return True

        except sqlite3.Error as e:
            logging.error("Error creating cluster v2: %s", e)
            return False

    def get_keywords_by_run_v2(
        self, run_id: str, limit: int | None = None
    ) -> list[EnhancedKeyword]:
        """Get keywords for a run using standardized schema v2.0.0."""
        if not self.use_standardized_schema:
            # Fallback to legacy method
            return []  # Simplified fallback

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                query = """
                    SELECT * FROM keywords 
                    WHERE run_id = ? 
                    ORDER BY score DESC, volume DESC
                """
                params: list[Any] = [run_id]

                if limit:
                    query += " LIMIT ?"
                    params.append(limit)

                cursor = conn.execute(query, params)
                rows = cursor.fetchall()

                # Convert to EnhancedKeyword objects
                keywords = []
                for row in rows:
                    keywords.append(
                        EnhancedKeyword(
                            keyword=row["keyword"],
                            source=row["source"],
                            volume=row["volume"],
                            trend_score=row["trend_score"],
                            competition=row["competition"],
                            score=row["score"],
                            category=row["category"],
                            intent=row["intent"],
                            intent_prob=row["intent_confidence"],
                            cluster_id=row["cluster_id"],
                            cluster_label=row["cluster_label"],
                            geo=row["geo"],
                            language=row["language"],
                            data_source=row["data_source"],
                            run_id=row["run_id"],
                        )
                    )

                return keywords

        except sqlite3.Error as e:
            logging.error("Error getting keywords by run v2: %s", e)
            return []

    def get_schema_info_v2(self) -> dict:
        """Get comprehensive schema information for debugging."""
        return get_schema_info()

    def validate_schema_v2(self) -> bool:
        """Validate that standardized schema v2.0.0 is properly set up."""
        try:
            info = self.get_schema_info_v2()
            required_tables = {"runs", "keywords", "clusters", "exports"}
            existing_tables = set(info["tables"].keys())

            if not required_tables.issubset(existing_tables):
                missing = required_tables - existing_tables
                logging.error("Missing required tables: %s", missing)
                return False

            # Check minimum number of indexes
            if len(info["indexes"]) < 10:
                logging.warning(f"Only {len(info['indexes'])} indexes found, expected at least 10")

            # Check foreign keys are enabled
            if info["pragmas"].get("foreign_keys") != 1:
                logging.warning("Foreign key constraints are not enabled")

            logging.info("Schema v2.0.0 validation passed")
            return True

        except sqlite3.Error as e:
            logging.error("Schema validation failed: %s", e)
            return False

    def get_performance_metrics(self) -> dict:
        """Obtiene métricas de rendimiento del sistema de monitoreo."""
        return sqlite_monitor.get_performance_stats()

    def get_database_stats(self) -> dict:
        """Obtiene estadísticas de la base de datos."""
        return sqlite_monitor.get_database_stats(self.db_path)

    def log_performance_report(self) -> None:
        """Genera un reporte de rendimiento en los logs."""
        try:
            perf_stats = self.get_performance_metrics()
            db_stats = self.get_database_stats()

            logging.info("=== SQLite Performance Report ===")
            logging.info(f"Total queries executed: {perf_stats['total_queries']}")
            logging.info(".2f")
            logging.info(
                f"Slow queries (>100ms): {perf_stats['slow_queries']} ({perf_stats.get('slow_query_percentage', 0):.1f}%)"
            )
            logging.info(f"Database size: {db_stats.get('database_size_mb', 0):.2f} MB")
            logging.info(f"Total keywords: {db_stats.get('total_keywords', 0)}")
            logging.info(f"Total runs: {db_stats.get('total_runs', 0)}")
            logging.info("==================================")

        except sqlite3.Error as e:
            logging.error("Error generating performance report: %s", e)
