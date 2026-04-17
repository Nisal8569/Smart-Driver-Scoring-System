import asyncio
import threading
import queue
import tkinter as tk
from src.acquisition.ble_device import BLEOBDAdapter
from src.models.scorer import MLDriverScorer
from src.processing.events import EventDetector
from src.ui.dashboard import DashboardApp
from src.utils.recorder import TripRecorder

OBDBLE_ADDRESS = "81:23:45:67:89:BA"


async def data_acquisition_loop(data_queue, stop_event):
    obd = BLEOBDAdapter(OBDBLE_ADDRESS)
    scorer = MLDriverScorer(model_path="src/models/fyp_model.pkl")
    event_detector = EventDetector()
    recorder = TripRecorder()

    try:
        print(f"Connecting to OBDBLE at {OBDBLE_ADDRESS}...")
        await obd.connect()
        print("Connected to OBD adapter")

        data_queue.put({'connected': True, 'speed': 0, 'rpm': 0, 'score': 100, 'label': 'IDLE'})

        iteration = 0

        while not stop_event.is_set():
            try:
                data = await obd.get_data()

                if data["speed"] is None or data["rpm"] is None:
                    await asyncio.sleep(0.5)
                    continue

                iteration += 1

                event = event_detector.process_step(
                    current_speed=data.get("speed", 0),
                    current_time=iteration * 0.5,
                    engine_load=data.get("engine_load", 0),
                    throttle=data.get("throttle", 0)
                )

                trip_score, prediction_label = scorer.update(
                    speed=data.get("speed", 0),
                    rpm=data.get("rpm", 0),
                    throttle=data.get("throttle", 0),
                    engine_load=data.get("engine_load", 0),
                    relative_throttle=data.get("relative_throttle", 0),
                    event=event
                )

                data_queue.put({
                    'speed':        data.get("speed", 0),
                    'rpm':          data.get("rpm", 0),
                    'throttle':     data.get("throttle", 0),
                    'engine_load':  data.get("engine_load", 0),
                    'score':        trip_score,
                    'label':        prediction_label,
                    'event':        event or "",
                    'connected':    True
                })

                recorder.record(
                    speed=data.get("speed", 0),
                    rpm=data.get("rpm", 0),
                    throttle=data.get("throttle", 0),
                    engine_load=data.get("engine_load", 0),
                    relative_throttle=data.get("relative_throttle", 0),
                    prediction=prediction_label,
                    score=trip_score,
                    event=event or ""
                )

                await asyncio.sleep(0.1)

            except Exception as e:
                print(f"Error in data loop: {e}")
                data_queue.put({'connected': False})
                await asyncio.sleep(1)

    except Exception as e:
        print(f"Connection error: {e}")
        data_queue.put({'connected': False})
    finally:
        await obd.disconnect()
        print("Disconnected from OBD adapter")


def run_async_loop(data_queue, stop_event):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(data_acquisition_loop(data_queue, stop_event))
    finally:
        loop.close()


def main():
    print("Starting Smart Driver Scoring System - LCD Mode")

    q = queue.Queue()
    stop_event = threading.Event()

    data_thread = threading.Thread(target=run_async_loop, args=(q, stop_event))
    data_thread.daemon = True
    data_thread.start()

    try:
        root = tk.Tk()
        app = DashboardApp(root, q)

        def on_closing():
            stop_event.set()
            root.destroy()

        root.protocol("WM_DELETE_WINDOW", on_closing)
        root.mainloop()

    except Exception as e:
        print(f"UI Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        stop_event.set()


if __name__ == "__main__":
    main()
