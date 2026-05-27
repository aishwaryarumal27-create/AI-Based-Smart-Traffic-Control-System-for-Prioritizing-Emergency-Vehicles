"""
congestion_predictor.py — AI-based congestion prediction
"""

import numpy as np
from collections import deque
import threading
import time
from typing import List, Dict, Any


class CongestionPredictor:
    def __init__(self, sequence_length: int = 10):
        self.sequence_length = sequence_length

        # FIXED: store history camera-wise
        self.history = {}

        self.predictions = {}
        self.running = True

        self.prediction_thread = threading.Thread(
            target=self._background_predict,
            daemon=True
        )
        self.prediction_thread.start()

    def add_data_point(
        self,
        cam_id: int,
        density: float,
        vehicle_count: int,
        timestamp: float = None
    ):
        """Add a data point for prediction"""

        if timestamp is None:
            timestamp = time.time()

        # FIXED
        if cam_id not in self.history:
            self.history[cam_id] = deque(
                maxlen=self.sequence_length * 2
            )

        self.history[cam_id].append({
            "timestamp": timestamp,
            "density": density,
            "count": vehicle_count
        })

    def _background_predict(self):
        """Background thread for predictions"""

        while self.running:

            # FIXED
            for cam_id in list(self.history.keys()):
                self._predict_for_camera(cam_id)

            time.sleep(30)

    def _predict_for_camera(self, cam_id: int):
        """Predict future congestion for a camera"""

        if (
            cam_id not in self.history or
            len(self.history[cam_id]) < self.sequence_length
        ):
            return

        recent = list(self.history[cam_id])

        densities = [
            d["density"]
            for d in recent[-self.sequence_length:]
        ]

        if len(densities) < 2:
            return

        # Trend detection
        trend = np.polyfit(
            range(len(densities)),
            densities,
            1
        )[0]

        predictions = []
        current = densities[-1]

        # Predict next 5 minutes
        for i in range(1, 6):
            predicted = current + (trend * i)

            # Clamp 0–100
            predicted = max(0, min(100, predicted))

            predictions.append(round(predicted, 1))

        # Congestion level
        future_congestion = "LOW"

        if predictions[-1] > 70:
            future_congestion = "HIGH"

        elif predictions[-1] > 40:
            future_congestion = "MEDIUM"

        self.predictions[cam_id] = {
            "current_density": round(densities[-1], 1),

            "trend": (
                "increasing"
                if trend > 0
                else "decreasing"
            ),

            "predictions": predictions,

            "future_congestion": future_congestion,

            "will_congest": predictions[-1] > 70,

            "time_to_congest": (
                self._estimate_time_to_congest(
                    trend,
                    densities[-1]
                )
                if trend > 0
                else None
            )
        }

    def _estimate_time_to_congest(
        self,
        trend: float,
        current: float
    ) -> int:
        """Estimate minutes until congestion"""

        if trend <= 0:
            return None

        needed = 70 - current

        if needed <= 0:
            return 0

        minutes = int(needed / trend)

        return max(1, minutes)

    def get_predictions(self) -> Dict[int, Any]:
        """Get predictions"""

        return self.predictions

    def get_recommendations(self) -> List[str]:
        """Generate recommendations"""

        recommendations = []

        for cam_id, pred in self.predictions.items():

            camera_names = {
                0: "North",
                1: "East",
                2: "South",
                3: "West"
            }

            cam_name = camera_names.get(
                cam_id,
                f"Camera {cam_id}"
            )

            if pred.get("will_congest", False):

                time_to = pred.get(
                    "time_to_congest",
                    0
                )

                if time_to == 0:

                    recommendations.append(
                        f"⚠️ {cam_name} is currently congested!"
                    )

                else:

                    recommendations.append(
                        f"📈 {cam_name} may congest in ~{time_to} mins."
                    )

            elif (
                pred.get("trend") == "increasing"
                and pred["current_density"] > 50
            ):

                recommendations.append(
                    f"⚠️ {cam_name} traffic increasing rapidly."
                )

        return recommendations[:3]

    def stop(self):
        self.running = False


# Global predictor instance
predictor = CongestionPredictor()