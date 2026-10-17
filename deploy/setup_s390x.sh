#!/usr/bin/env bash
# ==============================================================================
# Sentinel-Z: LinuxONE (s390x) Automated Deployment Script
# Run this directly on your LinuxONE Community Cloud instance:
#   bash deploy/setup_s390x.sh
# ==============================================================================

set -e

echo "=============================================================="
echo "  PROJECT SENTINEL-Z -- LINUXONE DEPLOYMENT ENGINE"
echo "=============================================================="

# 1. Architecture Check
ARCH=$(uname -m)
echo "[*] Detected Architecture: $ARCH"
if [ "$ARCH" != "s390x" ]; then
    echo "[!] WARNING: System is $ARCH (Expected s390x for IBM Z / LinuxONE)."
    echo "[!] Proceeding in compatibility mode..."
else
    echo "[+] SUCCESS: Running natively on IBM Z / LinuxONE (s390x)!"
fi

# 2. System dependencies (Ubuntu / Debian or RHEL)
echo "[*] Checking system dependencies..."
if command -v apt-get &> /dev/null; then
    sudo apt-get update -y
    sudo apt-get install -y python3 python3-pip python3-venv git sqlite3 libgomp1
elif command -v dnf &> /dev/null; then
    sudo dnf install -y python3 python3-pip git sqlite libgomp
fi

# 3. Virtual Environment Setup
echo "[*] Initializing dedicated virtual environment..."
python3 -m venv venv
source venv/bin/activate

# 4. Upgrade pip
pip install --upgrade pip setuptools wheel

# 5. Install all non-torch dependencies first
echo "[*] Installing core dependencies (s390x-safe)..."
pip install fastapi "uvicorn[standard]" pydantic websockets requests python-dotenv \
            numpy scipy scikit-learn xgboost onnx onnxruntime pandas

# 6. PyTorch for s390x — try IBM Open CE channel first, then whl, then skip gracefully
echo "[*] Attempting PyTorch installation for s390x..."
if [ "$ARCH" = "s390x" ]; then
    # Attempt 1: IBM Open CE (recommended, requires conda)
    if command -v conda &> /dev/null; then
        echo "[*] conda found — installing PyTorch via IBM Open CE..."
        conda install -y -c https://opence.mit.edu pytorch || echo "[!] IBM Open CE install failed — trying pip..."
    fi
    # Attempt 2: pip install (may succeed on newer s390x builds)
    if ! python3 -c "import torch" 2>/dev/null; then
        pip install torch --extra-index-url https://download.pytorch.org/whl/cpu 2>/dev/null || true
    fi
    # Fallback: Sentinel-Z has a CPU-math fallback in dual_engine.py — will still run
    if ! python3 -c "import torch" 2>/dev/null; then
        echo "[!] PyTorch not available on this s390x build."
        echo "[!] Sentinel-Z will run in NumPy-fallback mode for the PyTorch stage."
        echo "[!] Full functionality: install PyTorch via IBM Open CE (see requirements.txt)."
    else
        echo "[+] PyTorch successfully installed!"
    fi
else
    # x86/local dev: standard pip install
    pip install "torch>=2.0.0"
fi

# 7. Run Verification
echo "[*] Verifying runtime environment..."
python3 deploy/verify_env.py

echo "=============================================================="
echo "  DEPLOYMENT READY! To launch Sentinel-Z:"
echo "    source venv/bin/activate"
echo "    python3 backend/main.py"
echo "  API Docs: http://<your-linuxone-ip>:8000/docs"
echo "=============================================================="

