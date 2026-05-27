"""
eta.py — ETA estimator based on centroid velocity
"""

import time
import math


SIGNAL_LINE_Y = 300        # Approximate pixel Y position of stop-line
PIXELS_PER_METER = 8.0     # Calibration constant


class ETACalculator:
    def __init__(self):
        self.prev_positions: dict[str, tuple] = {}
        self.speeds: dict[str, float] = {}

    def calculate(self, cx: int, cy: int, label: str) -> int:
        """Return ETA in seconds (int). Returns 0 if already past signal."""
        key = label
        now = time.time()

        if key in self.prev_positions:
            px, py, pt = self.prev_positions[key]
            dt = now - pt
            if dt > 0:
                dist_px = math.sqrt((cx - px) ** 2 + (cy - py) ** 2)
                speed_px_s = dist_px / dt  # pixels per second
                speed_m_s = speed_px_s / PIXELS_PER_METER
                self.speeds[key] = max(speed_m_s, 0.5)

        self.prev_positions[key] = (cx, cy, now)

        speed = self.speeds.get(key, 5.0)  # default 5 m/s ≈ 18 km/h
        dist_to_signal_px = max(SIGNAL_LINE_Y - cy, 0)
        dist_to_signal_m = dist_to_signal_px / PIXELS_PER_METER

        if speed > 0:
            eta = int(dist_to_signal_m / speed)
        else:
            eta = 99

        return min(eta, 99)
