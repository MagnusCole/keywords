from pathlib import Path

from src.db.database import Keyword, KeywordDatabase
from src.io.exporters import KeywordExporter


def test_db_insert_and_csv_export(tmp_path):
    db_path = tmp_path / "test_keywords.db"
    db = KeywordDatabase(str(db_path))

    # Insert a keyword
    kw = Keyword(
        keyword="prueba de piscina",
        source="test",
        volume=100,
        trend_score=50.0,
        competition=0.3,
        score=75.0,
        category="",
        geo="PE",
        language="es",
        intent="transactional",
    )
    assert db.insert_keyword(kw)

    # Fetch it back
    rows = db.get_keywords(limit=5, min_score=0)
    assert any(r.get("keyword") == "prueba de piscina" for r in rows)

    # Export to CSV
    exporter = KeywordExporter(export_dir=str(tmp_path / "exports"))
    csv_path = exporter.export_to_csv(rows, filename="smoke.csv")
    assert csv_path and Path(csv_path).exists()
