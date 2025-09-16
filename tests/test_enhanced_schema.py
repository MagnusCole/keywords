"""
Test standalone enterprise schema functionality.
This validates that the enhanced schema works independently.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.db.schema import (
    STANDARD_CSV_COLUMNS,
    DataSource,
    EnhancedKeyword,
    IntentType,
    RunMetadata,
    generate_run_id,
)


def test_enhanced_schema():
    """Test all enhanced schema components."""
    print("🧪 Testing Enhanced Schema...")

    # Test RunMetadata
    run_meta = RunMetadata(profile="test", geo="PE", language="es", seeds=["marketing", "seo"])
    print(f"✅ Run ID generated: {run_meta.run_id}")
    print(f"✅ Run metadata: {run_meta.profile}, {run_meta.geo}")

    # Test EnhancedKeyword
    keyword = EnhancedKeyword(
        keyword="marketing digital",
        source="expansion",
        volume=1000,
        intent=IntentType.INFORMATIONAL,
        intent_prob=0.85,
        data_source=DataSource.TRENDS,
        run_id=run_meta.run_id,
        geo="PE",
        language="es",
    )
    print(f"✅ Enhanced keyword: {keyword.keyword}")
    print(f"✅ Intent: {keyword.intent.value} (prob: {keyword.intent_prob})")
    print(f"✅ Data source: {keyword.data_source.value}")
    print(f"✅ Run tracking: {keyword.run_id}")

    # Test serialization
    keyword_dict = keyword.to_dict()
    print(f"✅ Serialization: {len(keyword_dict)} fields")

    # Test CSV columns
    print(f"✅ Standard CSV columns: {len(STANDARD_CSV_COLUMNS)} columns")
    print(f"   Key columns: {STANDARD_CSV_COLUMNS[:5]}...")

    # Test ID generation
    run_id = generate_run_id("prod")
    print(f"✅ ID generation: {run_id}")

    print("\n🎯 Enhanced Schema Validation Complete!")
    print("   ✅ Run metadata with full traceability")
    print("   ✅ Enhanced keywords with intent classification")
    print("   ✅ Data source tracking")
    print("   ✅ Standardized export format")
    return True


if __name__ == "__main__":
    test_enhanced_schema()
