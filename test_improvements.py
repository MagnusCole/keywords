"""Test script para validar las mejoras implementadas"""

import asyncio
import logging

from src.scrapers import create_scraper

# Configurar logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


async def test_geo_targeting():
    """Test geo-targeting para diferentes países"""
    print("🌍 Testing Geo-targeting...")

    countries = ["PE", "ES", "MX", "GLOBAL"]
    seed = "marketing digital"

    for country in countries:
        print(f"\n📍 Testing {country}:")
        scraper = create_scraper(country=country)

        # Test autocomplete with geo-targeting
        suggestions = await scraper.get_autocomplete_suggestions(seed)
        print(f"  Autocomplete ({country}): {len(suggestions)} suggestions")
        if suggestions:
            print(f"  Sample: {suggestions[:3]}")

        await scraper.close()


async def test_parallel_expansion():
    """Test paralelismo mejorado"""
    print("\n⚡ Testing Parallel Expansion...")

    scraper = create_scraper(country="PE", max_concurrent=3)
    seeds = ["marketing digital"]

    import time

    start_time = time.time()

    results = await scraper.expand_keywords(seeds, max_concurrent=3)

    end_time = time.time()
    duration = end_time - start_time

    for seed, keywords in results.items():
        print(f"  {seed}: {len(keywords)} keywords in {duration:.2f}s")
        print(f"  Sample: {keywords[:5] if keywords else 'None'}")

    await scraper.close()


async def test_improved_related_searches():
    """Test improved related searches con real parsing"""
    print("\n🔍 Testing Improved Related Searches...")

    scraper = create_scraper(country="PE")
    seed = "seo"

    # Test con real related searches habilitado
    related_real = await scraper.get_related_searches(seed, use_real_related=True)
    print(f"  Real related searches: {len(related_real)}")
    print(f"  Sample: {related_real[:3]}")

    # Test con fallback method
    related_fallback = await scraper.get_related_searches(seed, use_real_related=False)
    print(f"  Fallback method: {len(related_fallback)}")
    print(f"  Sample: {related_fallback[:3]}")

    await scraper.close()


async def test_advanced_normalization():
    """Test normalización avanzada y fuzzy dedup"""
    print("\n🧹 Testing Advanced Normalization...")

    scraper = create_scraper(country="PE")

    # Test keywords con duplicados y problemas de normalización
    test_keywords = [
        "marketing digital",
        "marketing  digital",  # Espacios extra
        "Marketing Digital",  # Capitalización
        "marketing-digital",  # Guiones
        "marketing digitál",  # Acentos
        "marketing digital 2024",  # Años
        "curso marketing digital",
        "curso de marketing digital",  # Similar semánticamente
        "cursos marketing digital",  # Plural
    ]

    # Test filtrado avanzado
    filtered = scraper._filter_keywords(test_keywords)
    print(f"  Original: {len(test_keywords)} -> Filtered: {len(filtered)}")
    print(f"  Deduplicated: {filtered}")

    await scraper.close()


async def main():
    """Ejecutar todas las pruebas"""
    print("🚀 Testing All Improvements Implemented")
    print("=" * 50)

    try:
        await test_geo_targeting()
        await test_parallel_expansion()
        await test_improved_related_searches()
        await test_advanced_normalization()

        print("\n✅ All tests completed successfully!")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
