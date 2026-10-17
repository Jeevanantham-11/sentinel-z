"""
In-Memory Rolling State Buffer for ICU Patient Telemetry.
Simulates IBM Z Db2 in-memory caching / LinuxONE fast memory store.
Provides O(1) buffer append and feature vector construction.
"""

from collections import deque
from typing import Dict, List, Optional
import time

class PatientRollingBuffer:
    def __init__(self, patient_id: str, max_points: int = 360): # 360 observations (e.g. 1 per min for 6 hours)
        self.patient_id = patient_id
        self.history = deque(maxlen=max_points)
        self.last_updated = time.time()

    def add_observation(self, telemetry: dict):
        self.history.append({
            "timestamp": time.time(),
            "hr": telemetry.get("hr", 80.0),
            "map": telemetry.get("map", 85.0),
            "resp": telemetry.get("resp", 16.0),
            "temp": telemetry.get("temp", 37.0),
            "o2sat": telemetry.get("o2sat", 98.0),
            "lactate": telemetry.get("lactate", 1.2),
            "wbc": telemetry.get("wbc", 7.5),
        })
        self.last_updated = time.time()

    def get_feature_vector(self) -> List[float]:
        """
        Extracts instant values + 6-hour trajectory (deltas) in sub-millisecond time.
        """
        if not self.history:
            return [80.0, 85.0, 16.0, 37.0, 98.0, 1.2, 7.5, 0.0, 0.0]
        
        latest = self.history[-1]
        earliest = self.history[0]
        
        # Trend features (deltas over the window)
        hr_delta = latest["hr"] - earliest["hr"]
        map_delta = latest["map"] - earliest["map"]
        
        return [
            latest["hr"],
            latest["map"],
            latest["resp"],
            latest["temp"],
            latest["o2sat"],
            latest["lactate"],
            latest["wbc"],
            hr_delta,
            map_delta
        ]

class InMemoryStateStore:
    def __init__(self):
        self._patients: Dict[str, PatientRollingBuffer] = {}

    def get_or_create(self, patient_id: str) -> PatientRollingBuffer:
        if patient_id not in self._patients:
            self._patients[patient_id] = PatientRollingBuffer(patient_id)
        return self._patients[patient_id]
