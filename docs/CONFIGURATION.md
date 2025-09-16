# Production Configuration Guide v2.0.0

This guide covers the standardized configuration system implemented in PR-01.

## Configuration Architecture

### Single Source of Truth: `config/config.yaml`

All system configuration is centralized in a single YAML file with the following structure:

```yaml
# Project metadata
project:
  name: "keyword-intel"
  version: "1.0.0"

# Run configuration
run:
  geo: "PE"                                    # Target country
  language: "es"                              # Target language
  seeds: ["limpieza de piscina"]              # Seed keywords
  target:
    raw: 2000                                 # Target raw keywords
    filtered: 400                             # Target filtered keywords
    clusters: 30                              # Target clusters

# Keyword expansion settings
expansion:
  limit_per_seed: 200                         # Max keywords per seed
  alphabet_soup: true                         # Enable A-Z expansion
  modifiers: ["mejor", "precio", "curso"]     # Keyword modifiers

# Data sources
sources:
  trends: true                                # Enable Google Trends
  ads_volume: false                           # Enable Google Ads API
  data_source_priority: ["ads", "trends", "heuristic"]

# Filtering criteria
filters:
  min_score: 45                               # Minimum quality score
  max_competition: 0.7                        # Maximum competition
  intent_whitelist: ["transactional", "informational"]

# Frozen scoring formula (PR-04)
scoring:
  weights:
    relevance: 0.45                           # Fixed weight
    volume: 0.35                              # Fixed weight
    competition: 0.10                         # Fixed weight (inverted)
    trend: 0.10                               # Fixed weight

# ML pipeline configuration (PR-04)
ml:
  embeddings:
    enabled: true
    model_name: "sentence-transformers/all-MiniLM-L6-v2"
  clustering:
    algo: "hdbscan"                           # HDBSCAN → KMeans → Manual
    min_cluster_size: "auto"
    min_samples: "auto"
  intent_classifier:
    enabled: true

# Enhanced logging (PR-06)
logging:
  level: "INFO"                               # DEBUG, INFO, WARNING, ERROR
  json_format: true                           # Structured JSON logs
  console_enabled: true                       # Console output
  file_enabled: true                          # File logging
  filepath: "logs/run_{run_id}.jsonl"         # Log file path
  correlation_enabled: true                   # Correlation IDs
  performance_metrics: true                   # Include performance data

# Export standards (PR-05)
exports:
  format: "csv"                               # Standard format
  encoding: "utf-8"                           # Fixed encoding
  transparency_mode: true                     # Include scoring details
  metadata_headers: true                      # Include metadata
  column_order: "standard"                    # Fixed column ordering

# Environment-specific settings
environments:
  development:
    log_level: "DEBUG"
    performance_monitoring: true
  production:
    log_level: "INFO" 
    performance_monitoring: false
  test:
    log_level: "ERROR"
    cache_enabled: false
```

## Environment Profiles

### Profile Selection

The system supports multiple environment profiles:

```bash
# Development (default)
python main.py --profile development

# Production
python main.py --profile production

# Test
python main.py --profile test
```

### Profile Inheritance

Profiles inherit from base configuration and override specific settings:

```yaml
# Base settings apply to all profiles
run:
  geo: "PE"
  language: "es"

# Profile-specific overrides
profiles:
  development:
    logging:
      level: "DEBUG"
      console_enabled: true
  
  production:
    logging:
      level: "INFO"
      file_enabled: true
      filepath: "/var/log/keyword-intel/run_{run_id}.jsonl"
  
  test:
    logging:
      level: "ERROR"
    ml:
      embeddings:
        enabled: false  # Faster testing
```

## CLI Configuration Override

### Command Line Priority

CLI arguments override configuration file settings:

```bash
# Override geo setting
python main.py --geo US --language en

# Override seeds
python main.py --seeds "pool cleaning,pool maintenance"

# Override limits
python main.py --limit 500 --clusters 20

# Override log level
python main.py --log-level DEBUG
```

### Configuration Validation

The system validates all configuration on startup:

```python
from src.platform.settings import load_config, validate_config

# Load and validate configuration
config = load_config("config/config.yaml")
is_valid, errors = validate_config(config)

if not is_valid:
    print("Configuration errors:", errors)
```

## Frozen Formulas (PR-04)

### Scoring Formula v1.0.0

The scoring formula is **frozen** and cannot be modified without creating a new version:

```python
# Frozen scoring weights
RELEVANCE_WEIGHT = 0.45    # Primary factor
VOLUME_WEIGHT = 0.35       # Search volume importance  
COMPETITION_WEIGHT = 0.10  # Competition (inverted)
TREND_WEIGHT = 0.10        # Trend momentum

# Formula application
score = (
    norm(relevance) * 0.45 +
    norm(volume) * 0.35 + 
    (1 - norm(competition)) * 0.10 +
    norm(trend) * 0.10
) * 100
```

### Clustering Configuration

Standardized clustering with algorithm priority:

```python
# Algorithm priority (frozen)
CLUSTERING_ALGORITHMS = [
    "hdbscan",     # Primary: density-based
    "kmeans",      # Fallback: centroid-based  
    "manual"       # Final: rule-based
]

# Parameters (standardized)
HDBSCAN_CONFIG = {
    "min_cluster_size": 3,
    "min_samples": 2,
    "metric": "euclidean"
}

KMEANS_CONFIG = {
    "n_clusters": "auto",  # Elbow method
    "random_state": 42,
    "max_iter": 300
}
```

