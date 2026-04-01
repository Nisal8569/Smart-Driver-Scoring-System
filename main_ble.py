import asyncio
import csv
import os
from datetime import datetime
from src.acquisition.ble_device import BLEOBDAdapter
from src.models.scorer import MLDriverScorer
from src.processing.events import EventDetector

OBDBLE_ADDRESS = "81:23:45:67:89:BA"


async def main_loop():
    obd = BLEOBDAdapter(OBDBLE_ADDRESS)
    scorer = MLDriverScorer(model_path="src/models/fyp_model.pkl")
    event_detector = EventDetector()

    try:
        await obd.connect()

        print("SMART DRIVER SCORING SYSTEM - LIVE MODE (BLE)")
        print("Press Ctrl+C to stop\n")

        trip_score = 100.0
        iteration = 0
        trip_rows = []

        while True:
            data = await obd.get_data()

            if data["speed"] is None or data["rpm"] is None:
                print("Waiting for valid data...")
                await asyncio.sleep(1)
                continue

            iteration += 1

            event = event_detector.process_step(
                current_speed=data["speed"] or 0,
                current_time=iteration * 0.5,
                engine_load=data.get("engine_load", 0),
                throttle=data.get("throttle", 0)
            )
            events = [event] if event else []

            trip_score, prediction_label = scorer.update(
                speed=data.get("speed", 0),
                rpm=data.get("rpm", 0),
                throttle=data.get("throttle", 0),
                engine_load=data.get("engine_load", 0),
                relative_throttle=data.get("relative_throttle", 0),
                event=event
            )

            status_info = f"[{prediction_label}]"

            print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                  f"Spd: {data['speed'] or 0:5.1f} | "
                  f"RPM: {data['rpm'] or 0:5.0f} | "
                  f"Thr: {data.get('throttle', 0):4.1f}% | "
                  f"Load: {data.get('engine_load', 0):4.1f}% | "
                  f"Score: {trip_score:5.1f} {status_info}")

            if events:
                for e in events:
                    print(f"  EVENT: {e}")

            trip_rows.append({
                "timestamp":        datetime.now().isoformat(),
                "speed":            data.get("speed", 0),
                "rpm":              data.get("rpm", 0),
                "throttle":         data.get("throttle", 0),
                "engine_load":      data.get("engine_load", 0),
                "relative_throttle":data.get("relative_throttle", 0),
                "prediction":       prediction_label,
                "score":            round(trip_score, 1),
                "event":            events[0] if events else ""
            })

            await asyncio.sleep(0.5)

    except KeyboardInterrupt:
        print("\nTRIP SUMMARY")
        print(f"Final Score: {trip_score:.1f}/100")
        print(f"Total Readings: {iteration}")

        if trip_rows:
            os.makedirs("data/trips", exist_ok=True)
            filename = f"data/trips/trip_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            fieldnames = ["timestamp", "speed", "rpm", "throttle", "engine_load",
                          "relative_throttle", "prediction", "score", "event"]
            with open(filename, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(trip_rows)
            print(f"Trip saved to: {filename}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await obd.disconnect()


if __name__ == "__main__":
    asyncio.run(main_loop())
