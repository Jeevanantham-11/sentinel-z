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
from typing import Optional, Dict, Any
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
from backend.circuit_breaker import CircuitBreaker
from backend.db2_audit_log import Db2AuditLog
from backend.clinical_imputer import ClinicalImputationRegistry
from backend.ingestion_engine import parse_hl7_v2_message, parse_fhir_r4_bundle, MultiBedCohortStreamer
from deploy.hardware_matrix import introspect_hardware
from deploy.profile_hardware import profile_silicon_environment, benchmark_inference_sla
from ml_pipeline.feature_schema import calculate_heuristic_sepsis_score
from ml_pipeline.dual_engine import DualAIEngine
from ml_pipeline.alert_controller import AlertBudgetController
from tests.benchmark_vs_epic import run_comparative_benchmark
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
clinical_imputer = ClinicalImputationRegistry()
latency_tracker = LatencyTracker()
watsonx_agent = WatsonxClinicalAgent()
dual_ai_engine = DualAIEngine()
circuit_breaker = CircuitBreaker(latency_threshold_ms=4.0)
alert_controller = AlertBudgetController(target_max_alarms_per_bed_day=2.0)
db2_audit = Db2AuditLog()


class PatientTelemetry(BaseModel):
    patient_id: str = Field(..., description="Unique anonymized clinical identifier")
    hr: Optional[float] = Field(None, ge=20.0, le=300.0, description="Heart Rate (bpm)")
    map: Optional[float] = Field(None, ge=10.0, le=250.0, description="Mean Arterial Pressure (mmHg)")
    resp: Optional[float] = Field(None, ge=4.0, le=80.0, description="Respiratory Rate (breaths/min)")
    temp: Optional[float] = Field(None, ge=30.0, le=45.0, description="Body Temperature (Celsius)")
    o2sat: Optional[float] = Field(None, ge=50.0, le=100.0, description="Oxygen Saturation (%)")
    lactate: Optional[float] = Field(None, ge=0.1, le=30.0, description="Serum Lactate (mmol/L)")
    wbc: Optional[float] = Field(None, ge=0.1, le=100.0, description="White Blood Cell count (10^9/L)")

@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """System liveness and readiness probe for enterprise monitoring."""
    hw = introspect_hardware()
    return {
        "status": "healthy",
        "service": "Sentinel-Z In-Transaction Gateway",
        "platform": hw["architecture"],
        "hardware_tier": hw["hardware_tier"],
        "acceleration_mode": hw["acceleration_mode"],
        "endian": hw["byte_order"],
        "ai_frameworks": ["PyTorch", "XGBoost"],
        "llm_engine": "IBM Granite 3.0",
        "total_processed": latency_tracker.total_transactions
    }