## Export Standards (PR-05)

### Column Ordering

Standardized CSV export with fixed column order:

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
```

### Transparency Mode

Additional columns for scoring transparency:

```python
TRANSPARENCY_COLUMNS = [
    "relevance_raw",         # Raw relevance score
    "relevance_normalized",  # Normalized relevance
    "volume_normalized",     # Normalized volume
    "competition_normalized", # Normalized competition
    "trend_normalized",      # Normalized trend
    "scoring_version",       # Formula version
    "scoring_formula_version" # Implementation version
]
```

## Enterprise Logging (PR-06)

### Structured JSON Format

All logs use standardized JSON format with correlation tracking:

```json
{
  "@timestamp": "2025-09-16T10:43:27.803146+00:00",
  "@version": "2.0.0",
  "service": "keyword-intel",
  "version": "1.0.0",
  "environment": "production",
  "level": "INFO",
  "logger": "keyword_finder",
  "message": "Processing keyword batch",
  "correlation": {
    "correlation_id": "75d491fb-bd74-4a4f-bd41-a665fbe017c9",
    "run_id": "run_20250916_054336",
    "operation": "keyword_processing",
    "component": "main"
  },
  "source": {
    "file": "main.py",
    "line": 123,
    "function": "process_keywords",
    "module": "main"
  },
  "execution": {
    "thread_id": 84760,
    "thread_name": "MainThread",
    "process_id": 73380
  },
  "timing": {
    "created": 1758019407.803146,
    "relative_ms": 142.5999,
    "uptime_seconds": 0.0004513
  },
  "performance": {
    "memory_mb": 28.26,
    "cpu_percent": 0.0,
    "open_files": 1,
    "threads": 1
  },
  "extra": {
    "keywords_processed": 150,
    "batch_size": 50
  }
}
```

### Error Classification

Errors are automatically classified for better incident management:

```python
ERROR_CATEGORIES = {
    "SYSTEM": "Hardware, OS, resource issues",
    "USER": "Input validation, user errors", 
    "NETWORK": "Connection, timeout, API issues",
    "DATA": "Database, schema, integrity issues",
    "CONFIG": "Configuration, settings issues",
    "SECURITY": "Authentication, authorization issues"
}

SEVERITY_LEVELS = {
    "CRITICAL": "System unusable",
    "HIGH": "Major functionality impacted",
    "MEDIUM": "Reduced functionality",
    "LOW": "Minor issues, warnings"
}
```

## Best Practices

### 1. Configuration Management

- **Never hardcode values** - Use config.yaml for all settings
- **Use profiles** for environment-specific configuration
- **Validate configuration** on startup
- **Document all settings** with comments

### 2. Frozen Formulas

- **Never modify frozen formulas** - Create new versions instead
- **Use version tracking** for formula changes
- **Test thoroughly** before freezing new versions
- **Document formula rationale** and validation results

### 3. Export Standards

- **Always use StandardizedExporter** for consistent formatting
- **Include metadata** for audit trails
- **Use transparency mode** for debugging and validation
- **Validate exports** before delivery

### 4. Logging Standards

- **Use structured logging** for all production logs
- **Include correlation IDs** for request tracing
- **Classify errors appropriately** for incident management
- **Monitor performance metrics** for optimization

## Migration Guide

### From v1.x to v2.0

1. **Update configuration**:
   ```bash
   # Backup old config
   cp config.yaml config.yaml.backup
   
   # Use new standardized format
   cp config/config.yaml.template config.yaml
   ```

2. **Update imports**:
   ```python
   # Old
   from src.platform.logging_config_enterprise import setup_logging
   
   # New
   from src.platform.enhanced_logging import setup_enhanced_logging
   ```

3. **Update database schema**:
   ```python
   # Enable standardized schema
   db = KeywordDatabase(use_standardized_schema=True)
   ```

4. **Update exports**:
   ```python
   # Old
   exporter = KeywordExporter()
   
   # New (with standards)
   from src.io.export_standards import StandardizedExporter
   exporter = StandardizedExporter()
   ```

## Troubleshooting

### Common Configuration Issues

1. **Invalid YAML syntax**:
   ```bash
   python -c "import yaml; yaml.safe_load(open('config/config.yaml'))"
   ```

2. **Missing required fields**:
   ```python
   from src.platform.settings import validate_config
   is_valid, errors = validate_config(config)
   print(errors)
   ```

3. **Profile conflicts**:
   ```bash
   python main.py --profile production --debug-config
   ```

### Performance Optimization

1. **Enable caching**:
   ```yaml
   ml:
     embeddings:
       cache_enabled: true
       cache_ttl: 3600
   ```

2. **Adjust batch sizes**:
   ```yaml
   processing:
     batch_size: 100        # Reduce for memory constraints
     parallel_workers: 4    # Adjust for CPU cores
   ```

3. **Optimize logging**:
   ```yaml
   logging:
     level: "INFO"          # Reduce verbosity in production
     performance_metrics: false  # Disable if not needed
   ```