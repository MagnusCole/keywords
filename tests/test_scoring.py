import math
import sys
from pathlib import Path

# Ensure src is on the path for tests
sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from scoring import KeywordScorer


def test_calculate_score_basic():
    scorer = KeywordScorer(trend_weight=0.4, volume_weight=0.4, competition_weight=0.2)
    score = scorer.calculate_score(trend_score=50, volume=1000, competition=0.5, keyword_text="curso marketing digital")
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
