import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from .export_standards import PRODUCTION_EXPORT_STANDARD, StandardizedExporter

logger = logging.getLogger(__name__)


class KeywordExporter:
    """
    Legacy keyword exporter with PR-05 standardization integration.

    This class maintains backward compatibility while using the new
    StandardizedExporter for consistent export formats.
    """

    def __init__(self, export_dir: str = "exports"):
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)

        # Use standardized exporter for new exports
        self.standardized_exporter = StandardizedExporter(
            export_dir=self.export_dir, standard=PRODUCTION_EXPORT_STANDARD
        )

    def export_to_csv(
        self,
        keywords: list[dict[str, Any]],
        filename: str | None = None,
        scoring_metadata: dict[str, Any] | None = None,
        run_id: str = "",
        geo: str = "",
        language: str = "",
        transparency_mode: bool = True,
    ):
        """
        Export keywords to standardized CSV format.

        Args:
            keywords: List of keyword dictionaries
            filename: Optional filename, will auto-generate if None
            scoring_metadata: Optional scoring metadata for transparency
            run_id: Run identifier for tracking
            geo: Geographic market
            language: Language code
            transparency_mode: Include scoring transparency columns

        Returns:
            str: Path to exported file
        """
        try:
            # Use standardized exporter for consistent format
            filepath, export_metadata = self.standardized_exporter.export_keywords_csv(
                keywords=keywords,
                run_id=run_id,
                geo=geo,
                language=language,
                transparency_mode=transparency_mode,
                filename=filename,
            )

            logger.info(
                "Standardized CSV export complete: %s keywords " "exported to %s (v%s)",
                export_metadata.record_count,
                filepath,
                export_metadata.export_version,
            )

            return filepath

        except OSError as e:
            logger.error("CSV export failed: %s", e)
            # Fallback to legacy export for backward compatibility
            return self._legacy_export_to_csv(keywords, filename, scoring_metadata)

    def _legacy_export_to_csv(
        self,
        keywords: list[dict[str, Any]],
        filename: str | None = None,
        scoring_metadata: dict[str, Any] | None = None,
    ):
        """Legacy CSV export method for backward compatibility."""
        if not filename:
            filename = f"keyword_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        filepath = self.export_dir / filename

        try:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                # PR-04: Standardized column order and names
                fieldnames = [
                    "keyword",
                    "score",
                    "volume",
                    "competition",
                    "trend",
                    "intent",
                    "intent_prob",
                    "geo",
                    "language",
                    "source",
                    "data_source",
                    "cluster_id",
                    "run_id",
                    "updated_at",
                ]

                # Add scoring transparency fields if available
                if scoring_metadata:
                    fieldnames.extend(
                        [
                            "relevance_raw",
                            "relevance_norm",
                            "volume_norm",
                            "competition_norm",
                            "trend_norm",
                            "scoring_version",
                        ]
                    )

                writer = csv.DictWriter(f, fieldnames=fieldnames)

                # Write header with scoring metadata comment
                if scoring_metadata:
                    # Write JSON metadata as comment lines
                    import json

                    export_metadata = {
                        "scoring_metadata": scoring_metadata,
                        "export_timestamp": datetime.now().isoformat(),
                        "export_format": "CSV",
                        "standardized_scoring": "v1.0.0",
                    }
                    f.write(
                        f"# Scoring Metadata: {json.dumps(export_metadata, separators=(',', ':'))}\n"
                    )
                    f.write(f"# Generated: {datetime.now().isoformat()}\n")
                    f.write("# Standard: PR-04 Standardized Export Format v1.0.0\n")

                writer.writeheader()

                for kw in keywords:
                    # Ensure all required fields exist with defaults
                    row = {
                        "keyword": kw.get("keyword", ""),
                        "score": kw.get("score", 0),
                        "volume": kw.get("volume", 0),
                        "competition": kw.get("competition", 0),
                        "trend": kw.get("trend_score", 0),
                        "intent": kw.get("intent", "informational"),
                        "intent_prob": kw.get("intent_prob_transactional", 0.0),
                        "geo": kw.get("geo", ""),
                        "language": kw.get("language", ""),
                        "source": kw.get("source", "autocomplete"),
                        "data_source": kw.get("data_source", "heuristic"),
                        "cluster_id": kw.get("cluster_id", ""),
                        "run_id": kw.get("run_id", ""),
                        "updated_at": kw.get("updated_at", datetime.now().isoformat()),
                    }

                    # Add transparency fields if available
                    if scoring_metadata:
                        row.update(
                            {
                                "relevance_raw": kw.get("relevance_raw", ""),
                                "relevance_norm": kw.get("relevance_norm", ""),
                                "volume_norm": kw.get("volume_norm", ""),
                                "competition_norm": kw.get("competition_norm", ""),
                                "trend_norm": kw.get("trend_norm", ""),
                                "scoring_version": kw.get("scoring_version", ""),
                            }
                        )

                    writer.writerow(row)

            logging.info("CSV report with %s keywords exported to %s", len(keywords), filepath)
            return str(filepath)

        except OSError as e:
            logging.error("Error exporting CSV: %s", e)
            return ""

    def export_to_pdf(
        self, keywords: list[dict[str, Any]], filename: str | None = None, title: str = "Report"
    ):
        """Export keywords to PDF (placeholder implementation)."""
        if not filename:
            filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = self.export_dir / filename
        try:
            content = f"Report: {title}\nKeywords: {len(keywords)}"
            filepath.write_text(content, encoding="utf-8")
            return str(filepath)
        except OSError as e:
            logging.error("Error exporting PDF: %s", e)
            return ""

    def export_briefs(
        self,
        clusters: dict[str, list[dict[str, Any]]],
        dirname: str | None = None,
        geo: str | None = None,
    ):
        """Export cluster-based SEO briefs."""
        if not dirname:
            geo_suffix = f"_{geo}" if geo else ""
            dirname = f"briefs_{datetime.now().strftime('%Y%m%d_%H%M%S')}{geo_suffix}"
        briefs_dir = self.export_dir / dirname
        briefs_dir.mkdir(parents=True, exist_ok=True)

        try:
            for cluster_key, items in clusters.items():
                if items:
                    content = f"# {cluster_key}\n\nKeywords: {len(items)}\n"
                    (briefs_dir / f"{cluster_key}.md").write_text(content, encoding="utf-8")
            return str(briefs_dir)
        except OSError as e:
            logging.error("Error exporting briefs: %s", e)
            return ""

    def export_cluster_report(
        self,
        clusters: dict[str, list[dict[str, Any]]],
        filename: str | None = None,
        run_id: str = "",
        geo: str = "",
        language: str = "",
    ):
        """Export detailed cluster report with standardized format."""
        try:
            # Use standardized cluster export
            filepath, export_metadata = self.standardized_exporter.export_cluster_summary(
                clusters=clusters, run_id=run_id, geo=geo, language=language, filename=filename
            )

            logger.info(
                "Standardized cluster report complete: %s clusters " "exported to %s (v%s)",
                export_metadata.record_count,
                filepath,
                export_metadata.export_version,
            )

            return filepath

        except OSError as e:
            logger.error("Cluster export failed: %s", e)
            return self._legacy_export_cluster_report(clusters, filename)

    def _legacy_export_cluster_report(
        self, clusters: dict[str, list[dict[str, Any]]], filename: str | None = None
    ):
        """Legacy cluster export for backward compatibility."""
        if not filename:
            filename = f"cluster_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = self.export_dir / filename

        try:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["cluster_id", "keyword", "score"])
                writer.writeheader()
                for cluster_id, items in clusters.items():
                    for item in items:
                        writer.writerow(
                            {
                                "cluster_id": cluster_id,
                                "keyword": item.get("keyword", ""),
                                "score": item.get("score", 0),
                            }
                        )
            return str(filepath)
        except OSError as e:
            logging.error("Error exporting cluster report: %s", e)
            return ""

    def export_clusters_summary(
        self, clusters: dict[str, list[dict[str, Any]]], filename: str | None = None
    ):
        """Export cluster summary with statistics."""
        if not filename:
            filename = f"clusters_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = self.export_dir / filename

        try:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["cluster_id", "size", "avg_score"])
                writer.writeheader()
                for cluster_id, items in clusters.items():
                    size = len(items)
                    avg_score = (
                        sum(float(item.get("score", 0)) for item in items) / size if size else 0
                    )
                    writer.writerow(
                        {"cluster_id": cluster_id, "size": size, "avg_score": round(avg_score, 2)}
                    )
            return str(filepath)
        except OSError as e:
            logging.error("Error exporting clusters summary: %s", e)
            return ""
