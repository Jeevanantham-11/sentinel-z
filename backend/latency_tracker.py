"""
High-Precision Nanosecond Latency Tracker for IBM Z In-Transaction Inference.
Calculates p50, p95, p99 latencies in real time.
"""

import time
import numpy as np
from collections import deque

class LatencyTracker:
    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        self.latencies_ms = deque(maxlen=window_size)
        self.total_transactions = 0

    def record(self, elapsed_ms: float):
        self.latencies_ms.append(elapsed_ms)
        self.total_transactions += 1

    def get_metrics(self) -> dict:
        if not self.latencies_ms:
            return {
                "p50_ms": 0.0,
                "p95_ms": 0.0,
                "p99_ms": 0.0,
                "mean_ms": 0.0,
                "tps": 0,
                "total": self.total_transactions
            }
        arr = np.array(self.latencies_ms)
        return {
            "p50_ms": round(float(np.percentile(arr, 50)), 3),
            "p95_ms": round(float(np.percentile(arr, 95)), 3),
            "p99_ms": round(float(np.percentile(arr, 99)), 3),
            "mean_ms": round(float(np.mean(arr)), 3),
            "total": self.total_transactions
        }
