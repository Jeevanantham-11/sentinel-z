"""
In-Memory Rolling State Buffer for ICU Patient Telemetry.
Simulates IBM Z Db2 in-memory caching / LinuxONE fast memory store.
Provides O(1) buffer append and feature vector construction.
"""

from collections import deque
from typing import Dict, List, Optional
import time
import threading

class PatientRollingBuffer:
    def __init__(self, patient_id: str, max_points: int = 360):
        self.patient_id = patient_id
        self.history = deque(maxlen=max_points)
        self.last_updated = time.time()
        self._lock = threading.Lock()

    def add_observation(self, telemetry: dict):
        with self._lock:
            def _val(k, default):
                v = telemetry.get(k)
                return float(v) if v is not None else float(default)

            self.history.append({
                "timestamp": time.time(),
                "hr": _val("hr", 80.0),
                "map": _val("map", 85.0),
                "resp": _val("resp", 16.0),
                "temp": _val("temp", 37.0),
                "o2sat": _val("o2sat", 98.0),
                "lactate": _val("lactate", 1.2),
                "wbc": _val("wbc", 7.5),
            })
            self.last_updated = time.time()

    def get_feature_vector(self) -> List[float]:
        """
        Extracts instant physiological values and temporal 6-hour trajectories in O(1) time.
        """
        with self._lock:
            if not self.history:
                return [80.0, 85.0, 16.0, 37.0, 98.0, 1.2, 7.5, 0.0, 0.0]
            
            latest = self.history[-1]
            earliest = self.history[0]
            
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
    def __init__(self, max_patients: int = 1000):
        self._patients: Dict[str, PatientRollingBuffer] = {}
        self._max_patients = max_patients
        self._global_lock = threading.Lock()

    def get_or_create(self, patient_id: str) -> PatientRollingBuffer:
        with self._global_lock:
            if patient_id not in self._patients:
                # Memory protection: prevent unbounded heap growth under high load
                if len(self._patients) >= self._max_patients:
                    stalest_id = min(self._patients.keys(), key=lambda k: self._patients[k].last_updated)
                    del self._patients[stalest_id]
                self._patients[patient_id] = PatientRollingBuffer(patient_id)
            return self._patients[patient_id]


