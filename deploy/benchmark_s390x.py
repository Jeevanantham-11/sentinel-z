"""
Sentinel-Z: High-Velocity Dual AI Framework Benchmark on LinuxONE (s390x).
Evaluates PyTorch Temporal Embedding + XGBoost Risk Classification.
Measures p50, p90, p95, p99 in-transaction inference latencies across N iterations.
"""

import time
import sys
import platform
import argparse
import numpy as np
from pathlib import Path

# Add root directory to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from ml_pipeline.dual_engine import DualAIEngine

def run_benchmark(iterations: int = 2000):
    arch = platform.machine()
    system = platform.system()
    
    print("=" * 68)
    print("  PROJECT SENTINEL-Z -- IN-TRANSACTION DUAL-AI BENCHMARK")
    print("  Target Hardware: IBM Telum AI Accelerator / LinuxONE (s390x)")
    print("=" * 68)
    print(f"[*] Host OS          : {system} ({platform.release()})")
    print(f"[*] Architecture     : {arch}")
    print(f"[*] Benchmark Target : {iterations:,} continuous in-transaction evaluations")
    print(f"[*] AI Frameworks    : PyTorch (Temporal Latent) + XGBoost (Tabular Risk)")
    print("-" * 68)
    
    engine = DualAIEngine()
    
    # Cache and instruction pipeline warm-up (100 iterations)
    warmup_vector = [82.0, 80.0, 16.0, 37.1, 98.0, 1.2, 7.5, 0.0, 0.0]
    for _ in range(100):
        engine.evaluate(warmup_vector)
        
    latencies_total = []
    latencies_torch = []
    latencies_xgb = []
    
    print("[*] Commencing high-throughput evaluation loop...")
    t_bench_start = time.perf_counter()
    
    for i in range(iterations):
        # Generate realistic random variations
        feats = [
            float(np.random.normal(85.0, 15.0)),   # HR
            float(np.random.normal(75.0, 12.0)),   # MAP
            float(np.random.normal(18.0, 4.0)),    # Resp
            float(np.random.normal(37.2, 0.6)),    # Temp
            float(np.random.normal(96.0, 3.0)),    # O2Sat
            float(np.random.exponential(1.5)),     # Lactate
            float(np.random.normal(9.0, 3.0)),     # WBC
            float(np.random.normal(0.0, 5.0)),     # HR delta
            float(np.random.normal(0.0, 4.0)),     # MAP delta
        ]
        
        t0 = time.perf_counter_ns()
        score, diag = engine.evaluate(feats)
        t_end = time.perf_counter_ns()
        
        elapsed_ms = (t_end - t0) / 1_000_000.0
        latencies_total.append(elapsed_ms)
        latencies_torch.append(diag.get("pytorch_latency_ms", 0.0))
        latencies_xgb.append(diag.get("xgboost_latency_ms", 0.0))
        
    t_bench_total = time.perf_counter() - t_bench_start
    tps = round(iterations / t_bench_total, 1)
    
    arr_total = np.array(latencies_total)
    arr_torch = np.array(latencies_torch)
    arr_xgb = np.array(latencies_xgb)
    
    p50 = np.percentile(arr_total, 50)
    p90 = np.percentile(arr_total, 90)
    p95 = np.percentile(arr_total, 95)
    p99 = np.percentile(arr_total, 99)
    max_lat = np.max(arr_total)
    mean_lat = np.mean(arr_total)
    
    print("\n" + "=" * 68)
    print("  IN-TRANSACTION PERFORMANCE METRICS (SLA TARGET: < 4.000 ms)")
    print("=" * 68)
    print(f"  [-] Throughput Rate    : {tps:,.1f} In-Transaction Inferences / Second")
    print(f"  [-] Total Time Elapsed : {t_bench_total:.3f} seconds for {iterations:,} records")
    print("-" * 68)
    print("  LATENCY DISTRIBUTION (HOT PATH):")
    print(f"    - Median (p50)       : {p50:6.3f} ms   [Telum Target: < 1.0 ms]")
    print(f"    - 90th %ile (p90)    : {p90:6.3f} ms")
    print(f"    - 95th %ile (p95)    : {p95:6.3f} ms")
    print(f"    - 99th %ile (p99)    : {p99:6.3f} ms   [Enterprise SLA: < 4.0 ms]")
    print(f"    - Maximum Latency    : {max_lat:6.3f} ms")
    print(f"    - Arithmetic Mean    : {mean_lat:6.3f} ms")
    print("-" * 68)
    print("  FRAMEWORK BREAKDOWN (Average per transaction):")
    print(f"    - PyTorch Latent Net : {np.mean(arr_torch):6.3f} ms (LayerNorm + Tanh projection)")
    print(f"    - XGBoost Classifier : {np.mean(arr_xgb):6.3f} ms (Calibrated Sepsis-3 Decision)")
    print("=" * 68)
    
    if p99 < 4.0:
        print(">> VERDICT: [PASSED] SYSTEM FULLY QUALIFIES FOR IN-TRANSACTION INFERENCE <<")
    else:
        print(">> VERDICT: [WARNING] Latency exceeds 4ms target. Optimize batching or CPU governor. <<")
    print("=" * 68)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sentinel-Z LinuxONE Benchmark Engine")
    parser.add_argument("--iter", "--iterations", dest="iter", type=int, default=2000, help="Number of benchmark iterations")
    args = parser.parse_args()
    run_benchmark(iterations=args.iter)