@app.get("/api/v1/hardware", status_code=status.HTTP_200_OK)
async def get_hardware_info():
    """Hardware introspection and Telum/s390x execution acceleration provider discovery."""
    return introspect_hardware()

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
        # 1. In-Memory State Update with Physiological Decay Imputation (LOCF)
        buffer = state_store.get_or_create(data.patient_id)
        buffer.add_observation(data.dict())
        features = clinical_imputer.process_telemetry(data.patient_id, data.dict())
        
        # 2. In-Transaction Dual-Framework Model Inference (PyTorch + XGBoost on Telum)
        risk_score, diagnostics = dual_ai_engine.evaluate(features)
        
        t_end = time.perf_counter_ns()
        inference_ms = (t_end - t_start) / 1_000_000.0
        latency_tracker.record(inference_ms)
        circuit_breaker.record_execution(inference_ms, success=True)
        
        # 3. Clinical Alert-Budget Regulated Sepsis-3 Early Warning Triage Decision
        alert_decision = alert_controller.evaluate_alert(risk_score, patient_stability_index=1.0)
        is_critical = alert_decision["should_alert"]
        action = "INTERCEPT & ESCALATE" if is_critical else "COMMITTED TO EHR"
        
        # 4. Asynchronous Warm-Path GenAI Synthesis via IBM Granite
        rationale = None
        if is_critical:
            rationale = await watsonx_agent.generate_triage_rationale(
                patient_id=data.patient_id,
                risk_score=risk_score,
                vitals=data.dict()
            )
            logger.warning("Critical interception triggered for %s (Score: %.1f%%, Threshold: %.1f%%)",
                           data.patient_id, risk_score, alert_decision["active_threshold"])
            
        metrics = latency_tracker.get_metrics()
        
        # 5. Db2 Audit Log COMMIT — every scored transaction is persisted to the ledger
        guardrail_status = (rationale or {}).get("guardrail_status", "N/A")
        txn_id = db2_audit.commit_transaction(
            patient_id=data.patient_id,
            risk_score=risk_score,
            action=action,
            inference_ms=inference_ms,
            guardrail=guardrail_status,
            alert_status=alert_decision.get("alert_fatigue_status", "CONTROLLED"),
            cb_state=circuit_breaker.get_status().get("state", "CLOSED")
        )
        
        return {
            "status": "success",
            "patient_id": data.patient_id,
            "txn_id": txn_id,
            "risk_score": round(risk_score, 1),
            "action": action,
            "inference_latency_ms": round(inference_ms, 3),
            "diagnostics": diagnostics,
            "vitals": data.dict(),
            "rationale": rationale,
            "alert_budget": alert_decision,
            "circuit_breaker": circuit_breaker.get_status(),
            "metrics": metrics
        }
    except Exception as exc:
        t_end = time.perf_counter_ns()
        inference_ms = (t_end - t_start) / 1_000_000.0
        circuit_breaker.record_execution(inference_ms, success=False)
        logger.error("Fail-Visible Circuit Breaker activated for %s: %s", data.patient_id, str(exc))
        
        # Zero-Downtime Resilience: Fallback to deterministic clinical rules
        vitals_dict = data.dict()
        def _get_val(k, default):
            v = vitals_dict.get(k)
            return float(v) if v is not None else float(default)

        fallback_features = [
            _get_val("hr", 80.0), _get_val("map", 85.0),
            _get_val("resp", 16.0), _get_val("temp", 37.0),
            _get_val("o2sat", 98.0), _get_val("lactate", 1.2),
            _get_val("wbc", 7.5), 0.0, 0.0
        ]
        fallback_score = calculate_heuristic_sepsis_score(fallback_features)
        
        # Db2 audit: even failed-path transactions are committed to the ledger
        db2_audit.commit_transaction(
            patient_id=data.patient_id,
            risk_score=fallback_score,
            action="COMMITTED TO EHR [FAIL-VISIBLE CDS FALLBACK]",
            inference_ms=inference_ms,
            guardrail="BYPASS_FALLBACK",
            alert_status="DEGRADED",
            cb_state=circuit_breaker.get_status().get("state", "OPEN")
        )
        
        return {
            "status": "fail_visible_degraded",
            "patient_id": data.patient_id,
            "risk_score": round(fallback_score, 1),
            "action": "COMMITTED TO EHR [FAIL-VISIBLE CDS FALLBACK]",
            "inference_latency_ms": round(inference_ms, 3),
            "diagnostics": {
                "monitoring_state": "FAIL-VISIBLE DEGRADED (Backup Heuristic Rule Active)",
                "circuit_breaker": circuit_breaker.get_status(),
                "error": str(exc)
            },
            "vitals": vitals_dict,
            "rationale": None,
            "circuit_breaker": circuit_breaker.get_status(),
            "metrics": latency_tracker.get_metrics()
        }

@app.get("/api/v1/metrics", status_code=status.HTTP_200_OK)
async def get_system_metrics():
    """Returns real-time p50, p95, p99 latency distributions."""
    return latency_tracker.get_metrics()

