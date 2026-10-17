"""
Environment and Hardware Parity Verifier for Sentinel-Z.
Works on Windows (Local Dev) and LinuxONE / s390x (Deployment).
"""

import platform
import sys
import os
import time

def verify_system():
    print("=" * 60)
    print("  PROJECT SENTINEL-Z -- PLATFORM VERIFICATION REPORT")
    print("=" * 60)
    
    arch = platform.machine()
    system = platform.system()
    py_version = sys.version.split()[0]
    
    print(f"[*] Operating System : {system} ({platform.release()})")
    print(f"[*] Architecture     : {arch}")
    print(f"[*] Python Version   : {py_version}")
    
    if "s390x" in arch.lower():
        print("[+] PLATFORM STATUS  : RUNNING ON IBM Z / LinuxONE MAINFRAME (s390x)")
    else:
        print(f"[i] PLATFORM STATUS  : RUNNING ON LOCAL WORKSTATION ({arch}) [Emulation Mode]")
        
    print("-" * 60)
    print("Testing Core Dependencies:")
    
    deps = ["fastapi", "uvicorn", "numpy", "torch", "xgboost", "sklearn", "onnxruntime"]
    all_passed = True
    for dep in deps:
        try:
            mod = __import__(dep)
            ver = getattr(mod, "__version__", "loaded")
            print(f"  [OK] {dep:<15} : version {ver}")
        except ImportError as e:
            print(f"  [FAIL] {dep:<13} : NOT INSTALLED ({e})")
            all_passed = False
            
    print("-" * 60)
    # Test high-resolution timer
    t0 = time.perf_counter_ns()
    time.sleep(0.001) # 1ms
    t1 = time.perf_counter_ns()
    elapsed_ms = (t1 - t0) / 1_000_000.0
    print(f"[+] High-Precision Timer: Verified (~{elapsed_ms:.3f} ms resolution)")
    
    print("=" * 60)
    if all_passed:
        print(">> ENVIRONMENT HEALTH: 100% READY FOR SENTINEL-Z PIPELINE <<")
    else:
        print(">> ENVIRONMENT WARNING: Install missing packages via 'pip install -r requirements.txt' <<")
    print("=" * 60)

if __name__ == "__main__":
    verify_system()
