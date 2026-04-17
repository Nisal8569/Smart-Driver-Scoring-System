import csv
import re
from src.utils.recorder import TripRecorder

EXPECTED_HEADER = [
    "timestamp", "speed", "rpm", "throttle", "engine_load",
    "relative_throttle", "prediction", "score", "event"
]


def test_it04_filename_format(tmp_path):
    recorder = TripRecorder(output_dir=str(tmp_path))
    filename = recorder.filename
    assert re.search(r"trip_\d{8}_\d{6}\.csv$", filename), (
        f"Filename '{filename}' does not match trip_YYYYMMDD_HHMMSS.csv"
    )


def test_it04_header_has_9_fields(tmp_path):
    recorder = TripRecorder(output_dir=str(tmp_path))
    with open(recorder.filename, newline="") as f:
        header = next(csv.reader(f))
    assert len(header) == 9
    assert header == EXPECTED_HEADER


def test_it04_rows_written_correctly(tmp_path):
    recorder = TripRecorder(output_dir=str(tmp_path))
    recorder.record(speed=45, rpm=1800, throttle=22, engine_load=55,
                    relative_throttle=10, prediction="SAFE", score=78.5, event="")
    recorder.record(speed=62, rpm=2500, throttle=38, engine_load=70,
                    relative_throttle=15, prediction="AGGRESSIVE", score=77.0,
                    event="Harsh Acceleration")

    with open(recorder.filename, newline="") as f:
        rows = list(csv.reader(f))

    assert len(rows) == 3  # header + 2 data rows

    row1 = rows[1]
    assert row1[1] == "45"
    assert row1[6] == "SAFE"
    assert row1[7] == "78.5"
    assert row1[8] == ""

    row2 = rows[2]
    assert row2[1] == "62"
    assert row2[6] == "AGGRESSIVE"
    assert row2[8] == "Harsh Acceleration"
