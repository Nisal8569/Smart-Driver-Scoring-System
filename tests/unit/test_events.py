from src.processing.events import EventDetector


def test_ut08_hard_acceleration_single_step():
    detector = EventDetector()
    detector.process_step(0, 0)
    event = detector.process_step(25, 1)
    assert event == "Harsh Acceleration"


def test_ut09_hard_braking_rolling_window():
    # Three steady steps at 60 km/h fill the rolling window, then a drop of 22 km/h
    # over 2 seconds (accel = -11, no single-step trigger) fires the rolling check.
    detector = EventDetector()
    detector.process_step(60, 0)
    detector.process_step(60, 1)
    detector.process_step(60, 2)
    event = detector.process_step(38, 4)  # delta_t=2 → accel=-11, rolling: 38-60=-22
    assert event == "Harsh Braking"


def test_ut10_high_engine_load_triggers_event():
    detector = EventDetector()
    event = detector.process_step(current_speed=10, current_time=0,
                                  engine_load=96.0, throttle=35.0)
    assert event == "Harsh Acceleration"


def test_ut11_rolling_window_acceleration_30_to_62():
    # Seed three steps at 30, then 46, then 62.
    # Each step rises by 16 km/h (below the 20 single-step threshold).
    # On the step to 62, rolling check: 62 - history[-3]=30 = 32 > 20 → fires.
    detector = EventDetector()
    detector.process_step(30, 0)
    detector.process_step(30, 1)
    detector.process_step(30, 2)
    detector.process_step(46, 3)
    event = detector.process_step(62, 4)
    assert event == "Harsh Acceleration"
