import csv
import logging
from datetime import datetime
from pathlib import Path


class KeywordExporter:
    def __init__(self, export_dir: str = "exports"):
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def export_to_csv(self, keywords, filename=None):
        if not filename:
            filename = f"keyword_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = self.export_dir / filename
        try:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                fieldnames = ["keyword", "score", "volume", "competition"]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for kw in keywords:
                    writer.writerow(
                        {
                            "keyword": kw.get("keyword", ""),
                            "score": kw.get("score", 0),
                            "volume": kw.get("volume", 0),
                            "competition": kw.get("competition", 0),
                        }
                    )
            return str(filepath)
        except Exception as e:
            logging.error(f"Error: {e}")
            return ""

    def export_to_pdf(self, keywords, filename=None, title="Report"):
        if not filename:
            filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = self.export_dir / filename
        try:
            content = f"Report: {title}\nKeywords: {len(keywords)}"
            filepath.write_text(content)
            return str(filepath)
        except Exception:
            return ""

    def export_briefs(self, clusters, dirname=None, geo=None):
        if not dirname:
            dirname = f"briefs_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        briefs_dir = self.export_dir / dirname
        briefs_dir.mkdir(parents=True, exist_ok=True)
        for cluster_key, items in clusters.items():
            if items:
                content = f"# {cluster_key}\n\nKeywords: {len(items)}\n"
                (briefs_dir / f"{cluster_key}.md").write_text(content)
        return str(briefs_dir)

    def export_cluster_report(self, clusters, filename=None):
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
        except Exception:
            return ""

    def export_clusters_summary(self, clusters, filename=None):
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
        except Exception:
            return ""
