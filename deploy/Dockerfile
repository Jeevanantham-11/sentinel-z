# ==============================================================================
# Sentinel-Z: Multi-Architecture Container Engine (x86_64 and s390x)
# Compatible with Docker and Podman on IBM LinuxONE Community Cloud
#
# Build:
#   docker build -t sentinel-z .
# Run:
#   docker run -p 8000:8000 sentinel-z
# ==============================================================================

FROM python:3.10-slim

# Set environment flags
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install system utilities & OpenMP for XGBoost/PyTorch s390x acceleration
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    sqlite3 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (excluding torch — handled below per arch)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir fastapi "uvicorn[standard]" pydantic websockets \
        requests python-dotenv numpy scipy scikit-learn xgboost onnx onnxruntime pandas

# Install PyTorch conditionally:
#   s390x: attempt pip; falls back gracefully to NumPy stage in dual_engine.py
#   x86_64/amd64: standard torch CPU wheel
RUN ARCH=$(uname -m) && \
    if [ "$ARCH" = "s390x" ]; then \
        pip install --no-cache-dir torch --extra-index-url https://download.pytorch.org/whl/cpu 2>/dev/null || \
        echo "PyTorch not available for s390x via pip; using NumPy fallback (see dual_engine.py)"; \
    else \
        pip install --no-cache-dir "torch>=2.0.0"; \
    fi

# Copy application source
COPY . /app

# Create non-root application user for enterprise security compliance
RUN useradd -m -u 1001 sentinel && \
    chown -R sentinel:sentinel /app

USER sentinel

# Expose unified gateway port
EXPOSE 8000

# Health check probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start In-Transaction Gateway
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

