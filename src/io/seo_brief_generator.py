"""
seo_brief_generator.py — Enterprise SEO Brief Generator

Generates SEO briefs for each cluster using templates, context, metrics, and recommendations.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..db.schema import ClusterMetadata, EnhancedKeyword, RunMetadata


class SEOBriefGenerator:
    def __init__(self, template_dir: str | Path):
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(["html", "xml", "md"]),
        )

    def generate_brief(
        self,
        cluster: ClusterMetadata,
        keywords: Sequence[EnhancedKeyword],
        run: RunMetadata,
        output_path: str | Path,
        template_name: str = "seo_brief.md.j2",
        extra: dict[str, Any] | None = None,
    ) -> Path:
        """Render a brief for a cluster and save to output_path."""
        template = self.env.get_template(template_name)
        context = {
            "cluster": cluster,
            "keywords": keywords,
            "run": run,
            # Optionally add metrics/recommendations if present in cluster
            # "metrics": getattr(cluster, "metrics", {}),
            # "recommendations": getattr(cluster, "recommendations", []),
        }
        if extra:
            context.update(extra)
        output = template.render(**context)
        output_path = Path(output_path)
        output_path.write_text(output, encoding="utf-8")
        return output_path

    def generate_all(
        self,
        clusters: Sequence[ClusterMetadata],
        keywords_by_cluster: dict[int, list[EnhancedKeyword]],
        run: RunMetadata,
        output_dir: str | Path,
        template_name: str = "seo_brief.md.j2",
        extra: dict[str, Any] | None = None,
    ) -> list[Path]:
        """Generate briefs for all clusters."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        paths = []
        for cluster in clusters:
            kws = keywords_by_cluster.get(cluster.cluster_id, [])
            fname = f"brief_{cluster.cluster_id}.md"
            path = output_dir / fname
            self.generate_brief(cluster, kws, run, path, template_name, extra)
            paths.append(path)
        return paths
