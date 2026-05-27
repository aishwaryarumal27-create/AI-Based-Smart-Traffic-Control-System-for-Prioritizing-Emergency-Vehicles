"""
report.py — CSV report generator
"""

import csv
import os
from datetime import datetime


class ReportGenerator:
    def __init__(self, folder: str = "reports"):
        self.folder = folder
        self.rows: list[dict] = []
        os.makedirs(folder, exist_ok=True)

    def record(self, cam_id: int, vehicle_type: str, confidence: float,
               is_emergency: bool, eta: int, signal_state: str):
        self.rows.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "camera_id": cam_id,
            "vehicle_type": vehicle_type,
            "confidence": round(confidence, 3),
            "is_emergency": is_emergency,
            "ETA": eta,
            "signal_state": signal_state,
        })
        # Auto-flush every 500 rows to avoid memory bloat
        if len(self.rows) >= 5000:
            self.save()

    def save(self):
        if not self.rows:
            return
        fname = os.path.join(
            self.folder,
            f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        fieldnames = ["timestamp", "camera_id", "vehicle_type",
                      "confidence", "is_emergency", "ETA", "signal_state"]
        with open(fname, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.rows)
        print(f"[Report] Saved {len(self.rows)} rows → {fname}")
        self.rows = []
