import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta


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
    last_seen: str | None = None

    def __post_init__(self):
        if self.last_seen is None:
            self.last_seen = datetime.now().isoformat()


class KeywordDatabase:
    """Manejo de la base de datos SQLite para keywords"""

    def __init__(self, db_path: str = "keywords.db"):
        self.db_path = db_path
        self._init_database()
        logging.info(f"Database initialized at {db_path}")

    def _init_database(self):
        """Inicializa la base de datos con el schema necesario"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS keywords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword TEXT UNIQUE NOT NULL,
                    source TEXT NOT NULL,
                    volume INTEGER DEFAULT 0,
                    trend_score REAL DEFAULT 0.0,
                    competition REAL DEFAULT 0.0,
                    score REAL DEFAULT 0.0,
                    category TEXT DEFAULT '',
                    last_seen TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Índices para optimizar consultas
            conn.execute("CREATE INDEX IF NOT EXISTS idx_keyword ON keywords(keyword)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_score ON keywords(score DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_last_seen ON keywords(last_seen)")

            conn.commit()

    def insert_keyword(self, keyword: Keyword) -> bool:
        """Inserta o actualiza una keyword en la base de datos"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO keywords 
                    (keyword, source, volume, trend_score, competition, score, category, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        keyword.keyword,
                        keyword.source,
                        keyword.volume,
                        keyword.trend_score,
                        keyword.competition,
                        keyword.score,
                        keyword.category,
                        keyword.last_seen,
                    ),
                )
                conn.commit()
                return True
        except sqlite3.Error as e:
            logging.error(f"Error inserting keyword {keyword.keyword}: {e}")
            return False

    def insert_keywords_batch(self, keywords: list[Keyword]) -> int:
        """Inserta múltiples keywords de forma batch"""
        inserted = 0
        try:
            with sqlite3.connect(self.db_path) as conn:
                for keyword in keywords:
                    try:
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO keywords 
                            (keyword, source, volume, trend_score, competition, score, category, last_seen)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                            (
                                keyword.keyword,
                                keyword.source,
                                keyword.volume,
                                keyword.trend_score,
                                keyword.competition,
                                keyword.score,
                                keyword.category,
                                keyword.last_seen,
                            ),
                        )
                        inserted += 1
                    except sqlite3.Error as e:
                        logging.warning(f"Failed to insert keyword {keyword.keyword}: {e}")
                        continue
                conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Batch insert error: {e}")

        logging.info(f"Inserted {inserted}/{len(keywords)} keywords")
        return inserted

    def get_keywords(self, limit: int | None = None, min_score: float = 0.0) -> list[dict]:
        """Obtiene keywords ordenadas por score"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                query = """
                    SELECT * FROM keywords 
                    WHERE score >= ? 
                    ORDER BY score DESC
                """

                if limit:
                    query += f" LIMIT {limit}"

                cursor = conn.execute(query, (min_score,))
                return [dict(row) for row in cursor.fetchall()]

        except sqlite3.Error as e:
            logging.error(f"Error fetching keywords: {e}")
            return []

    def get_keyword_by_text(self, keyword_text: str) -> dict | None:
        """Busca una keyword específica por texto"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("SELECT * FROM keywords WHERE keyword = ?", (keyword_text,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            logging.error(f"Error fetching keyword {keyword_text}: {e}")
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

        except Exception as e:
            logging.error(f"Error updating keyword {keyword_text}: {e}")
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
            logging.error(f"Error getting stats: {e}")
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
                logging.info(f"Cleaned up {deleted} old keywords")
                return deleted
        except sqlite3.Error as e:
            logging.error(f"Error cleaning up keywords: {e}")
            return 0
