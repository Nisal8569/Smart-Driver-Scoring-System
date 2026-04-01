class EventDetector:
    def __init__(self, accel_threshold=20, brake_threshold=-20,
                 rolling_accel_threshold=20, rolling_window=3):
        self.accel_threshold = accel_threshold
        self.brake_threshold = brake_threshold
        self.rolling_accel_threshold = rolling_accel_threshold
        self.rolling_window = rolling_window
        self.last_speed = None
        self.last_time = None
        self.speed_history = []

    def process_step(self, current_speed, current_time,
                     engine_load=0.0, throttle=0.0):
        event = None

        if self.last_speed is not None and self.last_time is not None:
            delta_v = current_speed - self.last_speed
            delta_t = current_time - self.last_time
            if delta_t > 0:
                acceleration = delta_v / delta_t
                if acceleration > self.accel_threshold:
                    event = "Harsh Acceleration"
                elif acceleration < self.brake_threshold:
                    event = "Harsh Braking"

        # Catch sustained acceleration that stays below per-step threshold
        if event is None and len(self.speed_history) >= self.rolling_window:
            speed_gain = current_speed - self.speed_history[-self.rolling_window]
            if speed_gain > self.rolling_accel_threshold:
                event = "Harsh Acceleration"

        # Catch hard acceleration via engine load + throttle
        if event is None and engine_load >= 95.0 and throttle >= 30.0 and current_speed > 5:
            event = "Harsh Acceleration"

        self.last_speed = current_speed
        self.last_time = current_time
        self.speed_history.append(current_speed)
        if len(self.speed_history) > self.rolling_window + 1:
            self.speed_history.pop(0)

        return event
