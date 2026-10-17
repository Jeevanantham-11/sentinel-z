"""
Sentinel-Z: Clinical Telemetry Streamer & PhysioNet Benchmark Replayer.
Replays authentic, de-identified ICU patient trajectories from the PhysioNet 2019
Challenge benchmark or streams continuous high-throughput synthetic telemetry.
"""

import os
import sys
import time
import json
import random
import argparse
from pathlib import Path
import requests

BASE_DIR = Path(__file__).resolve().parent.parent
BENCHMARK_DIR = BASE_DIR / "data" / "benchmark_patients"
DEFAULT_URL = os.getenv("GATEWAY_URL", "http://localhost:8000/api/v1/telemetry")

def load_benchmark_patient(patient_id: str = "p000011") -> dict:
    """Loads a real PhysioNet benchmark patient file."""
    if not patient_id.endswith(".json"):
        patient_file = BENCHMARK_DIR / f"{patient_id}.json"
    else:
        patient_file = BENCHMARK_DIR / patient_id

    if not patient_file.exists():
        files = list(BENCHMARK_DIR.glob("p*.json"))
        if not files:
            raise FileNotFoundError(
                f"No benchmark patient files found in {BENCHMARK_DIR}. "
                "Run 'python data_pipeline/fetch_physionet.py' first."
            )
        patient_file = files[0]

    with open(patient_file, "r", encoding="utf-8") as f:
        return json.load(f)

def replay_real_patient(patient_id: str = "p000011", delay_sec: float = 0.4, url: str = DEFAULT_URL):
    """
    Replays an authentic ICU patient hour-by-hour through the Sentinel-Z gateway.
    Demonstrates real-time in-transaction clinical interception prior to EHR commit.
    """
    patient = load_benchmark_patient(patient_id)
    obs = patient["observations"]
    total_hours = len(obs)
    
    print("=" * 72)
    print(f"  REPLAYING AUTHENTIC PHYSIO-NET 2019 ICU PATIENT: {patient['patient_id']}")
    print(f"  Description : {patient['case_description']}")
    print(f"  Demographics: {patient['demographics']['gender']}, Age {patient['demographics']['age']:.0f}")
    print(f"  Total Stay  : {total_hours} Hours | Ground-Truth Sepsis: {patient['is_septic_case']}")
    print("=" * 72)
    print(" Hour | HR   | MAP  | Resp | Temp  | Lactate | Hot Path | Action")
    print("-" * 72)

    session = requests.Session()
    intercept_count = 0

    for item in obs:
        payload = {
            "patient_id": patient["patient_id"],
            "hr": item["hr"],
            "map": item["map"],
            "resp": item["resp"],
            "temp": item["temp"],
            "o2sat": item["o2sat"],
            "lactate": item["lactate"],
            "wbc": item["wbc"]
        }

        try:
            res = session.post(url, json=payload, timeout=2.0)
            if res.status_code == 200:
                data = res.json()
                score = data.get("risk_score", 0.0)
                action = data.get("action", "UNKNOWN")
                hot_ms = data.get("inference_latency_ms", 0.0)
                is_crit = (action == "INTERCEPT & ESCALATE") or (score >= 70.0)
                
                flag = " [CRITICAL INTERCEPT]" if is_crit else ""
                print(
                    f" {item['hour']:4d} | {item['hr']:4.1f} | {item['map']:4.1f} | "
                    f"{item['resp']:4.1f} | {item['temp']:5.2f} | {item['lactate']:7.2f} | "
                    f"{hot_ms:5.3f}ms | {action}{flag}"
                )

                if is_crit and data.get("rationale"):
                    intercept_count += 1
                    brief = data["rationale"].get("clinical_rationale", "")
                    engine = data["rationale"].get("engine", "IBM Granite")
                    print(f"      [->] {engine} Warm-Path Brief:")
                    print(f"           \"{brief}\"")
            else:
                print(f"[!] Server returned HTTP {res.status_code}")
        except Exception as exc:
            print(f"[X] Telemetry transmission error: {exc}")
            break

        if delay_sec > 0:
            time.sleep(delay_sec)

    print("=" * 72)
    print(f">> PATIENT REPLAY COMPLETE: {total_hours} Hours Processed, {intercept_count} Interceptions Triggered <<")
    print("=" * 72)

def generate_random_patient_payload():
    """Generates synthetic random patient for stress testing."""
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

def run_synthetic_stream(rate_per_sec: float = 4.0, max_events: int = 100, url: str = DEFAULT_URL):
    """Dispatches continuous high-throughput synthetic telemetry."""
    print(f"[*] Dispatching HL7/FHIR telemetry stream to {url} at {rate_per_sec} TPS...")
    delay = 1.0 / rate_per_sec if rate_per_sec > 0 else 0
    session = requests.Session()
    sent = 0
    
    while sent < max_events:
        payload = generate_random_patient_payload()
        try:
            res = session.post(url, json=payload, timeout=2.0)
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
    parser = argparse.ArgumentParser(description="Sentinel-Z High-Throughput Clinical Streamer & Replayer")
    parser.add_argument("--mode", choices=["replay", "stream"], default="replay", help="Replay real PhysioNet patient or stream synthetic data")
    parser.add_argument("--patient", type=str, default="p000011", help="PhysioNet patient ID for replay (e.g. p000011, p000028, p000001)")
    parser.add_argument("--rate", type=float, default=4.0, help="Transactions per second for stream mode")
    parser.add_argument("--count", type=int, default=100, help="Total transactions for stream mode")
    parser.add_argument("--delay", type=float, default=0.25, help="Delay between hours in replay mode (seconds)")
    parser.add_argument("--url", type=str, default=DEFAULT_URL, help="Gateway telemetry endpoint URL")
    args = parser.parse_args()
    
    if args.mode == "replay":
        replay_real_patient(patient_id=args.patient, delay_sec=args.delay, url=args.url)
    else:
        run_synthetic_stream(rate_per_sec=args.rate, max_events=args.count, url=args.url)
