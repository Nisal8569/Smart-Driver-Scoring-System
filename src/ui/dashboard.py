import tkinter as tk
from tkinter import font
import threading
import time
import queue
import sys
import os
import logging
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

log_dir = os.path.join(os.path.dirname(__file__), '../../logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f'dashboard_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)
logger.info(f"Logging to: {log_file}")

from src.acquisition.sim import MockOBDAdapter
from src.models.scorer import MLDriverScorer

SCREEN_WIDTH = 480
SCREEN_HEIGHT = 320
BG_COLOR = "#121212"
TEXT_COLOR = "#FFFFFF"
ACCENT_COLOR = "#00FFAB"  # Green
WARNING_COLOR = "#FF4C4C" # Red
IDLE_COLOR = "#888888"    # Grey

class DashboardApp:
    def __init__(self, root, data_queue):
        self.root = root
        self.data_queue = data_queue
        
        self.root.title("Driver Scoring System")
        self.root.geometry(f"{SCREEN_WIDTH}x{SCREEN_HEIGHT}")
        self.root.configure(bg=BG_COLOR)

        self.font_large = font.Font(family="Arial", size=50, weight="bold")
        self.font_medium = font.Font(family="Arial", size=20)
        self.font_small = font.Font(family="Arial", size=12)
        
        self.create_widgets()
        self.update_ui()
        
    def create_widgets(self):
        self.status_frame = tk.Frame(self.root, bg=BG_COLOR)
        self.status_frame.pack(side="top", fill="x", padx=10, pady=5)
        
        self.lbl_status = tk.Label(self.status_frame, text="DISCONNECTED", font=self.font_small, bg=BG_COLOR, fg=IDLE_COLOR)
        self.lbl_status.pack(side="left")
        
        self.lbl_score_title = tk.Label(self.status_frame, text="SCORE", font=self.font_small, bg=BG_COLOR, fg=TEXT_COLOR)
        self.lbl_score_title.pack(side="right")

        self.main_frame = tk.Frame(self.root, bg=BG_COLOR)
        self.main_frame.pack(expand=True, fill="both", padx=20)

        self.speed_frame = tk.Frame(self.main_frame, bg=BG_COLOR)
        self.speed_frame.pack(side="left", expand=True)
        
        self.lbl_speed_val = tk.Label(self.speed_frame, text="0", font=self.font_large, bg=BG_COLOR, fg=ACCENT_COLOR)
        self.lbl_speed_val.pack()
        self.lbl_speed_unit = tk.Label(self.speed_frame, text="km/h", font=self.font_medium, bg=BG_COLOR, fg=TEXT_COLOR)
        self.lbl_speed_unit.pack()

        self.score_frame = tk.Frame(self.main_frame, bg=BG_COLOR)
        self.score_frame.pack(side="right", expand=True)
        
        self.lbl_score_val = tk.Label(self.score_frame, text="100", font=self.font_large, bg=BG_COLOR, fg=ACCENT_COLOR)
        self.lbl_score_val.pack()
        self.lbl_score_unit = tk.Label(self.score_frame, text="Safety Score", font=self.font_medium, bg=BG_COLOR, fg=TEXT_COLOR)
        self.lbl_score_unit.pack()

        self.bottom_frame = tk.Frame(self.root, bg=BG_COLOR)
        self.bottom_frame.pack(side="bottom", fill="x", padx=10, pady=10)
        
        self.lbl_rpm = tk.Label(self.bottom_frame, text="RPM: 0", font=self.font_small, bg=BG_COLOR, fg=TEXT_COLOR)
        self.lbl_rpm.pack(side="left")
        
        self.lbl_throttle = tk.Label(self.bottom_frame, text="Throttle: 0%", font=self.font_small, bg=BG_COLOR, fg=TEXT_COLOR)
        self.lbl_throttle.pack(side="left", padx=10)
        
        self.lbl_load = tk.Label(self.bottom_frame, text="Load: 0%", font=self.font_small, bg=BG_COLOR, fg=TEXT_COLOR)
        self.lbl_load.pack(side="left")
        
        self.lbl_alert = tk.Label(self.bottom_frame, text="SAFE", font=self.font_medium, bg=ACCENT_COLOR, fg="#000000")
        self.lbl_alert.pack(side="right")

    def update_ui(self):
        try:
            while not self.data_queue.empty():
                data = self.data_queue.get_nowait()
                self.process_data(data)
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.update_ui)

    def process_data(self, data):
        if not hasattr(self, '_current_state'):
            self._current_state = {}

        speed = data.get('speed', 0)
        rpm = data.get('rpm', 0)
        throttle = data.get('throttle', 0)
        engine_load = data.get('engine_load', 0)
        score = data.get('score', 100)
        label = data.get('label', 'IDLE')
        connected = data.get('connected', False)

        if connected != self._current_state.get('connected'):
            if connected:
                self.lbl_status.config(text="CONNECTED", fg=ACCENT_COLOR)
            else:
                self.lbl_status.config(text="DISCONNECTED", fg=IDLE_COLOR)
            self._current_state['connected'] = connected

        if int(speed) != self._current_state.get('speed'):
            self.lbl_speed_val.config(text=f"{int(speed)}")
            self._current_state['speed'] = int(speed)
            
        if int(rpm) != self._current_state.get('rpm'):
            self.lbl_rpm.config(text=f"RPM: {int(rpm)}")
            self._current_state['rpm'] = int(rpm)
            
        if int(throttle) != self._current_state.get('throttle'):
            self.lbl_throttle.config(text=f"Throttle: {int(throttle)}%")
            self._current_state['throttle'] = int(throttle)
            
        if int(engine_load) != self._current_state.get('engine_load'):
            self.lbl_load.config(text=f"Load: {int(engine_load)}%")
            self._current_state['engine_load'] = int(engine_load)
            
        if score != self._current_state.get('score'):
            self.lbl_score_val.config(text=f"{score:.1f}%")
            self._current_state['score'] = score

        if label != self._current_state.get('label'):
            if label == "AGGRESSIVE":
                color = WARNING_COLOR
                alert_text = "AGGRESSIVE"
                self.lbl_alert.config(bg=WARNING_COLOR, fg="#FFFFFF")
            elif label == "SAFE":
                color = ACCENT_COLOR
                alert_text = "SAFE"
                self.lbl_alert.config(bg=ACCENT_COLOR, fg="#000000")
            else:
                color = IDLE_COLOR
                alert_text = label
                self.lbl_alert.config(bg=IDLE_COLOR, fg="#FFFFFF")
                
            self.lbl_alert.config(text=alert_text)
            self.lbl_speed_val.config(fg=color)
            self.lbl_score_val.config(fg=color)
            self._current_state['label'] = label


