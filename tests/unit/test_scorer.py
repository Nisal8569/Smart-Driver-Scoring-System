from unittest.mock import MagicMock
from src.models.scorer import MLDriverScorer


def _make_scorer(initial_score=75.0):
    scorer = MLDriverScorer(initial_score=initial_score)
    scorer.model = MagicMock()
    scorer.scaler = None
    return scorer


def _prime(scorer, n=14):
    """Add n IDLE samples (speed=0) to fill the feature buffer without triggering the model."""
    for _ in range(n):
        scorer.update(speed=0, rpm=0, throttle=0, engine_load=0)


def test_ut01_safe_prediction_increments_score():
    scorer = _make_scorer(initial_score=75.0)
    scorer.model.predict.return_value = [0]
    _prime(scorer)
    score, label = scorer.update(speed=50, rpm=2000, throttle=25, engine_load=50)
    assert score == 75.1
    assert label == "SAFE"


def test_ut02_aggressive_prediction_decrements_score():
    scorer = _make_scorer(initial_score=75.0)
    scorer.model.predict.return_value = [1]
    _prime(scorer)
    score, label = scorer.update(speed=60, rpm=3000, throttle=50, engine_load=80)
    assert score == 73.5
    assert label == "AGGRESSIVE"


def test_ut03_score_capped_at_100():
    scorer = _make_scorer(initial_score=100.0)
    scorer.model.predict.return_value = [0]
    _prime(scorer)
    score, _ = scorer.update(speed=50, rpm=2000, throttle=25, engine_load=50)
    assert score == 100.0


def test_ut04_score_floored_at_0():
    scorer = _make_scorer(initial_score=0.0)
    scorer.model.predict.return_value = [1]
    _prime(scorer)
    score, label = scorer.update(speed=60, rpm=3000, throttle=50, engine_load=80)
    assert score == 0.0
    assert label == "AGGRESSIVE"


def test_ut05_false_positive_suppression_treats_as_safe():
    scorer = _make_scorer(initial_score=75.0)
    scorer.model.predict.return_value = [1]
    _prime(scorer)
    score, label = scorer.update(
        speed=18, rpm=1500, throttle=32, engine_load=50, relative_throttle=17
    )
    assert label == "SAFE"
    assert score == 75.1
