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
    echo "[!] Proceeding in emulation / compatibility mode..."
else
    echo "[+] SUCCESS: Running natively on IBM Z / LinuxONE architecture (s390x)!"
fi

# 2. System dependencies (Ubuntu / Debian or RHEL)
echo "[*] Checking Python3 & Pip..."
if command -v apt-get &> /dev/null; then
    sudo apt-get update -y
    sudo apt-get install -y python3 python3-pip python3-venv git
elif command -v dnf &> /dev/null; then
    sudo dnf install -y python3 python3-pip git
fi

# 3. Virtual Environment Setup
echo "[*] Initializing dedicated virtual environment..."
python3 -m venv venv || python3 -m venv .venv
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# 4. Install dependencies
echo "[*] Installing Python dependencies..."
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt || pip install fastapi uvicorn onnx onnxruntime xgboost numpy scikit-learn requests python-dotenv

# 5. Run Verification
echo "[*] Verifying runtime environment..."
python deploy/verify_env.py

echo "=============================================================="
echo "  DEPLOYMENT READY! To launch Sentinel-Z:"
echo "    source venv/bin/activate || source .venv/bin/activate"
echo "    python backend/main.py"
echo "=============================================================="
