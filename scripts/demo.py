#!/usr/bin/env python3
"""
Demo script para probar el Keyword Finder con datos de prueba
"""

import asyncio
import sys
from pathlib import Path

# Agregar src al path (dos niveles arriba desde tools/)
sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from keyword_finder.core.database import Keyword, KeywordDatabase
from keyword_finder.core.exporters import KeywordExporter
from keyword_finder.core.scoring import BasicKeywordScorer


async def demo_keyword_finder() -> None:
    """Demo del sistema con keywords de ejemplo"""

    print("🚀 Keyword Finder Demo - Insertando keywords de prueba...")

    # Inicializar componentes
    db = KeywordDatabase()
    scorer = BasicKeywordScorer()
    exporter = KeywordExporter()

    # Keywords de ejemplo para marketing digital
    demo_keywords = [
        {
            "keyword": "marketing digital",
            "source": "demo",
            "volume": 12000,
            "trend_score": 85,
            "competition": 0.7,
        },
        {
            "keyword": "marketing digital para pymes",
            "source": "demo",
            "volume": 3200,
            "trend_score": 78,
            "competition": 0.4,
        },
        {
            "keyword": "estrategias marketing digital",
            "source": "demo",
            "volume": 5400,
            "trend_score": 72,
            "competition": 0.5,
        },
        {
            "keyword": "curso marketing digital",
            "source": "demo",
            "volume": 8900,
            "trend_score": 90,
            "competition": 0.8,
        },
        {
            "keyword": "marketing digital gratis",
            "source": "demo",
            "volume": 2100,
            "trend_score": 65,
            "competition": 0.3,
        },
        {
            "keyword": "agencia marketing digital",
            "source": "demo",
            "volume": 4300,
            "trend_score": 70,
            "competition": 0.6,
        },
        {
            "keyword": "marketing digital madrid",
            "source": "demo",
            "volume": 1800,
            "trend_score": 68,
            "competition": 0.4,
        },
        {
            "keyword": "que es marketing digital",
            "source": "demo",
            "volume": 6700,
            "trend_score": 75,
            "competition": 0.5,
        },
        {
            "keyword": "marketing digital ejemplos",
            "source": "demo",
            "volume": 2900,
            "trend_score": 62,
            "competition": 0.4,
        },
        {
            "keyword": "herramientas marketing digital",
            "source": "demo",
            "volume": 3800,
            "trend_score": 80,
            "competition": 0.6,
        },
    ]

    # Calcular scores y crear objetos Keyword
    scored_keywords = scorer.calculate_score(demo_keywords)
    keyword_objects = []

    for kw_data in scored_keywords:
        keyword_obj = Keyword(
            keyword=kw_data["keyword"],
            source=kw_data["source"],
            volume=kw_data["volume"],
            trend_score=kw_data["trend_score"],
            competition=kw_data["competition"],
            score=kw_data["score"],
        )
        keyword_objects.append(keyword_obj)

    # Insertar en base de datos
    inserted = db.insert_keywords_batch(keyword_objects)
    print(f"✅ Insertadas {inserted} keywords en la base de datos")

    # Mostrar top keywords
    top_keywords = db.get_keywords(limit=10)
    print(f"\n🎯 Top {len(top_keywords)} Keywords:")
    print("-" * 80)

    for i, kw in enumerate(top_keywords, 1):
        print(
            f"{i:2d}. {kw['keyword']:<35} Score: {kw['score']:5.1f} | "
            f"Trend: {kw['trend_score']:3.0f} | Volume: {kw['volume']:5d} | "
            f"Comp: {kw['competition']:4.2f}"
        )

    # Generar reportes
    print("\n📄 Generando reportes...")
    csv_file = exporter.export_to_csv(top_keywords, "demo_keywords.csv")
    pdf_file = exporter.export_to_pdf(
        top_keywords, "demo_report.pdf", "Demo Keyword Research Report"
    )

    print(f"✅ CSV: {csv_file}")
    print(f"✅ PDF: {pdf_file}")


if __name__ == "__main__":
    asyncio.run(demo_keyword_finder())
