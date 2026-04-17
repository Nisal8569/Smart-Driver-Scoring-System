import pandas as pd
from collections import deque


class FeatureExtractor:
    def __init__(self, window_size=15):
        self.window_size = max(window_size, 15)
        self.history = deque(maxlen=self.window_size)

    def add(self, speed, rpm, throttle, engine_load=0,
            relative_throttle=0, steering_angle=0, steering_speed=0):
        self.history.append({
            'speed': float(speed) if speed is not None else 0.0,
            'rpm': float(rpm) if rpm is not None else 0.0,
            'throttle': float(throttle) if throttle is not None else 0.0,
            'engine_load': float(engine_load) if engine_load is not None else 0.0,
            'relative_throttle': float(relative_throttle) if relative_throttle is not None else 0.0,
            'steering_angle': float(steering_angle) if steering_angle is not None else 0.0,
            'steering_speed': float(steering_speed) if steering_speed is not None else 0.0,
        })

    def get_features(self):
        if len(self.history) < 15:
            return None

        df = pd.DataFrame(list(self.history))
        last = df.iloc[-1]
        prev = df.iloc[-2]

        features = {
            'speed': last['speed'],
            'rpm': last['rpm'],
            'throttle': last['throttle'],
            'engine_load': last['engine_load'],
            'relative_throttle': last['relative_throttle'],
            'steering_angle': last['steering_angle'],
            'steering_speed': last['steering_speed'],
        }

        features['speed_delta'] = last['speed'] - prev['speed']
        features['rpm_delta'] = last['rpm'] - prev['rpm']
        features['throttle_delta'] = last['throttle'] - prev['throttle']
        features['engine_load_delta'] = last['engine_load'] - prev['engine_load']
        features['steering_angle_delta'] = last['steering_angle'] - prev['steering_angle']

        for w in [5, 10, 15]:
            for c in ['speed', 'rpm', 'throttle', 'engine_load']:
                window_data = df[c].iloc[-w:]
                features[f'{c}_mean_{w}'] = window_data.mean()
                features[f'{c}_std_{w}']  = window_data.std(ddof=1) if w > 1 else 0.0

        features['rpm_speed_ratio'] = last['rpm'] / max(last['speed'], 0.01)
        features['throttle_load_ratio'] = last['throttle'] / max(last['engine_load'], 0.01)
        features['steering_activity'] = abs(last['steering_angle']) + abs(last['steering_speed'])
        features['throttle_rpm_ratio'] = last['throttle'] / max(last['rpm'], 0.01)
        features['load_speed_ratio'] = last['engine_load'] / max(last['speed'], 0.01)

        column_order = [
            "speed", "rpm", "throttle", "engine_load",
            "relative_throttle", "steering_angle", "steering_speed",
            "speed_delta", "rpm_delta", "throttle_delta", "engine_load_delta", "steering_angle_delta",
            "speed_mean_5",  "speed_std_5",  "rpm_mean_5",  "rpm_std_5",  "throttle_mean_5",  "throttle_std_5",  "engine_load_mean_5",  "engine_load_std_5",
            "speed_mean_10", "speed_std_10", "rpm_mean_10", "rpm_std_10", "throttle_mean_10", "throttle_std_10", "engine_load_mean_10", "engine_load_std_10",
            "speed_mean_15", "speed_std_15", "rpm_mean_15", "rpm_std_15", "throttle_mean_15", "throttle_std_15", "engine_load_mean_15", "engine_load_std_15",
            "rpm_speed_ratio", "throttle_load_ratio", "steering_activity",
            "throttle_rpm_ratio", "load_speed_ratio",
        ]

        return pd.DataFrame([[features[c] for c in column_order]], columns=column_order).fillna(0)
