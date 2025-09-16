"""
test_seo_brief_generator.py — Test for SEOBriefGenerator
"""

from datetime import datetime
from pathlib import Path

from src.db.schema import ClusterMetadata, DataSource, EnhancedKeyword, IntentType, RunMetadata
from src.io.seo_brief_generator import SEOBriefGenerator


def test_generate_brief(tmp_path: Path):
    # Setup test data
    run = RunMetadata(
        run_id="test_run",
        started_at=datetime.now(),
        profile="test",
        geo="US",
        language="en",
        seeds=["seo", "marketing"],
    )
    cluster = ClusterMetadata(
        cluster_id=1,
        label="SEO Tools",
        run_id="test_run",
        keywords_count=3,
        avg_score=0.85,
        avg_volume=1200,
        dominant_intent=IntentType.INFORMATIONAL,
        dominant_data_source=DataSource.ADS_VOLUME,
        created_at=datetime.now(),
    )
    keywords = [
        EnhancedKeyword(
            keyword="seo tool",
            source="seed",
            volume=1000,
            trend_score=0.7,
            competition=0.5,
            score=0.8,
            category="tools",
            intent=IntentType.INFORMATIONAL,
            intent_prob=0.9,
            cluster_id=1,
            cluster_label="SEO Tools",
            geo="US",
            language="en",
            data_source=DataSource.ADS_VOLUME,
            run_id="test_run",
        ),
        EnhancedKeyword(
            keyword="best seo software",
            source="expansion",
            volume=800,
            trend_score=0.6,
            competition=0.6,
            score=0.75,
            category="software",
            intent=IntentType.INFORMATIONAL,
            intent_prob=0.85,
            cluster_id=1,
            cluster_label="SEO Tools",
            geo="US",
            language="en",
            data_source=DataSource.ADS_VOLUME,
            run_id="test_run",
        ),
        EnhancedKeyword(
            keyword="seo audit",
            source="expansion",
            volume=600,
            trend_score=0.5,
            competition=0.4,
            score=0.7,
            category="audit",
            intent=IntentType.INFORMATIONAL,
            intent_prob=0.8,
            cluster_id=1,
            cluster_label="SEO Tools",
            geo="US",
            language="en",
            data_source=DataSource.ADS_VOLUME,
            run_id="test_run",
        ),
    ]
    template_dir = Path(__file__).parent.parent / "templates"
    generator = SEOBriefGenerator(template_dir)
    output_path = tmp_path / "brief_1.md"
    generator.generate_brief(cluster, keywords, run, output_path)
    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert "SEO Brief: Cluster 1 - SEO Tools" in content
    assert "seo tool" in content
    assert "best seo software" in content
    assert "seo audit" in content
    assert "Dominant intent" in content
    print("SEO brief generated successfully:")
    print(content)


def main():
    import tempfile

    tmp = tempfile.TemporaryDirectory()
    test_generate_brief(Path(tmp.name))
    print("Test passed.")


if __name__ == "__main__":
    main()
