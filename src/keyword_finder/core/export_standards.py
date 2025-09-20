"""
Export standards and configurations for Keyword Finder.
"""

import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ExportMetadata:
    """Metadata for export operations."""

    record_count: int
    export_version: str
    timestamp: str
    format: str


@dataclass
class ExportStandard:
    """Standard configuration for data exports."""

    name: str
    format: str
    include_metadata: bool = True
    include_timestamps: bool = True
    compression: str | None = None
    delimiter: str = ","
    encoding: str = "utf-8"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "format": self.format,
            "include_metadata": self.include_metadata,
            "include_timestamps": self.include_timestamps,
            "compression": self.compression,
            "delimiter": self.delimiter,
            "encoding": self.encoding,
        }


# Production export standard
PRODUCTION_EXPORT_STANDARD = ExportStandard(
    name="production",
    format="csv",
    include_metadata=True,
    include_timestamps=True,
    compression="gzip",
    delimiter=",",
    encoding="utf-8",
)

# Development export standard
DEVELOPMENT_EXPORT_STANDARD = ExportStandard(
    name="development",
    format="csv",
    include_metadata=False,
    include_timestamps=True,
    compression=None,
    delimiter=",",
    encoding="utf-8",
)


class StandardizedExporter:
    """Standardized exporter with configurable standards."""

    def __init__(self, export_dir: Path, standard: ExportStandard):
        self.export_dir = export_dir
        self.standard = standard
        self.export_dir.mkdir(exist_ok=True)

    def export_keywords_csv(
        self,
        keywords: list[dict[str, Any]],
        run_id: str = "",
        geo: str = "",
        language: str = "",
        transparency_mode: bool = True,
        filename: str | None = None,
    ) -> tuple[str, ExportMetadata]:
        """Export keywords to standardized CSV format."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"keyword_analysis_{timestamp}.csv"

        filepath = self.export_dir / filename

        try:
            with open(filepath, "w", newline="", encoding=self.standard.encoding) as f:
                # Standard keyword export columns
                fieldnames = [
                    "keyword",
                    "score",
                    "volume",
                    "competition",
                    "trend_score",
                    "intent",
                    "intent_prob",
                    "geo",
                    "language",
                    "cluster_id",
                    "cluster_label",
                    "source",
                    "category",
                ]

                if transparency_mode:
                    fieldnames.extend(
                        [
                            "volume_weight",
                            "trend_weight",
                            "competition_weight",
                            "run_id",
                            "export_timestamp",
                        ]
                    )

                writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=self.standard.delimiter)
                writer.writeheader()

                export_timestamp = datetime.now().isoformat()

                for keyword in keywords:
                    row = {
                        "keyword": keyword.get("keyword", ""),
                        "score": keyword.get("score", 0),
                        "volume": keyword.get("volume", 0),
                        "competition": keyword.get("competition", 0),
                        "trend_score": keyword.get("trend_score", 0),
                        "intent": keyword.get("intent", ""),
                        "intent_prob": keyword.get("intent_prob", 0),
                        "geo": geo or keyword.get("geo", ""),
                        "language": language or keyword.get("language", ""),
                        "cluster_id": keyword.get("cluster_id", ""),
                        "cluster_label": keyword.get("cluster_label", ""),
                        "source": keyword.get("source", ""),
                        "category": keyword.get("category", ""),
                    }

                    if transparency_mode:
                        row.update(
                            {
                                "volume_weight": keyword.get("volume_weight", 0.4),
                                "trend_weight": keyword.get("trend_weight", 0.4),
                                "competition_weight": keyword.get("competition_weight", 0.2),
                                "run_id": run_id,
                                "export_timestamp": export_timestamp,
                            }
                        )

                    writer.writerow(row)

            metadata = ExportMetadata(
                record_count=len(keywords),
                export_version="2.0",
                timestamp=export_timestamp,
                format="csv",
            )

            return str(filepath), metadata

        except Exception as e:
            raise Exception(f"Failed to export keywords to CSV: {e}") from e

    def export_cluster_summary(
        self,
        clusters: dict[str, list[dict[str, Any]]],
        run_id: str = "",
        geo: str = "",
        language: str = "",
        filename: str | None = None,
    ) -> tuple[str, ExportMetadata]:
        """Export cluster summary with statistics."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"clusters_summary_{timestamp}.csv"

        filepath = self.export_dir / filename

        try:
            with open(filepath, "w", newline="", encoding=self.standard.encoding) as f:
                fieldnames = [
                    "cluster_id",
                    "cluster_label",
                    "size",
                    "avg_score",
                    "avg_volume",
                    "avg_competition",
                    "top_keywords",
                    "run_id",
                    "geo",
                    "language",
                ]

                writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=self.standard.delimiter)
                writer.writeheader()

                export_timestamp = datetime.now().isoformat()
                total_records = 0

                for cluster_id, items in clusters.items():
                    if not items:
                        continue

                    size = len(items)
                    total_records += size

                    avg_score = sum(float(item.get("score", 0)) for item in items) / size
                    avg_volume = sum(int(item.get("volume", 0)) for item in items) / size
                    avg_competition = (
                        sum(float(item.get("competition", 0)) for item in items) / size
                    )

                    # Get top 3 keywords by score
                    sorted_items = sorted(
                        items, key=lambda x: float(x.get("score", 0)), reverse=True
                    )
                    top_keywords = "; ".join(item.get("keyword", "") for item in sorted_items[:3])

                    cluster_label = (
                        items[0].get("cluster_label", cluster_id) if items else cluster_id
                    )

                    writer.writerow(
                        {
                            "cluster_id": cluster_id,
                            "cluster_label": cluster_label,
                            "size": size,
                            "avg_score": round(avg_score, 2),
                            "avg_volume": round(avg_volume, 0),
                            "avg_competition": round(avg_competition, 2),
                            "top_keywords": top_keywords,
                            "run_id": run_id,
                            "geo": geo,
                            "language": language,
                        }
                    )

            metadata = ExportMetadata(
                record_count=total_records,
                export_version="2.0",
                timestamp=export_timestamp,
                format="csv",
            )

            return str(filepath), metadata

        except Exception as e:
            raise Exception(f"Failed to export cluster summary: {e}") from e

    def export_data(self, data: list, filename: str) -> Path:
        """Export data using the configured standard."""
        # This is a placeholder implementation
        # In a real implementation, this would handle different formats
        export_path = self.export_dir / f"{filename}.{self.standard.format}"

        if self.standard.format == "csv":
            self._export_csv(data, export_path)
        elif self.standard.format == "json":
            self._export_json(data, export_path)
        else:
            raise ValueError(f"Unsupported export format: {self.standard.format}")

        return export_path

    def _export_csv(self, data: list, path: Path) -> None:
        """Export data as CSV."""
        if not data:
            return

        import csv

        with open(path, "w", newline="", encoding=self.standard.encoding) as f:
            if isinstance(data[0], dict):
                writer = csv.DictWriter(
                    f, fieldnames=data[0].keys(), delimiter=self.standard.delimiter
                )
                writer.writeheader()
                writer.writerows(data)

    def _export_json(self, data: list, path: Path) -> None:
        """Export data as JSON."""

        with open(path, "w", encoding=self.standard.encoding) as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
