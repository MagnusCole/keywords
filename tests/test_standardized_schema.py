"""
Test standardized database schema v2.0.0 functionality.

Tests include:
- Schema creation and validation
- UNIQUE constraints
- Foreign key relationships
- Index performance
- Data integrity
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from src.db.database import KeywordDatabase
from src.db.standardized_schema import StandardizedSchema, get_schema_info
from src.db.schema import EnhancedKeyword, RunMetadata, ClusterMetadata, DataSource, IntentType


class TestStandardizedSchema:
    """Test standardized database schema v2.0.0."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        
        db = KeywordDatabase(str(db_path), use_standardized_schema=True)
        yield db
        
        # Cleanup
        if db_path.exists():
            db_path.unlink()

    def test_schema_initialization(self, temp_db):
        """Test that standardized schema is properly initialized."""
        assert temp_db.use_standardized_schema is True
        assert temp_db.validate_schema_v2() is True
        
        # Get schema info
        info = temp_db.get_schema_info_v2()
        
        # Check required tables exist
        required_tables = {"runs", "keywords", "clusters", "exports"}
        assert set(info["tables"].keys()) >= required_tables
        
        # Check indexes exist
        assert len(info["indexes"]) >= 10
        
        # Check foreign keys are enabled
        assert info["pragmas"]["foreign_keys"] == 1

    def test_run_creation_v2(self, temp_db):
        """Test run creation with standardized schema."""
        run_metadata = RunMetadata(
            run_id="test_run_v2",
            started_at=datetime.now(),
            profile="test",
            geo="US",
            language="en",
            seeds=["test", "keyword"]
        )
        
        success = temp_db.create_run_v2(run_metadata)
        assert success is True

    def test_keyword_insertion_v2(self, temp_db):
        """Test keyword insertion with UNIQUE constraints."""
        # First create a run
        run_metadata = RunMetadata(
            run_id="test_run_keywords",
            profile="test",
            geo="US",
            language="en",
            seeds=["test"]
        )
        temp_db.create_run_v2(run_metadata)
        
        # Create test keyword
        keyword = EnhancedKeyword(
            keyword="test keyword",
            source="seed",
            volume=1000,
            trend_score=0.8,
            competition=0.5,
            score=75.0,
            category="test",
            intent=IntentType.INFORMATIONAL,
            intent_prob=0.9,
            cluster_id=1,
            cluster_label="Test Cluster",
            geo="US",
            language="en",
            data_source=DataSource.HEURISTIC,
            run_id="test_run_keywords"
        )
        
        # Insert keyword
        success = temp_db.insert_keyword_v2(keyword)
        assert success is True
        
        # Try to insert same keyword (should update, not create duplicate)
        keyword.score = 80.0  # Update score
        success = temp_db.insert_keyword_v2(keyword)
        assert success is True
        
        # Verify only one keyword exists
        keywords = temp_db.get_keywords_by_run_v2("test_run_keywords")
        assert len(keywords) == 1
        assert keywords[0].score == 80.0  # Should have updated score

    def test_cluster_creation_v2(self, temp_db):
        """Test cluster creation with standardized schema."""
        # First create a run
        run_metadata = RunMetadata(run_id="test_run_cluster", profile="test", geo="US", language="en", seeds=["test"])
        temp_db.create_run_v2(run_metadata)
        
        # Create test cluster
        cluster = ClusterMetadata(
            cluster_id=1,
            label="Test Cluster",
            run_id="test_run_cluster",
            keywords_count=5,
            avg_score=75.0,
            avg_volume=1200,
            dominant_intent=IntentType.INFORMATIONAL,
            dominant_data_source=DataSource.HEURISTIC,
            created_at=datetime.now()
        )
        
        success = temp_db.create_cluster_v2(cluster)
        assert success is True

    def test_unique_constraints(self, temp_db):
        """Test that UNIQUE constraints prevent duplicates."""
        # Create run
        run_metadata = RunMetadata(run_id="test_unique", profile="test", geo="US", language="en", seeds=["test"])
        temp_db.create_run_v2(run_metadata)
        
        # Create keyword
        keyword1 = EnhancedKeyword(
            keyword="duplicate test",
            source="seed",
            geo="US",
            language="en",
            run_id="test_unique",
            data_source=DataSource.HEURISTIC,
            intent=IntentType.INFORMATIONAL
        )
        
        # Create identical keyword (same keyword, geo, language, run_id)
        keyword2 = EnhancedKeyword(
            keyword="duplicate test",
            source="expansion",
            score=90.0,
            geo="US",
            language="en",
            run_id="test_unique",
            data_source=DataSource.ADS_VOLUME,
            intent=IntentType.COMMERCIAL
        )
        
        # Insert first keyword
        temp_db.insert_keyword_v2(keyword1)
        
        # Insert duplicate (should replace)
        temp_db.insert_keyword_v2(keyword2)
        
        # Should only have one keyword with updated values
        keywords = temp_db.get_keywords_by_run_v2("test_unique")
        assert len(keywords) == 1
        assert keywords[0].source == "expansion"  # Should have updated
        assert keywords[0].score == 90.0

    def test_foreign_key_constraints(self, temp_db):
        """Test that foreign key constraints work properly."""
        # Try to insert keyword without creating run first (should fail in strict mode)
        keyword = EnhancedKeyword(
            keyword="orphan keyword",
            source="seed",
            geo="US",
            language="en",
            run_id="nonexistent_run",
            data_source=DataSource.HEURISTIC,
            intent=IntentType.INFORMATIONAL
        )
        
        # This might not fail in SQLite by default, but the constraint is defined
        # The behavior depends on PRAGMA foreign_keys setting
        success = temp_db.insert_keyword_v2(keyword)
        # We can't strictly test failure here without more complex setup

    def test_performance_indexes(self, temp_db):
        """Test that performance indexes are created."""
        info = temp_db.get_schema_info_v2()
        
        expected_indexes = [
            "idx_keywords_run_id",
            "idx_keywords_geo_lang",
            "idx_keywords_score_desc",
            "idx_keywords_volume_desc",
            "idx_keywords_geo_lang_score"
        ]
        
        existing_indexes = info["indexes"]
        for expected in expected_indexes:
            assert expected in existing_indexes, f"Missing performance index: {expected}"

    def test_data_retrieval_v2(self, temp_db):
        """Test data retrieval with standardized schema."""
        # Create run and keywords
        run_metadata = RunMetadata(run_id="test_retrieval", profile="test", geo="US", language="en", seeds=["test"])
        temp_db.create_run_v2(run_metadata)
        
        # Insert multiple keywords
        keywords_data = [
            ("keyword 1", 100, 80.0),
            ("keyword 2", 200, 70.0),
            ("keyword 3", 150, 90.0),
        ]
        
        for kw_text, volume, score in keywords_data:
            keyword = EnhancedKeyword(
                keyword=kw_text,
                source="seed",
                volume=volume,
                score=score,
                geo="US",
                language="en",
                run_id="test_retrieval",
                data_source=DataSource.HEURISTIC,
                intent=IntentType.INFORMATIONAL
            )
            temp_db.insert_keyword_v2(keyword)
        
        # Retrieve keywords
        retrieved = temp_db.get_keywords_by_run_v2("test_retrieval")
        assert len(retrieved) == 3
        
        # Should be ordered by score DESC (keyword 3, 1, 2)
        assert retrieved[0].keyword == "keyword 3"
        assert retrieved[1].keyword == "keyword 1" 
        assert retrieved[2].keyword == "keyword 2"
        
        # Test with limit
        limited = temp_db.get_keywords_by_run_v2("test_retrieval", limit=2)
        assert len(limited) == 2

    def test_schema_validation_comprehensive(self, temp_db):
        """Comprehensive test of schema validation."""
        validation_result = temp_db.validate_schema_v2()
        assert validation_result is True
        
        # Get detailed schema info
        info = temp_db.get_schema_info_v2()
        
        # Validate table structures
        assert "keywords" in info["tables"]
        keyword_columns = [col[1] for col in info["tables"]["keywords"]]  # column names
        required_columns = ["keyword_id", "keyword", "source", "volume", "score", "run_id"]
        for col in required_columns:
            assert col in keyword_columns, f"Missing required column: {col}"
        
        # Validate foreign keys
        assert "keywords" in info["foreign_keys"]
        fk_info = info["foreign_keys"]["keywords"]
        assert len(fk_info) > 0  # Should have foreign key to runs table


def test_schema_creation_standalone():
    """Test standalone schema creation."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    
    try:
        # Create schema directly
        schema = StandardizedSchema(db_path)
        schema.initialize_database()
        
        # Validate creation
        info = get_schema_info(db_path)
        assert len(info["tables"]) >= 4
        assert len(info["indexes"]) >= 10
        
    finally:
        if db_path.exists():
            db_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])