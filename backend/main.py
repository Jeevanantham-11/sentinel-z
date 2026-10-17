"""
Sentinel-Z: Core In-Transaction Ingestion Gateway & API Server.
Simulates IBM z/OS Connect and IBM Watson Machine Learning for z/OS (WMLz).
Serves the unified frontend and executes sub-millisecond hot-path inference.
"""

import time
import os
import sys
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add parent directory to path for clean imports
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.state_store import InMemoryStateStore
from backend.latency_tracker import LatencyTracker
from ml_pipeline.feature_schema import calculate_heuristic_sepsis_score
from warm_path.watsonx_agent import WatsonxClinicalAgent

app = FastAPI(
    title="Sentinel-Z In-Transaction Gateway",
    description="IBM Z / LinuxONE Real-Time Sepsis Deterioration Interception Engine",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global State and Services
state_store = InMemoryStateStore()
latency_tracker = LatencyTracker()
watsonx_agent = WatsonxClinicalAgent()

class PatientTelemetry(BaseModel):
    patient_id: str
    hr: float = 80.0
    map: float = 85.0
    resp: float = 16.0
    temp: float = 37.0
    o2sat: float = 98.0
    lactate: float = 1.2
    wbc: float = 7.5

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """Serves the unified Command Center UI without needing external ports."""
    ui_path = BASE_DIR / "frontend" / "index.html"
    if ui_path.exists():
        with open(ui_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h3>Sentinel-Z Gateway Active. UI file not found.</h3>")

@app.post("/api/v1/telemetry")
async def ingest_telemetry(data: PatientTelemetry):
    """
    THE HOT PATH (< 4ms SLA)
    Executes In-Transaction scoring before committing observation.
    """
    t_start = time.perf_counter_ns()
    
    # 1. In-Memory State Update O(1)
    buffer = state_store.get_or_create(data.patient_id)
    buffer.add_observation(data.dict())
    features = buffer.get_feature_vector()
    
    # 2. In-Transaction Model Inference (Telum NNPA / WMLz Emulation)
    # Sub-millisecond matrix evaluation
    risk_score = calculate_heuristic_sepsis_score(features)
    
    t_end = time.perf_counter_ns()
    inference_ms = (t_end - t_start) / 1_000_000.0
    latency_tracker.record(inference_ms)
    
    # 3. Action Decision: Safe Commit vs. Intercept
    is_critical = risk_score >= 80.0
    action = "INTERCEPT & ESCALATE" if is_critical else "COMMITTED TO EHR"
    
    # 4. Asynchronous Warm-Path trigger for Critical events
    rationale = None
    if is_critical:
        # Out-of-band asynchronous call (does not block database throughput)
        rationale = await watsonx_agent.generate_triage_rationale(
            patient_id=data.patient_id,
            risk_score=risk_score,
            vitals=data.dict()
        )
        
    metrics = latency_tracker.get_metrics()
    
    return {
        "status": "success",
        "patient_id": data.patient_id,
        "risk_score": round(risk_score, 1),
        "action": action,
        "inference_latency_ms": round(inference_ms, 3),
        "vitals": data.dict(),
        "rationale": rationale,
        "metrics": metrics
    }

@app.get("/api/v1/metrics")
async def get_system_metrics():
    """Returns real-time p50, p95, p99 latency distributions."""
    return latency_tracker.get_metrics()

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("  LAUNCHING PROJECT SENTINEL-Z IN-TRANSACTION GATEWAY")
    print("  Unified Port: 8000 | Web UI: http://localhost:8000")
    print("=" * 60)
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=False)
