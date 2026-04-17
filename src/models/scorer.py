import joblib
import os
import pandas as pd
from src.processing.features import FeatureExtractor


class MLDriverScorer:
    def __init__(self, model_path="src/models/fyp_model.pkl", initial_score=75.0):
        self.score = float(initial_score)
        self.feature_extractor = FeatureExtractor(window_size=15)
        self.model = None
        self.scaler = None

        model_dir = os.path.dirname(os.path.abspath(__file__))

        resolved_model_path = model_path
        if not os.path.exists(resolved_model_path):
            resolved_model_path = os.path.join(model_dir, os.path.basename(model_path))

        if os.path.exists(resolved_model_path):
            try:
                self.model = joblib.load(resolved_model_path)
            except Exception as e:
                print(f"[MLDriverScorer] ERROR loading model: {e}")

        scaler_path = os.path.join(model_dir, "fyp_scaler.pkl")
        if os.path.exists(scaler_path):
            try:
                self.scaler = joblib.load(scaler_path)
            except Exception as e:
                print(f"[MLDriverScorer] ERROR loading scaler: {e}")
        else:
            print(f"[MLDriverScorer] WARNING: Scaler not found at {scaler_path}")

    def update(self, speed, rpm, throttle, engine_load=0.0,
               relative_throttle=0.0, steering_angle=0.0, steering_speed=0.0,
               event=None):
        raw_signals = [speed, rpm, throttle, engine_load,
                       relative_throttle, steering_angle, steering_speed]

        scaled_signals = raw_signals
        if self.scaler:
            try:
                df_temp = pd.DataFrame([raw_signals], columns=self.scaler.feature_names_in_)
                scaled_signals = self.scaler.transform(df_temp)[0]
            except Exception:
                pass

        self.feature_extractor.add(*scaled_signals)

        if speed == 0:
            return self.score, "IDLE"

        # OBD dropout — moving but no engine signal, skip
        if speed > 5 and rpm == 0 and engine_load == 0:
            return self.score, "SAFE"

        prediction_label = "WAITING"
        features_df = self.feature_extractor.get_features()

        if features_df is not None and self.model:
            try:
                pred = self.model.predict(features_df.values)[0]

                if pred == 1 or event in ("Harsh Acceleration", "Harsh Braking"):
                    # suppress false positives for acceleration at low speed only
                    # never suppress confirmed braking events
                    if event != "Harsh Braking" and speed < 30 and relative_throttle < 20 and throttle < 40:
                        prediction_label = "SAFE"
                        self.score = round(min(100, self.score + 0.1), 1)
                    else:
                        prediction_label = "AGGRESSIVE"
                        self.score = round(max(0, self.score - 1.5), 1)
                else:
                    prediction_label = "SAFE"
                    self.score = round(min(100, self.score + 0.1), 1)

            except Exception:
                pass

        return self.score, prediction_label
