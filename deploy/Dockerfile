# ==============================================================================
# Sentinel-Z: Multi-Architecture Container Engine (x86_64 and s390x)
# Compatible with Docker and Podman on IBM LinuxONE Community Cloud
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
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . /app

# Create non-root application user for enterprise security compliance
RUN useradd -m -u 1001 sentinel && \
    chown -R sentinel:sentinel /app

USER sentinel

# Expose unified gateway port
EXPOSE 8000

# Health check probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start In-Transaction Gateway
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
