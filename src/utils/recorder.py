import os
import csv
from datetime import datetime


class TripRecorder:
    def __init__(self, output_dir="data/trips"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.filename = os.path.join(self.output_dir, f"trip_{timestamp}.csv")
        self._write_header()
        print(f"[TripRecorder] Recording to: {self.filename}")

    def _write_header(self):
        with open(self.filename, mode='w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp", "speed", "rpm", "throttle", "engine_load",
                "relative_throttle", "prediction", "score", "event"
            ])

    def record(self, speed, rpm, throttle, engine_load, relative_throttle,
               prediction, score, event=""):
        timestamp = datetime.now().isoformat()
        try:
            with open(self.filename, mode='a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    timestamp, speed, rpm, throttle, engine_load,
                    relative_throttle, prediction, score, event
                ])
        except Exception as e:
            print(f"[TripRecorder] Failed to write: {e}")