@app.get("/api/v1/alert-budget", status_code=status.HTTP_200_OK)
async def get_alert_budget():
    """
    Returns the live Alert-Budget Controller state.
    Shows the adaptive threshold and projected false-alarm rate per bed per day.
    Implements the novel alarm-fatigue mitigation differentiator of Sentinel-Z.
    """
    return {
        "description": "Dynamic alert threshold controller — maintains <2.0 false alarms/bed/day",
        "citation": "Wong et al., JAMA IM 2021 (Epic Sepsis Model: 33% sensitivity, 12% PPV)",
        **alert_controller.get_metrics()
    }

@app.get("/api/v1/audit/log", status_code=status.HTTP_200_OK)
async def get_audit_log(limit: int = 50):
    """
    Returns the last N committed EHR transactions from the Db2 Audit Log.
    Simulates IBM Db2 for z/OS row-level audit table (production: ibm_db connector).
    Integration note: On LinuxONE, replace SQLite with Db2 via ibm_db / ibm_db_sa.
    """
    return {
        "audit_source": "Sentinel-Z Db2 Audit Log (SQLite simulation — ibm_db on production)",
        "integration_note": "Production: CICS/z/OS Connect → scoring → Db2 z/OS COMMIT via ibm_db connector",
        "summary": db2_audit.get_summary(),
        "recent_transactions": db2_audit.get_recent(limit=limit)
    }

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

class HL7IngestPayload(BaseModel):
    raw_message: str = Field(..., description="Raw HL7 v2.x pipe-delimited message (ORU^R01)")

@app.post("/api/v1/ingest/hl7", status_code=status.HTTP_200_OK)
async def ingest_hl7_v2(payload: HL7IngestPayload):
    """
    Hospital Bedside Ingestion: Ingests raw HL7 v2 ORU^R01 observation message.
    Parses MSH, PID, and OBX LOINC observations and executes in-transaction scoring.
    """
    try:
        parsed = parse_hl7_v2_message(payload.raw_message)
        telemetry = PatientTelemetry(
            patient_id=parsed["patient_id"],
            **parsed["vitals"]
        )
        return await ingest_telemetry(telemetry)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"HL7 parse error: {str(exc)}")

@app.post("/api/v1/ingest/fhir", status_code=status.HTTP_200_OK)
async def ingest_fhir(payload: Dict[str, Any]):
    """
    EHR Interoperability: Ingests HL7 FHIR R4 Observation or Bundle resource.
    Extracts Subject Patient reference and LOINC codes for real-time scoring.
    """
    try:
        parsed = parse_fhir_r4_bundle(payload)
        telemetry = PatientTelemetry(
            patient_id=parsed["patient_id"],
            **parsed["vitals"]
        )
        return await ingest_telemetry(telemetry)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"FHIR parse error: {str(exc)}")

@app.get("/api/v1/benchmark/competitive", status_code=status.HTTP_200_OK)
async def get_competitive_benchmark():
    """
    Quantitative head-to-head clinical benchmark:
    Sentinel-Z vs. Epic Sepsis Model (Wong et al. JAMA IM 2021) vs. Traditional qSOFA.
    """
    res = run_comparative_benchmark()
    return {
        "status": "success",
        "benchmark_dataset": "PhysioNet / Computing in Cardiology Challenge 2019",
        "citation": "Wong et al., JAMA Internal Medicine 2021; 38,455 hospitalizations",
        "results": res
    }

@app.get("/api/v1/hardware/profile", status_code=status.HTTP_200_OK)
async def get_hardware_profile():
    """
    Silicon Profiler: Probes CPU architecture, endianness,
    instruction facilities, and benchmarks sustained in-transaction inferences.
    """
    silicon = profile_silicon_environment()
    perf = benchmark_inference_sla(iterations=1000)
    return {
        "silicon_environment": silicon,
        "performance_benchmark": perf
    }

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    logger.info("Initializing Sentinel-Z Gateway on %s:%d", host, port)
    uvicorn.run("backend.main:app", host=host, port=port, reload=False)

