"""
Export Standardization v1.0.0 for PR-05

This module provides standardized export formats with:
- Fixed column ordering and naming conventions
- Consistent filename formats with versioning
- UTF-8 encoding enforcement
- Export validation and metadata tracking
- Production-ready export standards
"""

from __future__ import annotations

import csv
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExportStandard:
    """Frozen export standard v1.0.0 - Production specification."""
    
    VERSION: str = "1.0.0"
    
    # Standard CSV column order (frozen)
    STANDARD_COLUMNS: tuple[str, ...] = (
        "keyword",
        "score", 
        "volume",
        "competition",
        "trend_score",
        "intent",
        "intent_probability",
        "geo",
        "language", 
        "source",
        "data_source",
        "cluster_id",
        "cluster_label",
        "run_id",
        "created_at",
        "updated_at"
    )
    
    # Extended columns for transparency mode
    TRANSPARENCY_COLUMNS: tuple[str, ...] = (
        "relevance_raw",
        "relevance_normalized", 
        "volume_normalized",
        "competition_normalized",
        "trend_normalized",
        "scoring_version",
        "scoring_formula_version"
    )
    
    # Encoding and format standards
    ENCODING: str = "utf-8"
    LINE_TERMINATOR: str = "\n"
    DELIMITER: str = ","
    QUOTE_CHAR: str = '"'
    
    # Filename conventions
    DATETIME_FORMAT: str = "%Y%m%d_%H%M%S"
    FILENAME_PREFIX: str = "keyword_export"
    CLUSTER_PREFIX: str = "cluster_report"
    SUMMARY_PREFIX: str = "export_summary"


@dataclass
class ExportMetadata:
    """Metadata for export tracking and validation."""
    
    export_id: str
    export_timestamp: datetime
    export_version: str
    format_type: str
    record_count: int
    columns_included: List[str]
    transparency_mode: bool
    run_id: str
    geo: str
    language: str
    source_system: str = "keyword-finder"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "export_id": self.export_id,
            "export_timestamp": self.export_timestamp.isoformat(),
            "export_version": self.export_version,
            "format_type": self.format_type,
            "record_count": self.record_count,
            "columns_included": self.columns_included,
            "transparency_mode": self.transparency_mode,
            "run_id": self.run_id,
            "geo": self.geo,
            "language": self.language,
            "source_system": self.source_system
        }


