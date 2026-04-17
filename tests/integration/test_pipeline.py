import csv
from unittest.mock import MagicMock
from src.models.scorer import MLDriverScorer
from src.utils.recorder import TripRecorder


def test_it01_full_pipeline_20_samples_writes_csv_with_9_fields(tmp_path):
    scorer = MLDriverScorer(initial_score=75.0)
    scorer.model = MagicMock()
    scorer.model.predict.return_value = [0]
    scorer.scaler = None

    recorder = TripRecorder(output_dir=str(tmp_path))

    for i in range(20):
        speed = 30 + i
        score, label = scorer.update(
            speed=speed, rpm=1800, throttle=25, engine_load=50
        )
        recorder.record(
            speed=speed, rpm=1800, throttle=25, engine_load=50,
            relative_throttle=10, prediction=label, score=score
        )

    csv_files = list(tmp_path.glob("trip_*.csv"))
    assert len(csv_files) == 1

    with open(csv_files[0], newline="") as f:
        rows = list(csv.reader(f))

    header = rows[0]
    assert len(header) == 9
    assert header == [
        "timestamp", "speed", "rpm", "throttle", "engine_load",
        "relative_throttle", "prediction", "score", "event"
    ]

    data_rows = rows[1:]
    assert len(data_rows) == 20
