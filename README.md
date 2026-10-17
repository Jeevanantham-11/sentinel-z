# Project Sentinel-Z: In-Transaction Clinical Interception for Sepsis Deterioration

> **IBM Z Datathon 2026** — *Track 1: Real-Time AI for Critical Decisions*  
> Deployable on **IBM Z / LinuxONE (`s390x`)** and Local Workstations.

---

## 1. Executive Summary

Hospital sepsis mortality increases by **7.6% for every hour antimicrobial intervention is delayed** following septic shock onset. Current Electronic Health Record (EHR) systems fail this critical latency window:
1. **Embedded EHR Batch Analytics (Epic / Cerner):** Evaluate patient observations 15 to 60 minutes *after* database commit, causing delayed intervention and chronic alarm fatigue.
2. **External Cloud AI Startups:** Egressing high-velocity clinical telemetry off-premise adds 200–500ms network round-trip latency, I/O queue backpressure, and data-residency compliance exposure under HIPAA zero-trust frameworks.

**Project Sentinel-Z** introduces **In-Transaction Clinical Interception**: bringing predictive ML directly to the transactional ingestion boundary before database commit.

---

## 2. Decoupled 4-Plane Architecture

```
[ Bedside ICU Monitors & Labs ]
               │
               ▼  (HL7 v2 / FHIR R4 Streaming)
┌─────────────────────────────────────────────────────────────┐
│  Ingestion Gateway (z/OS Connect / FastAPI Mock)            │
│  - Port 8000 (Ingestion & WebSocket Hub)                    │
└──────────────┬──────────────────────────────────────────────┘
               │  In-Memory Rolling State Buffer (O(1))
               ▼
┌─────────────────────────────────────────────────────────────┐
│  HOT PATH (< 4ms) — In-Transaction Inference Engine         │
│  - ONNX Runtime / IBM WMLz emulation                        │
│  - Sepsis-3 calibrated risk scoring (0 - 100)               │
│  - Strict 5ms fail-open timeout                             │
│  - Telum on-chip matrix acceleration abstraction            │
└──────────────┬──────────────────────────────┬───────────────┘
  Commit Safe  │                              │ Alert Threshold (>85%)
               ▼                              ▼
┌──────────────────────────────┐  ┌───────────────────────────┐
│ Database Ledger (Commits)    │  │ WARM PATH (Asynchronous)  │
│ - Transaction writes without │  │ - Event Broker Queue      │
│   delaying patient care      │  │ - watsonx.ai GenAI Agent  │
└──────────────────────────────┘  │ - Grounded by TreeSHAP    │
                                  └─────────────┬─────────────┘
                                                │ Explanatory Rationale
                                                ▼
                                  ┌───────────────────────────┐
                                  │ Live Command Center (UI)  │
                                  │ - Latency Gauge (<4ms)    │
                                  │ - Streaming Vitals Feed   │
                                  │ - Actionable Nurse Alerts │
                                  └───────────────────────────┘
```

---

## 3. Team Responsibilities (4-Member Division)

To prevent merge conflicts and ensure parallel velocity, the workload is partitioned into four distinct modules:

| Member | Title / Domain | Primary Responsibilities | Deliverables |
| :--- | :--- | :--- | :--- |
| **Member 1** | **ML & Modeling Lead** | • PhysioNet 2019 dataset preprocessing<br>• XGBoost / LightGBM training<br>• Model export to `.onnx`<br>• TreeSHAP feature extraction logic | `ml_pipeline/train_model.py`<br>`ml_pipeline/models/sepsis_model.onnx`<br>`ml_pipeline/feature_schema.py` |
| **Member 2** | **Backend & Hot Path Lead** | • z/OS Connect API simulator (FastAPI)<br>• In-memory 6-hour rolling state buffer<br>• Sub-4ms ONNX executor with `perf_counter_ns`<br>• High-velocity HL7/FHIR streaming generator | `backend/main.py`<br>`backend/state_store.py`<br>`data_simulator/hl7_generator.py` |
| **Member 3** | **Frontend & Dashboard Lead** | • Real-time clinical triage dashboard<br>• Live throughput (TPS) & sub-4ms latency meters<br>• ICU vitals telemetry graphs (HR, MAP, Lactate)<br>• Emergency alert banner with GenAI rationales | `frontend/index.html`<br>`frontend/app.js` (or React/Vite)<br>`frontend/styles.css` |
| **Member 4** | **Warm Path & LinuxONE Deploy Lead** | • Asynchronous queue worker<br>• watsonx.ai prompt template & grounding<br>• LinuxONE deployment scripts (`setup_s390x.sh`)<br>• 3-minute presentation script & video editing | `warm_path/watsonx_agent.py`<br>`deploy/setup_s390x.sh`<br>`docs/pitch_script.md` |

---

## 4. Development Workflow: Windows ➔ GitHub ➔ LinuxONE

1. **Local Engineering (Windows Workstations):**
   * Each member works on their designated folder/branch (`feature/ml`, `feature/backend`, `feature/ui`, `feature/warm-path`).
   * Test scripts locally via `python deploy/verify_env.py`.
2. **Git Integration:**
   * Merge features into `main`.
   * Cross-platform line endings are enforced via `.gitattributes` (`*.sh text eol=lf`).
3. **LinuxONE Cloud Deployment:**
   * SSH into your LinuxONE Community Cloud instance:
     ```bash
     git clone <YOUR_GITHUB_REPO_URL>
     cd sentinel-z
     bash deploy/setup_s390x.sh
     ```
   * Run the end-to-end pipeline:
     ```bash
     source venv/bin/activate
     python backend/main.py
     ```
4. **Demonstration & Benchmarking:**
   * Run the synthetic HL7 streamer to generate 1,000 TPS.
   * Verify measured inference latency ($<4\text{ ms}$) and capture terminal output showing `s390x`.

---

## 5. Quickstart (Local Test)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Verify platform
python deploy/verify_env.py

# 3. Start Backend Ingestion Gateway
python backend/main.py

# 4. In another terminal, start the synthetic HL7 telemetry stream
python data_simulator/hl7_generator.py
```