class StandardizedExporter:
    """
    Standardized exporter implementing PR-05 export canonicalization.
    
    Features:
    - Fixed column ordering per ExportStandard
    - Consistent filename conventions
    - UTF-8 encoding enforcement
    - Export validation and metadata
    - Version tracking and audit trail
    """
    
    def __init__(self, export_dir: str | Path = "exports", standard: ExportStandard | None = None):
        """
        Initialize standardized exporter.
        
        Args:
            export_dir: Directory for exports
            standard: Export standard to use (defaults to production standard)
        """
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)
        self.standard = standard or ExportStandard()
        
    def generate_filename(
        self, 
        prefix: str, 
        run_id: str = "", 
        geo: str = "", 
        language: str = "",
        extension: str = ".csv"
    ) -> str:
        """
        Generate standardized filename.
        
        Format: {prefix}_{timestamp}_{run_id}_{geo}_{lang}{extension}
        Example: keyword_export_20250916_143022_run_001_PE_es.csv
        """
        timestamp = datetime.now().strftime(self.standard.DATETIME_FORMAT)
        parts = [prefix, timestamp]
        
        if run_id:
            parts.append(run_id)
        if geo:
            parts.append(geo)
        if language:
            parts.append(language)
            
        return "_".join(parts) + extension
    
    def normalize_keyword_data(self, keyword: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize keyword data to standard format.
        
        Args:
            keyword: Raw keyword data
            
        Returns:
            Normalized keyword data with standard fields
        """
        return {
            "keyword": str(keyword.get("keyword", "")),
            "score": float(keyword.get("score", 0.0)),
            "volume": int(keyword.get("volume", 0)),
            "competition": float(keyword.get("competition", 0.0)),
            "trend_score": float(keyword.get("trend_score", keyword.get("trend", 0.0))),
            "intent": str(keyword.get("intent", "informational")),
            "intent_probability": float(keyword.get("intent_prob", keyword.get("intent_probability", 0.0))),
            "geo": str(keyword.get("geo", "")),
            "language": str(keyword.get("language", "")),
            "source": str(keyword.get("source", "unknown")),
            "data_source": str(keyword.get("data_source", "heuristic")),
            "cluster_id": str(keyword.get("cluster_id", "")),
            "cluster_label": str(keyword.get("cluster_label", "")),
            "run_id": str(keyword.get("run_id", "")),
            "created_at": keyword.get("created_at", datetime.now().isoformat()),
            "updated_at": keyword.get("updated_at", datetime.now().isoformat())
        }
    
    def add_transparency_data(self, keyword: Dict[str, Any], normalized: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add transparency columns if available.
        
        Args:
            keyword: Original keyword data
            normalized: Normalized keyword data
            
        Returns:
            Keyword data with transparency fields added
        """
        transparency_data = {
            "relevance_raw": keyword.get("relevance_raw", ""),
            "relevance_normalized": keyword.get("relevance_norm", ""),
            "volume_normalized": keyword.get("volume_norm", ""),
            "competition_normalized": keyword.get("competition_norm", ""),
            "trend_normalized": keyword.get("trend_norm", ""),
            "scoring_version": keyword.get("scoring_version", ""),
            "scoring_formula_version": keyword.get("scoring_formula_version", "")
        }
        
        return {**normalized, **transparency_data}
    
    def validate_export_data(self, keywords: List[Dict[str, Any]]) -> tuple[bool, List[str]]:
        """
        Validate export data against standards.
        
        Args:
            keywords: List of keyword data to validate
            
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        
        if not keywords:
            errors.append("No keywords provided for export")
            return False, errors
        
        # Check required fields
        required_fields = ["keyword", "score"]
        for i, kw in enumerate(keywords):
            for field in required_fields:
                if field not in kw or kw[field] == "":
                    errors.append(f"Row {i}: Missing required field '{field}'")
        
        # Check data types
        for i, kw in enumerate(keywords):
            try:
                float(kw.get("score", 0))
            except (ValueError, TypeError):
                errors.append(f"Row {i}: Invalid score value")
                
            try:
                int(kw.get("volume", 0))
            except (ValueError, TypeError):
                errors.append(f"Row {i}: Invalid volume value")
        
        return len(errors) == 0, errors
    
    def export_keywords_csv(
        self, 
        keywords: List[Dict[str, Any]], 
        run_id: str = "",
        geo: str = "",
        language: str = "",
        transparency_mode: bool = False,
        filename: str | None = None
    ) -> tuple[str, ExportMetadata]:
        """
        Export keywords to standardized CSV format.
        
        Args:
            keywords: List of keyword data
            run_id: Run identifier
            geo: Geographic market
            language: Language code
            transparency_mode: Include transparency columns
            filename: Custom filename (optional)
            
        Returns:
            (filepath, export_metadata)
        """
        # Validate input data
        is_valid, errors = self.validate_export_data(keywords)
        if not is_valid:
            raise ValueError(f"Export validation failed: {'; '.join(errors)}")
        
        # Generate filename
        if not filename:
            filename = self.generate_filename(
                self.standard.FILENAME_PREFIX, run_id, geo, language
            )
        
        filepath = self.export_dir / filename
        
        # Determine columns
        columns = list(self.standard.STANDARD_COLUMNS)
        if transparency_mode:
            columns.extend(self.standard.TRANSPARENCY_COLUMNS)
        
        # Create export metadata
        export_metadata = ExportMetadata(
            export_id=f"exp_{run_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            export_timestamp=datetime.now(),
            export_version=self.standard.VERSION,
            format_type="CSV",
            record_count=len(keywords),
            columns_included=columns,
            transparency_mode=transparency_mode,
            run_id=run_id,
            geo=geo,
            language=language
        )
        
        try:
            with open(
                filepath, 
                "w", 
                newline="", 
                encoding=self.standard.ENCODING
            ) as f:
                # Write metadata header
                f.write(f"# Export Metadata: {json.dumps(export_metadata.to_dict(), separators=(',', ':'))}\n")
                f.write(f"# Export Standard Version: {self.standard.VERSION}\n")
                f.write(f"# Generated: {datetime.now().isoformat()}\n")
                f.write("# Specification: PR-05 Export Canonicalization\n")
                
                # Write CSV data
                writer = csv.DictWriter(
                    f,
                    fieldnames=columns,
                    delimiter=self.standard.DELIMITER,
                    quotechar=self.standard.QUOTE_CHAR,
                    lineterminator=self.standard.LINE_TERMINATOR
                )
                
                writer.writeheader()
                
                for keyword in keywords:
                    # Normalize data
                    normalized = self.normalize_keyword_data(keyword)
                    
                    # Add transparency data if enabled
                    if transparency_mode:
                        normalized = self.add_transparency_data(keyword, normalized)
                    
                    # Filter to include only standard columns
                    row = {col: normalized.get(col, "") for col in columns}
                    writer.writerow(row)
            
            logger.info(f"Standardized CSV export complete: {len(keywords)} keywords → {filepath}")
            return str(filepath), export_metadata
            
        except Exception as e:
            logger.error(f"Export failed: {e}")
            raise
    
    def export_cluster_summary(
        self,
        clusters: Dict[str, List[Dict[str, Any]]],
        run_id: str = "",
        geo: str = "",
        language: str = "",
        filename: str | None = None
    ) -> tuple[str, ExportMetadata]:
        """
        Export cluster summary with standardized format.
        
        Args:
            clusters: Dictionary of cluster_id -> keywords
            run_id: Run identifier  
            geo: Geographic market
            language: Language code
            filename: Custom filename (optional)
            
        Returns:
            (filepath, export_metadata)
        """
        # Generate filename
        if not filename:
            filename = self.generate_filename(
                self.standard.CLUSTER_PREFIX, run_id, geo, language
            )
        
        filepath = self.export_dir / filename
        
        # Prepare cluster summary data
        cluster_data = []
        for cluster_id, keywords in clusters.items():
            if keywords:
                total_score = sum(float(kw.get("score", 0)) for kw in keywords)
                avg_score = total_score / len(keywords)
                total_volume = sum(int(kw.get("volume", 0)) for kw in keywords)
                avg_volume = total_volume / len(keywords)
                
                cluster_data.append({
                    "cluster_id": cluster_id,
                    "cluster_size": len(keywords),
                    "avg_score": round(avg_score, 2),
                    "total_volume": total_volume,
                    "avg_volume": round(avg_volume, 0),
                    "top_keyword": keywords[0].get("keyword", "") if keywords else "",
                    "run_id": run_id,
                    "geo": geo,
                    "language": language,
                    "created_at": datetime.now().isoformat()
                })
        
        # Create metadata
        export_metadata = ExportMetadata(
            export_id=f"cluster_{run_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            export_timestamp=datetime.now(),
            export_version=self.standard.VERSION,
            format_type="CSV_CLUSTER_SUMMARY",
            record_count=len(cluster_data),
            columns_included=["cluster_id", "cluster_size", "avg_score", "total_volume", "avg_volume", "top_keyword"],
            transparency_mode=False,
            run_id=run_id,
            geo=geo,
            language=language
        )
        
        try:
            with open(
                filepath,
                "w", 
                newline="",
                encoding=self.standard.ENCODING
            ) as f:
                # Write metadata header
                f.write(f"# Cluster Summary Metadata: {json.dumps(export_metadata.to_dict(), separators=(',', ':'))}\n")
                f.write(f"# Export Standard Version: {self.standard.VERSION}\n")
                f.write(f"# Generated: {datetime.now().isoformat()}\n")
                
                # Write CSV data
                if cluster_data:
                    writer = csv.DictWriter(f, fieldnames=cluster_data[0].keys())
                    writer.writeheader()
                    writer.writerows(cluster_data)
            
            logger.info(f"Cluster summary export complete: {len(cluster_data)} clusters → {filepath}")
            return str(filepath), export_metadata
            
        except Exception as e:
            logger.error(f"Cluster export failed: {e}")
            raise


# Production standard instance
PRODUCTION_EXPORT_STANDARD = ExportStandard()