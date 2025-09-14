"""Test del nuevo sistema de scoring avanzado"""

import asyncio
import logging

from src.scoring import AdvancedKeywordScorer
from src.scrapers import create_scraper

# Configurar logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


async def test_advanced_scoring():
    """Test completo del nuevo sistema de scoring avanzado"""
    print("🎛️ Testing Advanced Keyword Scoring System")
    print("=" * 60)

    # 1. Generar keywords de prueba
    scraper = create_scraper(country="PE", max_concurrent=3)

    try:
        print("\n1️⃣ Generating test keywords...")
        results = await scraper.expand_keywords(["marketing digital"], max_concurrent=2)

        # Preparar datos para scoring
        test_keywords = []
        for seed, keywords in results.items():
            for i, keyword in enumerate(keywords[:30]):  # Limitar para test
                test_keywords.append(
                    {
                        "keyword": keyword,
                        "trend_score": 50 + (i % 40),  # Simular trend scores 50-90
                        "volume": 100 + (i * 50),  # Simular volúmenes variados
                        "competition": 0.2 + ((i % 8) * 0.1),  # Simular competencia 0.2-0.9
                    }
                )

        print(f"   Generated {len(test_keywords)} test keywords")

        # 2. Test scoring avanzado
        print("\n2️⃣ Testing Advanced Scoring...")
        scorer = AdvancedKeywordScorer(target_geo="PE", target_intent="transactional")

        advanced_results = scorer.calculate_advanced_score(test_keywords)

        # 3. Mostrar top results
        print("\n3️⃣ Top 10 Advanced Scored Keywords:")
        print("-" * 80)
        print(f"{'Rank':<4} {'Score':<6} {'Keyword':<35} {'Intent':<7} {'Geo':<4} {'Words'}")
        print("-" * 80)

        for i, kw in enumerate(advanced_results[:10]):
            keyword = kw["keyword"][:34]  # Truncar si es muy largo
            score = kw.get("advanced_score", 0)
            intent_w = kw.get("intent_weight", 0)
            geo_w = kw.get("geo_weight", 0)
            word_count = len(kw["keyword"].split())

            intent_label = "TRANS" if intent_w >= 0.9 else "COMM" if intent_w >= 0.6 else "INFO"
            geo_label = "✅" if geo_w >= 0.9 else "❌"

            print(
                f"{i+1:<4} {score:<6.1f} {keyword:<35} {intent_label:<7} {geo_label:<4} {word_count}"
            )

        # 4. Análisis por señales
        print("\n4️⃣ Signal Analysis:")
        print("-" * 40)

        # Intent distribution
        transactional = sum(1 for kw in advanced_results[:20] if kw.get("intent_weight", 0) >= 0.9)
        commercial = sum(
            1 for kw in advanced_results[:20] if 0.6 <= kw.get("intent_weight", 0) < 0.9
        )
        informational = sum(1 for kw in advanced_results[:20] if kw.get("intent_weight", 0) < 0.6)

        print("Top 20 Intent Distribution:")
        print(f"  🎯 Transactional: {transactional} ({transactional/20*100:.1f}%)")
        print(f"  💰 Commercial: {commercial} ({commercial/20*100:.1f}%)")
        print(f"  📚 Informational: {informational} ({informational/20*100:.1f}%)")

        # Geo distribution
        geo_targeted = sum(1 for kw in advanced_results[:20] if kw.get("geo_weight", 0) >= 0.9)
        print(f"\n🇵🇪 Geo-targeted (PE): {geo_targeted} ({geo_targeted/20*100:.1f}%)")

        # Word count distribution
        word_counts = [len(kw["keyword"].split()) for kw in advanced_results[:20]]
        avg_words = sum(word_counts) / len(word_counts)
        print(f"📏 Avg word count: {avg_words:.1f}")

        # 5. Guardrails aplicados
        print("\n5️⃣ Guardrails Applied:")
        penalties = {}
        bonuses = {}

        for kw in advanced_results:
            if "guardrail_penalty" in kw:
                penalty = kw["guardrail_penalty"]
                penalties[penalty] = penalties.get(penalty, 0) + 1
            if "guardrail_bonus" in kw:
                bonus = kw["guardrail_bonus"]
                bonuses[bonus] = bonuses.get(bonus, 0) + 1

        print("Penalties applied:")
        for penalty, count in penalties.items():
            print(f"  ❌ {penalty}: {count} keywords")

        print("Bonuses applied:")
        for bonus, count in bonuses.items():
            print(f"  ✅ {bonus}: {count} keywords")

        # 6. Sample detailed signals
        print("\n6️⃣ Detailed Signal Breakdown (Top 3):")
        print("-" * 80)

        for i, kw in enumerate(advanced_results[:3]):
            print(f"\n🏆 Rank {i+1}: {kw['keyword']} (Score: {kw['advanced_score']:.1f})")
            print(f"   📈 Trend: {kw.get('trend_norm', 0):.2f}")
            print(f"   📊 Volume: {kw.get('volume_norm', 0):.2f}")
            print(f"   🏁 Competition: {kw.get('competition_norm', 0):.2f}")
            print(f"   🎯 Intent Weight: {kw.get('intent_weight', 0):.2f}")
            print(f"   🌍 Geo Weight: {kw.get('geo_weight', 0):.2f}")
            print(f"   🔍 SERP Difficulty: {kw.get('serp_difficulty', 0):.2f}")
            print(f"   🎪 Cluster Centrality: {kw.get('cluster_centrality', 0):.2f}")
            print(f"   ✨ Freshness Boost: {kw.get('freshness_boost', 0):.2f}")

        print("\n✅ Advanced Scoring Test Completed Successfully!")

        return advanced_results

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return []

    finally:
        await scraper.close()


async def compare_scoring_systems():
    """Compara el sistema original vs avanzado"""
    print("\n🆚 Comparing Original vs Advanced Scoring")
    print("=" * 50)

    # Sample keywords para comparación
    sample_keywords = [
        {
            "keyword": "marketing digital lima",
            "trend_score": 75,
            "volume": 2000,
            "competition": 0.4,
        },
        {
            "keyword": "curso marketing digital gratis",
            "trend_score": 60,
            "volume": 5000,
            "competition": 0.8,
        },
        {
            "keyword": "agencia marketing digital perú",
            "trend_score": 70,
            "volume": 1500,
            "competition": 0.5,
        },
        {"keyword": "marketing", "trend_score": 90, "volume": 50000, "competition": 0.9},
        {
            "keyword": "que es marketing digital",
            "trend_score": 80,
            "volume": 3000,
            "competition": 0.3,
        },
    ]

    # Scoring avanzado
    advanced_scorer = AdvancedKeywordScorer(target_geo="PE", target_intent="transactional")
    advanced_results = advanced_scorer.calculate_advanced_score(sample_keywords.copy())

    print(f"{'Keyword':<30} {'Advanced':<8} {'Intent':<7} {'Geo':<4}")
    print("-" * 55)

    for kw in advanced_results:
        keyword = kw["keyword"][:29]
        score = kw.get("advanced_score", 0)
        intent_w = kw.get("intent_weight", 0)
        geo_w = kw.get("geo_weight", 0)

        intent_label = "TRANS" if intent_w >= 0.9 else "COMM" if intent_w >= 0.6 else "INFO"
        geo_label = "✅" if geo_w >= 0.9 else "❌"

        print(f"{keyword:<30} {score:<8.1f} {intent_label:<7} {geo_label}")


if __name__ == "__main__":

    async def main():
        await test_advanced_scoring()
        await compare_scoring_systems()

    asyncio.run(main())
