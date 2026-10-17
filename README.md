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
│  Ingestion Gateway (z/OS Connect / FastAPI Gateway Simulator)│
│  - Port 8000 (Ingestion & WebSocket Hub)                    │
└──────────────┬──────────────────────────────────────────────┘
               │  In-Memory Rolling State Buffer (O(1))
               ▼
┌─────────────────────────────────────────────────────────────┐
│  HOT PATH (< 4ms) — Dual AI In-Transaction Engine           │
│  - Stage 1: PyTorch Latent Temporal Autoencoder             │
│  - Stage 2: XGBoost Sepsis-3 Calibrated Classifier          │
│  - Native IBM Telum NNPA Matrix Acceleration                │
│  - Strict 5ms Fail-Open Circuit Breaker                     │
└──────────────┬──────────────────────────────┬───────────────┘
  Commit Safe  │                              │ Alert Threshold (>80%)
               ▼                              ▼
┌──────────────────────────────┐  ┌───────────────────────────┐
│ Database Ledger (Commits)    │  │ WARM PATH (Asynchronous)  │
│ - Transaction writes without │  │ - Event Broker Queue      │
│   delaying patient care      │  │ - IBM Granite 3.0 Agent   │
└──────────────────────────────┘  │ - Grounded by TreeSHAP    │
                                  └─────────────┬─────────────┘
                                                │ Explanatory Brief
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
| **Member 1** | **ML & Modeling Lead** | • PhysioNet 2019 dataset training pipeline<br>• PyTorch Latent Autoencoder + XGBoost Classifier<br>• Model artifact serialization & TreeSHAP ranking | `ml_pipeline/dual_engine.py`<br>`ml_pipeline/train_dual_framework.py`<br>`ml_pipeline/models/` |
| **Member 2** | **Backend & Hot Path Lead** | • z/OS Connect API simulator (FastAPI)<br>• In-memory 6-hour rolling state buffer (O(1))<br>• Sub-4ms dual-engine executor & latency tracker<br>• High-velocity HL7/FHIR streaming generator | `backend/main.py`<br>`backend/state_store.py`<br>`data_simulator/hl7_generator.py` |
| **Member 3** | **Frontend & Dashboard Lead** | • Real-time clinical triage dashboard<br>• Live throughput (TPS) & sub-4ms latency meters<br>• ICU vitals telemetry graphs (HR, MAP, Lactate)<br>• Emergency alert banner with IBM Granite rationales | `frontend/index.html` |
| **Member 4** | **Warm Path & LinuxONE Deploy Lead** | • Asynchronous watsonx.ai IBM Granite 3.0 worker<br>• Docker/Podman multi-arch containerization<br>• LinuxONE deployment scripts (`setup_s390x.sh`)<br>• CLI latency benchmark tool (`benchmark_s390x.py`) | `warm_path/watsonx_agent.py`<br>`deploy/setup_s390x.sh`<br>`deploy/benchmark_s390x.py`<br>`deploy/Dockerfile` |

---

## 4. Development Workflow: Windows ➔ GitHub ➔ LinuxONE

1. **Local Engineering (Windows Workstations):**
   * Each member works on their designated folder/branch.
   * Test scripts locally via `python deploy/verify_env.py`.
2. **Git Integration:**
   * Merge features into `main`.
   * Cross-platform line endings are enforced via `.gitattributes` (`*.sh text eol=lf`).
3. **LinuxONE Cloud Deployment:**
   * SSH into your LinuxONE Community Cloud instance:
     ```bash
     git clone https://github.com/Jeevanantham-11/sentinel-z.git
     cd sentinel-z
     bash deploy/setup_s390x.sh
     ```
   * Or run containerized with Docker/Podman:
     ```bash
     docker build -f deploy/Dockerfile -t sentinel-z .
     docker run -d -p 8000:8000 sentinel-z
     ```
4. **Demonstration & Benchmarking:**
   * Run the CLI benchmark on LinuxONE:
     ```bash
     python deploy/benchmark_s390x.py --iter 2000
     ```

---

## 5. Quickstart (Local Test)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Verify platform & AI frameworks
python deploy/verify_env.py

# 3. Run Dual-AI CLI Benchmark
python deploy/benchmark_s390x.py --iter 1000

# 4. Start Ingestion Gateway & Web Console
python backend/main.py

# 5. In another terminal, stream synthetic hospital transactions
python data_simulator/hl7_generator.py
```
