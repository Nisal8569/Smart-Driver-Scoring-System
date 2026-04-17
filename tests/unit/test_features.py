from src.processing.features import FeatureExtractor


def _add_samples(extractor, n, speed=0.5, rpm=0.5, throttle=0.3, engine_load=0.4):
    for _ in range(n):
        extractor.add(speed, rpm, throttle, engine_load)


def test_ut06_returns_none_with_13_samples():
    extractor = FeatureExtractor(window_size=15)
    _add_samples(extractor, 13)
    assert extractor.get_features() is None


def test_ut07_returns_41_column_dataframe_at_15_samples():
    extractor = FeatureExtractor(window_size=15)
    _add_samples(extractor, 15)
    df = extractor.get_features()
    assert df is not None
    assert df.shape == (1, 41)
