"""
Export standards and configurations for Keyword Finder.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any


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
    encoding="utf-8"
)

# Development export standard
DEVELOPMENT_EXPORT_STANDARD = ExportStandard(
    name="development",
    format="csv",
    include_metadata=False,
    include_timestamps=True,
    compression=None,
    delimiter=",",
    encoding="utf-8"
)


class StandardizedExporter:
    """Standardized exporter with configurable standards."""

    def __init__(self, export_dir: Path, standard: ExportStandard):
        self.export_dir = export_dir
        self.standard = standard
        self.export_dir.mkdir(exist_ok=True)

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
        with open(path, 'w', newline='', encoding=self.standard.encoding) as f:
            if isinstance(data[0], dict):
                writer = csv.DictWriter(f, fieldnames=data[0].keys(),
                                      delimiter=self.standard.delimiter)
                writer.writeheader()
                writer.writerows(data)

    def _export_json(self, data: list, path: Path) -> None:
        """Export data as JSON."""
        import json
        with open(path, 'w', encoding=self.standard.encoding) as f:
            json.dump(data, f, indent=2, ensure_ascii=False)