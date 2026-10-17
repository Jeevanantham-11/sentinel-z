"""
Sentinel-Z: Core In-Transaction Ingestion Gateway & API Server.
Simulates IBM z/OS Connect and IBM Watson Machine Learning for z/OS (WMLz).
Serves the unified frontend and executes sub-millisecond hot-path inference.
"""

import time
import os
import sys
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Structured logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("sentinel-z.gateway")

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.state_store import InMemoryStateStore
from backend.latency_tracker import LatencyTracker
from ml_pipeline.feature_schema import calculate_heuristic_sepsis_score
from ml_pipeline.dual_engine import DualAIEngine
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

state_store = InMemoryStateStore()
latency_tracker = LatencyTracker()
watsonx_agent = WatsonxClinicalAgent()
dual_ai_engine = DualAIEngine()

class PatientTelemetry(BaseModel):
    patient_id: str = Field(..., description="Unique anonymized clinical identifier")
    hr: float = Field(80.0, ge=20.0, le=300.0, description="Heart Rate (bpm)")
    map: float = Field(85.0, ge=10.0, le=250.0, description="Mean Arterial Pressure (mmHg)")
    resp: float = Field(16.0, ge=4.0, le=80.0, description="Respiratory Rate (breaths/min)")
    temp: float = Field(37.0, ge=30.0, le=45.0, description="Body Temperature (Celsius)")
    o2sat: float = Field(98.0, ge=50.0, le=100.0, description="Oxygen Saturation (%)")
    lactate: float = Field(1.2, ge=0.1, le=30.0, description="Serum Lactate (mmol/L)")
    wbc: float = Field(7.5, ge=0.1, le=100.0, description="White Blood Cell count (10^9/L)")

@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """System liveness and readiness probe for enterprise monitoring."""
    import platform
    return {
        "status": "healthy",
        "service": "Sentinel-Z In-Transaction Gateway",
        "platform": platform.machine(),
        "ai_frameworks": ["PyTorch", "XGBoost"],
        "llm_engine": "IBM Granite 3.0",
        "total_processed": latency_tracker.total_transactions
    }

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """Serves the integrated command center console."""
    ui_path = BASE_DIR / "frontend" / "index.html"
    if ui_path.exists():
        with open(ui_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h3>Sentinel-Z Gateway Active. UI file not found.</h3>")

@app.post("/api/v1/telemetry", status_code=status.HTTP_200_OK)
async def ingest_telemetry(data: PatientTelemetry):
    """
    In-Transaction Hot Path (< 4ms SLA).
    Scores clinical observation prior to EHR ledger commit.
    """
    t_start = time.perf_counter_ns()
    
    try:
        # 1. In-Memory State Update O(1)
        buffer = state_store.get_or_create(data.patient_id)
        buffer.add_observation(data.dict())
        features = buffer.get_feature_vector()
        
        # 2. In-Transaction Dual-Framework Model Inference (PyTorch + XGBoost on Telum)
        risk_score, diagnostics = dual_ai_engine.evaluate(features)
        
        t_end = time.perf_counter_ns()
        inference_ms = (t_end - t_start) / 1_000_000.0
        latency_tracker.record(inference_ms)
        
        # 3. Deterministic Sepsis-3 Early Warning Triage Decision
        is_critical = risk_score >= 70.0
        action = "INTERCEPT & ESCALATE" if is_critical else "COMMITTED TO EHR"
        
        # 4. Asynchronous Warm-Path GenAI Synthesis via IBM Granite
        rationale = None
        if is_critical:
            rationale = await watsonx_agent.generate_triage_rationale(
                patient_id=data.patient_id,
                risk_score=risk_score,
                vitals=data.dict()
            )
            logger.warning("Critical interception triggered for %s (Score: %.1f%%)", data.patient_id, risk_score)
            
        metrics = latency_tracker.get_metrics()
        
        return {
            "status": "success",
            "patient_id": data.patient_id,
            "risk_score": round(risk_score, 1),
            "action": action,
            "inference_latency_ms": round(inference_ms, 3),
            "diagnostics": diagnostics,
            "vitals": data.dict(),
            "rationale": rationale,
            "metrics": metrics
        }
    except Exception as exc:
        t_end = time.perf_counter_ns()
        inference_ms = (t_end - t_start) / 1_000_000.0
        logger.error("Fail-Open Circuit Breaker activated for %s: %s", data.patient_id, str(exc))
        
        # Zero-Downtime Resilience: Fallback to deterministic clinical rules
        vitals_dict = data.dict()
        fallback_features = [
            vitals_dict.get("hr", 80.0), vitals_dict.get("map", 85.0),
            vitals_dict.get("resp", 16.0), vitals_dict.get("temp", 37.0),
            vitals_dict.get("o2sat", 98.0), vitals_dict.get("lactate", 1.2),
            vitals_dict.get("wbc", 7.5), 0.0, 0.0
        ]
        fallback_score = calculate_heuristic_sepsis_score(fallback_features)
        
        return {
            "status": "circuit_breaker_active",
            "patient_id": data.patient_id,
            "risk_score": round(fallback_score, 1),
            "action": "COMMITTED TO EHR [CIRCUIT BREAKER FALLBACK]",
            "inference_latency_ms": round(inference_ms, 3),
            "diagnostics": {
                "circuit_breaker": True,
                "fallback_mode": "deterministic_heuristic_fail_open",
                "error": str(exc)
            },
            "vitals": vitals_dict,
            "rationale": None,
            "metrics": latency_tracker.get_metrics()
        }

@app.get("/api/v1/metrics", status_code=status.HTTP_200_OK)
async def get_system_metrics():
    """Returns real-time p50, p95, p99 latency distributions."""
    return latency_tracker.get_metrics()

@app.get("/api/v1/patients/benchmark", status_code=status.HTTP_200_OK)
async def list_benchmark_patients():
    """Lists authentic de-identified ICU patients from the PhysioNet 2019 dataset."""
    import json
    manifest_path = BASE_DIR / "data" / "benchmark_patients" / "manifest.json"
    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"patient_count": 0, "patients": []}

@app.get("/api/v1/patients/benchmark/{patient_id}", status_code=status.HTTP_200_OK)
async def get_benchmark_patient(patient_id: str):
    """Retrieves hour-by-hour clinical telemetry for an authentic PhysioNet patient."""
    import json
    clean_id = patient_id.replace(".json", "")
    patient_path = BASE_DIR / "data" / "benchmark_patients" / f"{clean_id}.json"
    if not patient_path.exists():
        raise HTTPException(status_code=404, detail=f"Benchmark patient {patient_id} not found")
    with open(patient_path, "r", encoding="utf-8") as f:
        return json.load(f)

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    logger.info("Initializing Sentinel-Z Gateway on %s:%d", host, port)
    uvicorn.run("backend.main:app", host=host, port=port, reload=False)
