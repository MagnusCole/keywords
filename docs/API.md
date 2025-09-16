# API Reference v2.0.0

This document provides comprehensive API documentation for the Keyword Finder system's production-ready components.

## 📋 Table of Contents

1. [Core Components](#core-components)
2. [Scoring System](#scoring-system)
3. [ML Pipeline](#ml-pipeline)
4. [Export System](#export-system)
5. [Logging System](#logging-system)
6. [Database Schema](#database-schema)
7. [Configuration API](#configuration-api)
8. [Error Handling](#error-handling)

## 🔧 Core Components

### KeywordFinder

Main orchestrator class for keyword research operations.

```python
from src.main import KeywordFinder

class KeywordFinder:
    def __init__(self, config: dict):
        """Initialize keyword finder with configuration."""
        
    async def find_keywords(
        self, 
        seeds: list[str], 
        limit: int = 400,
        existing_mode: bool = False
    ) -> tuple[list[dict], dict]:
        """
        Find and score keywords based on seeds.
        
        Args:
            seeds: List of seed keywords
            limit: Maximum keywords to return
            existing_mode: Use only existing data
            
        Returns:
            (keywords, metadata)
        """
```

**Example Usage:**

```python
import asyncio
from src.main import KeywordFinder
from src.platform.settings import load_config

# Load configuration
config = load_config("config/config.yaml")

# Initialize finder
finder = KeywordFinder(config)

# Find keywords
async def main():
    keywords, metadata = await finder.find_keywords(
        seeds=["limpieza piscina", "mantenimiento piscina"],
        limit=500,
        existing_mode=False
    )
    
    print(f"Found {len(keywords)} keywords")
    print(f"Metadata: {metadata}")

asyncio.run(main())
```

### GoogleScraper

Web scraper for Google autocomplete suggestions.

```python
from src.io.scrapers import GoogleScraper

class GoogleScraper:
    def __init__(self, geo: str = "PE", language: str = "es"):
        """Initialize Google scraper with geo-targeting."""
        
    async def get_suggestions(
        self, 
        keyword: str, 
        limit: int = 200
    ) -> list[dict]:
        """
        Get autocomplete suggestions for keyword.
        
        Args:
            keyword: Base keyword
            limit: Maximum suggestions
            
        Returns:
            List of suggestion dictionaries
        """
```

**Example Usage:**

```python
import asyncio
from src.io.scrapers import GoogleScraper

async def get_suggestions():
    scraper = GoogleScraper(geo="PE", language="es")
    
    suggestions = await scraper.get_suggestions(
        keyword="limpieza piscina",
        limit=100
    )
    
    for suggestion in suggestions[:5]:
        print(f"Keyword: {suggestion['keyword']}")
        print(f"Source: {suggestion['source']}")
        
    await scraper.close()

asyncio.run(get_suggestions())
```

## 🎯 Scoring System

### StandardizedScorer (Production)

Production-ready scorer with frozen formulas.

```python
from src.core.standardized_scoring import StandardizedScorer
from src.ml.pipeline_config import PRODUCTION_SCORING_FORMULA

class StandardizedScorer:
    def __init__(
        self, 
        frozen_formula: FrozenScoringFormula = PRODUCTION_SCORING_FORMULA,
        run_id: str = ""
    ):
        """Initialize with frozen scoring formula."""
        
    def score_batch(
        self, 
        keywords: list[dict], 
        geo: str, 
        language: str
    ) -> tuple[list[dict], ScoringMetadata]:
        """
        Score a batch of keywords with standardized process.
        
        Args:
            keywords: List of keyword data
            geo: Geographic market
            language: Language market
            
        Returns:
            (scored_keywords, scoring_metadata)
        """
```

**Frozen Scoring Formula v1.0.0:**

```python
# Formula specification (immutable)
score = (
    norm(relevance) * 0.45 +  # Primary ranking factor
    norm(volume) * 0.35 +     # Search volume importance
    (1 - norm(competition)) * 0.10 +  # Competition (inverted)
    norm(trend) * 0.10        # Trend momentum
) * 100

# Usage example
from src.core.standardized_scoring import StandardizedScorer

scorer = StandardizedScorer()
keywords = [
    {
        "keyword": "limpieza piscina",
        "volume": 1200,
        "competition": 0.4,
        "trend_score": 75
    }
]

scored_keywords, metadata = scorer.score_batch(keywords, "PE", "es")

print(f"Score: {scored_keywords[0]['score']}")
print(f"Formula version: {metadata.frozen_formula.VERSION}")
```

### KeywordScorer (Legacy)

Legacy scorer for backward compatibility.

```python
from src.core.scoring import KeywordScorer

class KeywordScorer:
    def __init__(self, geo: str = "PE", intent_focus: str = "transactional"):
        """Initialize legacy scorer."""
        
    def score_keywords(
        self, 
        keywords: list[dict]
    ) -> list[dict]:
        """Score keywords using legacy algorithm."""
```

## 🤖 ML Pipeline

### SemanticClusterer

Standardized clustering with algorithm priority.

```python
from src.ml.clustering import SemanticClusterer

class SemanticClusterer:
    def __init__(self, config: StandardClusteringConfig):
        """Initialize with standardized configuration."""
        
    def cluster_keywords(
        self, 
        keywords: list[dict]
    ) -> tuple[dict, dict]:
        """
        Cluster keywords using algorithm priority.
        
        Algorithm Priority:
        1. HDBSCAN (density-based)
        2. KMeans (centroid-based)  
        3. Manual (rule-based)
        
        Returns:
            (clusters, metadata)
        """
```

**Configuration:**

```python
from src.ml.pipeline_config import StandardClusteringConfig

# Standard configuration
config = StandardClusteringConfig(
    embedding_model="sentence-transformers/all-MiniLM-L6-v2",
    algorithm_priority=["hdbscan", "kmeans", "manual"],
    hdbscan_min_cluster_size=3,
    hdbscan_min_samples=2,
    kmeans_random_state=42,
    cache_enabled=True
)

clusterer = SemanticClusterer(config)
clusters, metadata = clusterer.cluster_keywords(keywords)
```

### FrozenScoringFormula

Immutable scoring configuration.

```python
from src.ml.pipeline_config import FrozenScoringFormula, PRODUCTION_SCORING_FORMULA

@dataclass(frozen=True)
class FrozenScoringFormula:
    VERSION: str = "1.0.0"
    
    # Frozen weights (cannot be modified)
    RELEVANCE_WEIGHT: float = 0.45
    VOLUME_WEIGHT: float = 0.35
    COMPETITION_WEIGHT: float = 0.10
    TREND_WEIGHT: float = 0.10
    
    # Intent multipliers
    INTENT_BASE_MULTIPLIER: float = 0.9
    INTENT_COMMERCIAL_BOOST: float = 0.15
    INTENT_TRANSACTIONAL_BOOST: float = 0.20

# Usage
formula = PRODUCTION_SCORING_FORMULA
print(f"Version: {formula.VERSION}")
print(f"Relevance weight: {formula.RELEVANCE_WEIGHT}")
```

## 📤 Export System

### StandardizedExporter

Production export system with fixed formats.

```python
from src.io.export_standards import StandardizedExporter, PRODUCTION_EXPORT_STANDARD

class StandardizedExporter:
    def __init__(
        self, 
        export_dir: str | Path = "exports",
        standard: ExportStandard = PRODUCTION_EXPORT_STANDARD
    ):
        """Initialize with export standards."""
        
    def export_keywords_csv(
        self,
        keywords: list[dict],
        run_id: str = "",
        geo: str = "",
        language: str = "",
        transparency_mode: bool = False
    ) -> tuple[str, ExportMetadata]:
        """
        Export to standardized CSV format.
        
        Returns:
            (filepath, export_metadata)
        """
```

**Standard Column Order:**

```python
STANDARD_COLUMNS = [
    "keyword",           # Primary identifier
    "score",            # Composite score (0-100)
    "volume",           # Search volume
    "competition",      # Competition (0-1)
    "trend_score",      # Trend momentum
    "intent",           # Intent classification
    "intent_probability", # Intent confidence
    "geo",              # Geographic market
    "language",         # Language code
    "source",           # Data source
    "data_source",      # Source system
    "cluster_id",       # Cluster assignment
    "cluster_label",    # Cluster name
    "run_id",           # Run identifier
    "created_at",       # Creation timestamp
    "updated_at"        # Last update
]

# Usage example
exporter = StandardizedExporter()

filepath, metadata = exporter.export_keywords_csv(
    keywords=keywords,
    run_id="run_001",
    geo="PE",
    language="es",
    transparency_mode=True  # Include scoring details
)

print(f"Exported to: {filepath}")
print(f"Records: {metadata.record_count}")
print(f"Version: {metadata.export_version}")
```

## 📊 Logging System

### Enhanced Enterprise Logging

Structured JSON logging with correlation IDs.

```python
from src.platform.enhanced_logging import (
    setup_enhanced_logging,
    get_structured_logger,
    set_log_context,
    ErrorClassification
)

# Setup logging
setup_enhanced_logging(
    run_id="run_001",
    level="INFO",
    service_name="keyword-intel",
    environment="production"
)

# Get structured logger
logger = get_structured_logger(__name__)

# Log with context
set_log_context(
    operation="keyword_processing",
    component="main"
)

logger.info("Processing started", batch_size=100)

# Log with error classification
error_classification = ErrorClassification(
    category="NETWORK",
    severity="MEDIUM",
    recoverable=True,
    component="scraper"
)

logger.error(
    "API timeout occurred",
    error_classification=error_classification,
    timeout_seconds=30
)
```

**Log Format:**

```json
{
  "@timestamp": "2025-09-16T10:43:27.803146+00:00",
  "@version": "2.0.0",
  "service": "keyword-intel",
  "level": "INFO",
  "message": "Processing started",
  "correlation": {
    "correlation_id": "75d491fb-bd74-4a4f-bd41-a665fbe017c9",
    "run_id": "run_001",
    "operation": "keyword_processing",
    "component": "main"
  },
  "source": {
    "file": "main.py",
    "function": "process_keywords",
    "line": 123
  },
  "performance": {
    "memory_mb": 128.42,
    "cpu_percent": 15.5
  },
  "extra": {
    "batch_size": 100
  }
}
```

## 🗄️ Database Schema

### StandardizedSchema v2.0.0

Production database schema with constraints.

```python
from src.db.standardized_schema import StandardizedSchema

class StandardizedSchema:
    VERSION = "2.0.0"
    
    def initialize_database(self) -> None:
        """Initialize standardized database schema."""
        
    def create_run_v2(self, run_data: dict) -> str:
        """Create new run with v2.0 schema."""
        
    def insert_keyword_v2(self, keyword_data: dict) -> int:
        """Insert keyword with v2.0 schema."""
        
    def get_keywords_by_run_v2(self, run_id: str) -> list[dict]:
        """Get keywords by run with v2.0 schema."""
```

**Schema Tables:**

```sql
-- Runs table
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    profile TEXT NOT NULL,
    geo TEXT NOT NULL,
    language TEXT NOT NULL,
    seeds TEXT NOT NULL,        -- JSON array
    target_raw INTEGER,
    target_filtered INTEGER,
    target_clusters INTEGER,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    status TEXT DEFAULT 'running',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(id)
);

-- Keywords table  
CREATE TABLE IF NOT EXISTS keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    keyword TEXT NOT NULL,
    score REAL,
    volume INTEGER,
    competition REAL,
    trend_score REAL,
    intent TEXT,
    intent_probability REAL,
    geo TEXT NOT NULL,
    language TEXT NOT NULL,
    source TEXT,
    data_source TEXT,
    cluster_id TEXT,
    cluster_label TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES runs(id),
    UNIQUE(run_id, keyword)
);

-- Performance indexes (21 total)
CREATE INDEX IF NOT EXISTS idx_keywords_run_id ON keywords(run_id);
CREATE INDEX IF NOT EXISTS idx_keywords_score ON keywords(score DESC);
CREATE INDEX IF NOT EXISTS idx_keywords_geo_lang ON keywords(geo, language);
-- ... additional indexes
```

## ⚙️ Configuration API

### Settings Management

Centralized configuration with validation.

```python
from src.platform.settings import load_config, validate_config

# Load configuration
config = load_config("config/config.yaml")

# Validate configuration
is_valid, errors = validate_config(config)
if not is_valid:
    print("Configuration errors:", errors)

# Access configuration values
geo = config.get("run", {}).get("geo", "PE")
seeds = config.get("run", {}).get("seeds", [])
scoring_weights = config.get("scoring", {}).get("weights", {})
```

**Configuration Structure:**

```yaml
project:
  name: "keyword-intel"
  version: "2.0.0"

run:
  geo: "PE"
  language: "es"
  seeds: ["keyword1", "keyword2"]
  target:
    raw: 2000
    filtered: 400
    clusters: 30

scoring:
  weights:
    relevance: 0.45  # Frozen
    volume: 0.35     # Frozen
    competition: 0.10 # Frozen
    trend: 0.10      # Frozen

ml:
  embeddings:
    enabled: true
    model_name: "sentence-transformers/all-MiniLM-L6-v2"
  clustering:
    algo: "hdbscan"
    min_cluster_size: "auto"

logging:
  level: "INFO"
  json_format: true
  correlation_enabled: true
```

## ❌ Error Handling

### Error Classification System

Structured error handling with automatic classification.

```python
from src.platform.enhanced_logging import ErrorClassification

# Error categories
ERROR_CATEGORIES = {
    "SYSTEM": "Hardware, OS, resource issues",
    "USER": "Input validation, user errors",
    "NETWORK": "Connection, timeout, API issues", 
    "DATA": "Database, schema, integrity issues",
    "CONFIG": "Configuration, settings issues",
    "SECURITY": "Authentication, authorization issues"
}

# Severity levels
SEVERITY_LEVELS = {
    "CRITICAL": "System unusable",
    "HIGH": "Major functionality impacted",
    "MEDIUM": "Reduced functionality", 
    "LOW": "Minor issues, warnings"
}

# Create error classification
error = ErrorClassification(
    category="NETWORK",
    severity="MEDIUM",
    recoverable=True,
    component="google_scraper",
    error_code="NET_001"
)
```

### Exception Handling

Custom exceptions with automatic classification.

```python
from src.platform.exceptions_enterprise import (
    ScoringError,
    NetworkError,
    ConfigError,
    DataError
)

try:
    # Risky operation
    result = api_call()
except NetworkError as e:
    logger.error(
        "Network operation failed",
        error_classification=create_network_error("api_client"),
        error_details=str(e)
    )
    # Implement retry logic
    
except ScoringError as e:
    logger.error(
        "Scoring calculation failed",
        error_classification=create_data_error("scorer"),
        error_details=str(e)
    )
    # Fallback to legacy scorer
```

## 📋 API Examples

### Complete Keyword Research Pipeline

```python
import asyncio
from src.main import KeywordFinder
from src.platform.settings import load_config
from src.platform.enhanced_logging import setup_enhanced_logging

async def full_pipeline_example():
    # Setup logging
    setup_enhanced_logging(
        run_id="example_001",
        level="INFO",
        service_name="keyword-intel"
    )
    
    # Load configuration
    config = load_config("config/config.yaml")
    
    # Initialize keyword finder
    finder = KeywordFinder(config)
    
    try:
        # Find keywords
        keywords, metadata = await finder.find_keywords(
            seeds=["limpieza piscina", "mantenimiento piscina"],
            limit=500,
            existing_mode=False
        )
        
        print(f"✅ Found {len(keywords)} keywords")
        print(f"✅ Clusters: {metadata.get('clusters', 0)}")
        print(f"✅ Top keyword: {keywords[0]['keyword']} (score: {keywords[0]['score']})")
        
        # Export results
        from src.io.export_standards import StandardizedExporter
        exporter = StandardizedExporter()
        
        filepath, export_metadata = exporter.export_keywords_csv(
            keywords=keywords,
            run_id="example_001",
            geo="PE",
            language="es",
            transparency_mode=True
        )
        
        print(f"✅ Exported to: {filepath}")
        print(f"✅ Export version: {export_metadata.export_version}")
        
    except Exception as e:
        print(f"❌ Pipeline failed: {e}")
        
    finally:
        # Cleanup
        await finder.cleanup()

# Run the example
asyncio.run(full_pipeline_example())
```

### Custom Scoring Example

```python
from src.core.standardized_scoring import StandardizedScorer
from src.ml.pipeline_config import FrozenScoringFormula

# Create custom formula (for testing only)
custom_formula = FrozenScoringFormula(
    VERSION="1.1.0-test",
    RELEVANCE_WEIGHT=0.50,  # Increased relevance
    VOLUME_WEIGHT=0.30,
    COMPETITION_WEIGHT=0.10,
    TREND_WEIGHT=0.10
)

# Initialize scorer with custom formula
scorer = StandardizedScorer(frozen_formula=custom_formula)

# Score keywords
test_keywords = [
    {
        "keyword": "test keyword",
        "volume": 1000,
        "competition": 0.5,
        "trend_score": 80
    }
]

scored_keywords, metadata = scorer.score_batch(test_keywords, "PE", "es")

print(f"Custom score: {scored_keywords[0]['score']}")
print(f"Formula version: {metadata.frozen_formula.VERSION}")
```

## 🔍 Testing API

### Unit Testing

```python
import pytest
from src.core.standardized_scoring import StandardizedScorer

class TestStandardizedScoring:
    def test_frozen_formula(self):
        """Test frozen formula produces consistent results."""
        scorer = StandardizedScorer()
        
        keywords = [{"keyword": "test", "volume": 100, "competition": 0.5, "trend_score": 50}]
        
        # Score multiple times
        result1, _ = scorer.score_batch(keywords, "PE", "es")
        result2, _ = scorer.score_batch(keywords, "PE", "es")
        
        assert result1[0]["score"] == result2[0]["score"], "Frozen formula must be deterministic"
        
    def test_score_validation(self):
        """Test score is within valid range."""
        scorer = StandardizedScorer()
        
        keywords = [{"keyword": "test", "volume": 1000, "competition": 0.3, "trend_score": 80}]
        result, _ = scorer.score_batch(keywords, "PE", "es")
        
        score = result[0]["score"]
        assert 0 <= score <= 100, f"Score {score} must be between 0-100"
```

### Integration Testing

```python
import pytest
import asyncio
from src.main import KeywordFinder

@pytest.mark.asyncio
async def test_end_to_end_pipeline():
    """Test complete keyword research pipeline."""
    config = {"run": {"geo": "PE", "language": "es"}}
    finder = KeywordFinder(config)
    
    try:
        keywords, metadata = await finder.find_keywords(
            seeds=["test"],
            limit=10,
            existing_mode=True
        )
        
        assert len(keywords) > 0, "Should find keywords"
        assert all("score" in kw for kw in keywords), "All keywords should have scores"
        
    finally:
        await finder.cleanup()
```

## 📚 Additional Resources

### Documentation Links

- **Configuration Guide**: [CONFIGURATION.md](CONFIGURATION.md)
- **Deployment Guide**: [DEPLOYMENT.md](DEPLOYMENT.md)  
- **Troubleshooting**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Contributing**: [CONTRIBUTING.md](CONTRIBUTING.md)

### Code Examples

- **Examples Directory**: `/examples/`
- **Test Cases**: `/tests/`
- **Demo Scripts**: `/tools/demo.py`

### API Versioning

The API follows semantic versioning:

- **Major Version**: Breaking changes to API
- **Minor Version**: New features, backward compatible
- **Patch Version**: Bug fixes, no API changes

Current version: **v2.0.0** (Production Ready)