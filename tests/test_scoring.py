#!/usr/bin/env python3
"""
Test simple del sistema de scoring estandarizado PR-04.
"""

import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.standardized_scoring import StandardizedScorer, create_scoring_config_from_yaml


def main():
    """Test básico del scoring estandarizado."""
    logging.basicConfig(level=logging.INFO)

    print("🧪 Testing PR-04 Standardized Scoring...")

    # Crear configuración de ejemplo
    config = create_scoring_config_from_yaml(
        {
            "scoring": {
                "weights": {"relevance": 0.45, "volume": 0.35, "competition": 0.10, "trend": 0.10},
                "intent_reranking": True,
            }
        }
    )

    # Crear scorer
    scorer = StandardizedScorer(config)

    # Datos de prueba
    test_keywords = [
        {
            "keyword": "python programming",
            "volume": 1000,
            "competition": 0.5,
            "trend": 0.8,
            "intent": "informational",
            "intent_prob_transactional": 0.2,
            "geo": "US",
            "language": "en",
        },
        {
            "keyword": "buy python course",
            "volume": 500,
            "competition": 0.3,
            "trend": 0.6,
            "intent": "transactional",
            "intent_prob_transactional": 0.9,
            "geo": "US",
            "language": "en",
        },
    ]

    print(f"📊 Input: {len(test_keywords)} keywords")

    # Procesar keywords
    results = scorer.score_batch(test_keywords, geo="US", language="en")

    print(f"✅ Output: {len(results[0])} scored keywords")
    print(
        f"📈 Config: relevance={results[1].config.relevance_weight}, volume={results[1].config.volume_weight}"
    )
    print(f"🎯 Market: {results[1].market_norms.geo}-{results[1].market_norms.language}")

    for kw in results[0]:
        print(f"  • {kw['keyword']}: score={kw['score']:.3f}")

    print("🎉 PR-04 scoring test successful!")


if __name__ == "__main__":
    main()
