"""
tracker.py — Simple centroid-based vehicle tracker
"""

from collections import OrderedDict
import numpy as np
from scipy.spatial.distance import cdist


class CentroidTracker:
    def __init__(self, max_disappeared: int = 30, max_distance: int = 80):
        self.next_id = 0
        self.objects: OrderedDict[int, np.ndarray] = OrderedDict()
        self.disappeared: OrderedDict[int, int] = OrderedDict()
        self.max_disappeared = max_disappeared
        self.max_distance = max_distance

    def register(self, centroid: np.ndarray):
        self.objects[self.next_id] = centroid
        self.disappeared[self.next_id] = 0
        self.next_id += 1

    def deregister(self, obj_id: int):
        del self.objects[obj_id]
        del self.disappeared[obj_id]

    def update(self, detections: list) -> OrderedDict:
        if not detections:
            for obj_id in list(self.disappeared.keys()):
                self.disappeared[obj_id] += 1
                if self.disappeared[obj_id] > self.max_disappeared:
                    self.deregister(obj_id)
            return self.objects

        input_centroids = np.array([
            [(x1 + x2) // 2, (y1 + y2) // 2]
            for x1, y1, x2, y2, *_ in detections
        ])

        if not self.objects:
            for c in input_centroids:
                self.register(c)
        else:
            obj_ids = list(self.objects.keys())
            obj_centroids = np.array(list(self.objects.values()))
            D = cdist(obj_centroids, input_centroids)

            rows = D.min(axis=1).argsort()
            cols = D.argmin(axis=1)[rows]

            used_rows, used_cols = set(), set()
            for r, c in zip(rows, cols):
                if r in used_rows or c in used_cols:
                    continue
                if D[r, c] > self.max_distance:
                    continue
                obj_id = obj_ids[r]
                self.objects[obj_id] = input_centroids[c]
                self.disappeared[obj_id] = 0
                used_rows.add(r)
                used_cols.add(c)

            unused_rows = set(range(D.shape[0])) - used_rows
            unused_cols = set(range(D.shape[1])) - used_cols

            for r in unused_rows:
                obj_id = obj_ids[r]
                self.disappeared[obj_id] += 1
                if self.disappeared[obj_id] > self.max_disappeared:
                    self.deregister(obj_id)

            for c in unused_cols:
                self.register(input_centroids[c])

        return self.objects