USE_MOCK = False  # Set to True to use simulated data
MOCK_FILE = os.path.join(os.path.dirname(__file__), '../../data/mock_drive_data.csv')
OBD_MAC_ADDRESS = "81:23:45:67:89:BA"  # MAC address of your OBD scanner

def data_worker(data_queue):
    """Background thread to fetch data"""
    import asyncio
    from src.utils.recorder import TripRecorder

    scorer = MLDriverScorer(model_path="src/models/fyp_model.pkl") 
    recorder = TripRecorder()

    adapter = None
    if USE_MOCK:
        logger.info("Using MOCK data mode")
        if os.path.exists(MOCK_FILE):
            adapter = MockOBDAdapter(MOCK_FILE, delay=0.5)
            try:
                adapter.connect()
                logger.info("Mock adapter connected")
            except Exception as e:
                logger.error(f"Mock Connection Failed: {e}")
                adapter = None
        else:
            logger.error(f"Mock Data File Not Found: {MOCK_FILE}")
    else:
        # Use Real BLE OBD
        logger.info(f"Using REAL BLE OBD mode - connecting to {OBD_MAC_ADDRESS}")
        from src.acquisition.ble_device import BLEOBDAdapter
        adapter = BLEOBDAdapter(OBD_MAC_ADDRESS)

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(adapter.connect())
            logger.info("BLE OBD adapter connected successfully")
        except Exception as e:
            logger.error(f"BLE Connection Failed: {e}", exc_info=True)
            adapter = None
    
    while True:
        try:
            if adapter:
                if USE_MOCK:
                    raw_data = adapter.get_data()
                else:
                    loop = asyncio.get_event_loop()
                    raw_data = loop.run_until_complete(adapter.get_data())

                speed = raw_data.get('speed', 0)
                rpm = raw_data.get('rpm', 0)
                throttle = raw_data.get('throttle', 0)
                engine_load = raw_data.get('engine_load', 0)
                relative_throttle = raw_data.get('relative_throttle', 0)
                
                score, label = scorer.update(
                    speed=speed, 
                    rpm=rpm, 
                    throttle=throttle, 
                    engine_load=engine_load,
                    relative_throttle=relative_throttle
                )

                ui_packet = {
                    'speed': speed,
                    'rpm': rpm,
                    'throttle': throttle,
                    'engine_load': engine_load,
                    'score': score,
                    'label': label,
                    'connected': True
                }
                data_queue.put(ui_packet)

                recorder.record(
                    speed=speed,
                    rpm=rpm,
                    throttle=throttle,
                    engine_load=engine_load,
                    relative_throttle=relative_throttle,
                    prediction=label,
                    score=score
                )
                
            else:
                 data_queue.put({'connected': False})
                 
            time.sleep(0.5) # Update rate
            
        except Exception as e:
            logger.error(f"Data Loop Error: {e}", exc_info=True)
            time.sleep(1)

if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("SMART DRIVER SCORING SYSTEM - DASHBOARD")
    logger.info("=" * 50)
    logger.info(f"Mode: {'MOCK DATA' if USE_MOCK else 'REAL BLE OBD'}")
    if not USE_MOCK:
        logger.info(f"OBD MAC: {OBD_MAC_ADDRESS}")
    logger.info("=" * 50)

    q = queue.Queue()

    logger.info("Starting Data Thread...")
    t = threading.Thread(target=data_worker, args=(q,))
    t.daemon = True
    t.start()

    logger.info("Initializing UI...")
    try:
        root = tk.Tk()
        logger.info("UI Root Created")
        app = DashboardApp(root, q)
        logger.info("App Initialized. Starting Mainloop...")
        root.mainloop()
    except Exception as e:
        logger.error(f"UI Error: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
