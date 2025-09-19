def generate_reliability_report(top_keywords, rejected_keywords):
    """Generate enhanced business reliability report for keyword analysis results"""
    # === Business Intelligence Report ===
    print("\n📋 Business Intelligence & Reliability Report")
    print("=" * 60)

    if not top_keywords:
        print("❌ No keywords to analyze")
        return

    # Data source breakdown
    source_breakdown = {}
    intent_breakdown = {}
    service_breakdown = {}
    quality_breakdown = {}

    total_score = 0
    high_quality_count = 0

    for kw in top_keywords:
        # Data source tracking
        ds = kw.get("data_source", "heurístico")
        source_breakdown[ds] = source_breakdown.get(ds, 0) + 1

        # Intent tracking
        intent = kw.get("intent_category", "informational")
        intent_breakdown[intent] = intent_breakdown.get(intent, 0) + 1

        # Service category tracking
        service = kw.get("service_category", "general")
        service_breakdown[service] = service_breakdown.get(service, 0) + 1

        # Quality tracking
        quality = kw.get("data_quality", "unknown")
        quality_breakdown[quality] = quality_breakdown.get(quality, 0) + 1

        # Score analysis
        score = kw.get("score", 0)
        total_score += score
        if score >= 60:
            high_quality_count += 1

    print("\n🔍 DATA QUALITY ANALYSIS:")
    print("-" * 30)
    for source, count in source_breakdown.items():
        percentage = (count / len(top_keywords)) * 100
        status = "🟢" if source in ["trends", "ads"] else "🟡" if source == "heurístico" else "🔴"
        print(f"  {status} {source}: {count} keywords ({percentage:.1f}%)")

    print("\n🎯 BUSINESS INTENT ANALYSIS:")
    print("-" * 30)
    for intent, count in intent_breakdown.items():
        percentage = (count / len(top_keywords)) * 100
        priority = "🔥" if intent == "transactional" else "⚡" if intent == "commercial" else "📚"
        print(f"  {priority} {intent}: {count} keywords ({percentage:.1f}%)")

    print("\n📊 BUSINESS METRICS:")
    print("-" * 30)
    avg_score = total_score / len(top_keywords) if top_keywords else 0
    real_data_pct = (
        (source_breakdown.get("trends", 0) + source_breakdown.get("ads", 0))
        / len(top_keywords)
        * 100
    )
    transactional_pct = intent_breakdown.get("transactional", 0) / len(top_keywords) * 100
    high_quality_pct = (high_quality_count / len(top_keywords)) * 100

    print(f"  📈 Average Score: {avg_score:.1f}/100")
    print(f"  🎯 High-Value Keywords (>60): {high_quality_count} ({high_quality_pct:.1f}%)")
    print(f"  🔒 Real Data Coverage: {real_data_pct:.1f}%")
    print(f"  💰 Transactional Intent: {transactional_pct:.1f}%")
    print(f"  ❌ Keywords Filtered Out: {len(rejected_keywords)}")

    # Business recommendations
    print("\n💡 BUSINESS RECOMMENDATIONS:")
    print("-" * 30)
    if transactional_pct < 30:
        print("  ⚠️  LOW transactional intent - consider more service-focused seeds")
    if real_data_pct < 50:
        print("  ⚠️  LOW real data coverage - configure Google Ads for accurate volumes")
    if avg_score < 50:
        print("  ⚠️  LOW average scores - refine targeting strategy")
    if high_quality_pct > 50:
        print("  ✅ GOOD high-value keyword ratio")
    if len(rejected_keywords) > len(top_keywords):
        print("  ✅ EXCELLENT filtering - removing low-value terms")

    # Top rejected analysis
    if rejected_keywords:
        print("\n🚫 TOP REJECTED KEYWORDS (Quality Control):")
        print("-" * 30)
        rejection_reasons = {}
        for kw in rejected_keywords[:10]:
            reason = kw.get("relevance_reason", "unknown")
            rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1
            print(f"  ❌ {kw['keyword'][:40]:<40} → {reason}")

        print("\n📋 REJECTION PATTERN ANALYSIS:")
        for reason, count in rejection_reasons.items():
            print(f"  {reason}: {count} keywords")

    print("\n" + "=" * 60)
    print(f"  Keywords rejected: {len(rejected_keywords)} (low relevance)")

    if rejected_keywords:
        print("\nTop rejected keywords:")
        for i, kw in enumerate(rejected_keywords[:5], 1):
            reason = kw.get("relevance_reason", "unknown")
            print(f"  {i}. {kw['keyword']} (reason: {reason})")
