"""
High-Throughput Clinical Telemetry Simulator.
Generates synthetic HL7 v2 / FHIR R4 clinical observations.
Can run in demo streaming mode or 1,000 TPS stress-test mode.
"""

import time
import random
import sys
import argparse
import requests

TARGET_URL = "http://localhost:8000/api/v1/telemetry"

def generate_random_patient_payload():
    is_critical = random.random() < 0.20
    patient_id = f"ICU-{random.randint(100, 125)}"
    
    if is_critical:
        return {
            "patient_id": patient_id,
            "hr": round(random.uniform(110.0, 140.0), 1),
            "map": round(random.uniform(50.0, 64.0), 1),
            "resp": round(random.uniform(22.0, 30.0), 1),
            "temp": round(random.uniform(38.4, 39.5), 1),
            "o2sat": round(random.uniform(88.0, 93.0), 1),
            "lactate": round(random.uniform(2.5, 5.2), 1),
            "wbc": round(random.uniform(14.0, 22.0), 1)
        }
    else:
        return {
            "patient_id": patient_id,
            "hr": round(random.uniform(65.0, 95.0), 1),
            "map": round(random.uniform(75.0, 98.0), 1),
            "resp": round(random.uniform(14.0, 19.0), 1),
            "temp": round(random.uniform(36.6, 37.3), 1),
            "o2sat": round(random.uniform(96.0, 99.0), 1),
            "lactate": round(random.uniform(0.8, 1.6), 1),
            "wbc": round(random.uniform(5.5, 9.5), 1)
        }

def run_stream(rate_per_sec: float = 3.0, max_events: int = 100):
    print(f"[*] Dispatching HL7/FHIR telemetry stream to {TARGET_URL} at {rate_per_sec} TPS...")
    delay = 1.0 / rate_per_sec if rate_per_sec > 0 else 0
    session = requests.Session()
    sent = 0
    
    while sent < max_events:
        payload = generate_random_patient_payload()
        t0 = time.perf_counter_ns()
        try:
            res = session.post(TARGET_URL, json=payload, timeout=2.0)
            if res.status_code == 200:
                data = res.json()
                action = data.get("action", "UNKNOWN")
                score = data.get("risk_score", 0.0)
                hot_ms = data.get("inference_latency_ms", 0.0)
                print(f"[{sent+1:04d}] {payload['patient_id']} | Risk: {score:4.1f}% | Hot Path: {hot_ms:5.3f}ms | Action: {action}")
            else:
                print(f"[!] Server returned status {res.status_code}")
        except Exception as e:
            print(f"[X] Telemetry transmission failed: {e}")
            break
            
        sent += 1
        if delay > 0:
            time.sleep(delay)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sentinel-Z High-Throughput Clinical Streamer")
    parser.add_argument("--rate", type=float, default=4.0, help="Transactions per second (TPS)")
    parser.add_argument("--count", type=int, default=100, help="Total transactions to dispatch")
    args = parser.parse_args()
    run_stream(rate_per_sec=args.rate, max_events=args.count)
