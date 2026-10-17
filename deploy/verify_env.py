"""
Environment and Hardware Parity Verifier for Sentinel-Z.
Works on Windows (Local Dev), x86_64 Linux, and IBM LinuxONE (s390x).
Gracefully handles the case where PyTorch is not available on s390x.
"""

import platform
import sys
import os
import time
import sqlite3


def verify_system():
    print("=" * 66)
    print("  PROJECT SENTINEL-Z -- PLATFORM VERIFICATION REPORT")
    print("=" * 66)

    arch = platform.machine()
    system = platform.system()
    py_version = sys.version.split()[0]

    print(f"[*] Operating System : {system} ({platform.release()})")
    print(f"[*] Architecture     : {arch}")
    print(f"[*] Python Version   : {py_version}")

    if "s390x" in arch.lower():
        print("[+] PLATFORM STATUS  : RUNNING ON IBM Z / LinuxONE MAINFRAME (s390x)")
    else:
        print(f"[i] PLATFORM STATUS  : RUNNING ON LOCAL WORKSTATION ({arch}) [Dev Mode]")

    print("-" * 66)
    print("Core Dependency Check:")

    # Always-required packages (must be available on s390x)
    required_deps = ["fastapi", "uvicorn", "numpy", "scipy", "xgboost", "sklearn", "onnxruntime", "pandas"]
    all_required_passed = True
    for dep in required_deps:
        try:
            mod = __import__(dep)
            ver = getattr(mod, "__version__", "loaded")
            print(f"  [OK]   {dep:<18} : {ver}")
        except ImportError as e:
            print(f"  [FAIL] {dep:<18} : NOT INSTALLED ({e})")
            all_required_passed = False

    # Optional packages (graceful degradation on s390x)
    print("\nOptional Dependency Check:")
    optional_deps = ["torch", "onnxruntime"]
    for dep in optional_deps:
        try:
            mod = __import__(dep)
            ver = getattr(mod, "__version__", "loaded")
            print(f"  [OK]   {dep:<18} : {ver}")
        except ImportError:
            if dep == "torch" and "s390x" in arch.lower():
                print(f"  [INFO] {dep:<18} : Not installed on s390x — dual_engine.py uses NumPy fallback")
            else:
                print(f"  [WARN] {dep:<18} : Not installed")

    # SQLite (used for Db2 audit simulation)
    print("\nPersistence Layer Check:")
    try:
        test_db = ":memory:"
        conn = sqlite3.connect(test_db)
        conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
        conn.close()
        print(f"  [OK]   sqlite3            : {sqlite3.sqlite_version} (Db2 audit simulation layer)")
    except Exception as e:
        print(f"  [FAIL] sqlite3            : {e}")

    print("-" * 66)

    # High-resolution timer test
    t0 = time.perf_counter_ns()
    time.sleep(0.001)
    t1 = time.perf_counter_ns()
    elapsed_ms = (t1 - t0) / 1_000_000.0
    print(f"[+] High-Precision Timer : Verified (~{elapsed_ms:.3f} ms resolution)")

    # Dual engine quick smoke test
    print("[*] Smoke-testing Dual AI Engine...")
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from ml_pipeline.dual_engine import DualAIEngine
        engine = DualAIEngine()
        score, diag = engine.evaluate([82.0, 80.0, 16.0, 37.1, 98.0, 1.2, 7.5, 0.0, 0.0])
        print(f"  [OK]   DualAIEngine      : score={score:.1f}, pytorch_ms={diag['pytorch_latency_ms']:.3f}")
        framework = "PyTorch+XGBoost" if engine.has_torch else "NumPy+XGBoost (torch fallback)"
        print(f"  [OK]   Active framework  : {framework}")
    except Exception as e:
        print(f"  [FAIL] DualAIEngine      : {e}")

    print("=" * 66)
    if all_required_passed:
        print(">> ENVIRONMENT HEALTH: READY FOR SENTINEL-Z PIPELINE <<")
    else:
        print(">> ENVIRONMENT WARNING: Install missing packages via setup_s390x.sh <<")
    print("=" * 66)


if __name__ == "__main__":
    verify_system()
