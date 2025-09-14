import math
import sys
from pathlib import Path

# Ensure src is on the path for tests
sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from scoring import KeywordScorer


def test_calculate_score_basic():
    scorer = KeywordScorer(trend_weight=0.4, volume_weight=0.4, competition_weight=0.2)
    score = scorer.calculate_score(
        trend_score=50, volume=1000, competition=0.5, keyword_text="curso marketing digital"
    )
    assert 0 <= score <= 100


def test_volume_normalization_bounds():
    scorer = KeywordScorer()
    assert math.isclose(scorer._normalize_volume(0), 0.0)
    assert 0.0 <= scorer._normalize_volume(10) <= 1.0
    assert scorer._normalize_volume(1_000_000) == 1.0


def test_bonus_long_tail_and_terms():
    scorer = KeywordScorer()
    kw = "mejor curso marketing digital madrid"
    base = scorer.calculate_score(50, 1000, 0.5, keyword_text="marketing")
    boosted = scorer.calculate_score(50, 1000, 0.5, keyword_text=kw)
    assert boosted >= base


def test_single_word_penalty():
    scorer = KeywordScorer()
    single = scorer.calculate_score(50, 1000, 0.5, keyword_text="marketing")
    multi = scorer.calculate_score(50, 1000, 0.5, keyword_text="como hacer marketing para pymes")
    assert multi > single


def test_question_bonus():
    scorer = KeywordScorer()
    base = scorer.calculate_score(50, 1000, 0.5, keyword_text="marketing de contenidos")
    question = scorer.calculate_score(
        50, 1000, 0.5, keyword_text="como hacer marketing de contenidos"
    )
    assert question > base


def test_volume_estimation():
    scorer = KeywordScorer()

    # Single words should have high estimated volume
    single_vol = scorer.estimate_volume("marketing")
    assert single_vol > 5000

    # Long-tail should have lower volume
    longtail_vol = scorer.estimate_volume(
        "como hacer un curso de marketing digital completo gratis"
    )
    assert longtail_vol < single_vol

    # Question keywords should have different volume pattern
    question_vol = scorer.estimate_volume("que es marketing digital")
    base_vol = scorer.estimate_volume("marketing digital")
    # Questions are more specific, typically have lower volume
    assert 1000 <= question_vol <= base_vol


def test_competition_estimation():
    scorer = KeywordScorer()

    # Single words should have high competition
    single_comp = scorer.estimate_competition("marketing")
    assert single_comp > 0.7

    # Long-tail should have lower competition
    longtail_comp = scorer.estimate_competition("como hacer marketing para pymes locales")
    assert longtail_comp < single_comp

    # Commercial terms should increase competition
    commercial_comp = scorer.estimate_competition("mejor curso marketing precio")
    base_comp = scorer.estimate_competition("marketing digital")
    assert commercial_comp >= base_comp


def test_keyword_categorization():
    scorer = KeywordScorer()

    assert scorer.categorize_keyword("seo para empresas") == "seo"
    assert scorer.categorize_keyword("marketing en redes sociales") == "redes_sociales"
    assert scorer.categorize_keyword("curso de marketing digital") == "educacion"
    assert scorer.categorize_keyword("herramientas de marketing") == "herramientas"
    assert scorer.categorize_keyword("agencia de marketing") == "servicios"
    assert scorer.categorize_keyword("precio software marketing") == "comercial"  # changed test
    assert scorer.categorize_keyword("marketing online") == "digital"


def test_deduplication():
    scorer = KeywordScorer()

    keywords_data = [
        {"keyword": "como hacer marketing digital", "score": 25.0},
        {"keyword": "como hacer marketing digital gratis", "score": 20.0},  # Similar
        {"keyword": "herramientas de marketing", "score": 30.0},
        {"keyword": "herramientas marketing", "score": 22.0},  # Similar
        {"keyword": "curso seo", "score": 15.0},
    ]

    deduplicated = scorer.deduplicate_keywords(keywords_data, similarity_threshold=0.8)

    # Should remove similar duplicates and keep higher scored ones
    assert len(deduplicated) == 3  # Should remove 2 similar ones

    # Check that higher scored ones are kept
    keywords_text = [kw["keyword"] for kw in deduplicated]
    assert "como hacer marketing digital" in keywords_text  # Higher score kept
    assert "herramientas de marketing" in keywords_text  # Higher score kept
    assert "curso seo" in keywords_text
