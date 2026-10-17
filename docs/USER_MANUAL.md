# IBM Sentinel-Z: Comprehensive User Manual & Operator's Guide

> **Enterprise In-Transaction Clinical Deterioration & Sepsis Interception Platform**  
> *Target Silicon: IBM z16 / LinuxONE (`s390x`) & IBM Telum AI Co-Processor*  
> *Author: Project Sentinel-Z Engineering Team*

---

## 1. Platform Overview & Navigation Architecture

Sentinel-Z provides real-time clinical deterioration surveillance inside the hospital transactional commit loop. The interface is organized into **3 Core Zones**:

1. **Top Header Control Cluster:** Global streaming controls, authentic PhysioNet patient replays, audio chime settings, and gateway liveness monitoring.
2. **Left Enterprise Sidebar:** Navigation across 8 operational views, host silicon architecture status, and live alert threshold counters.
3. **Main Operational Stage:** Dynamic workspace displaying bedside units, explainability studios, or audit ledgers depending on the active view.

```
┌────────────────────────────────────────────────────────────────────────────────────────────────┐
│ [IBM] Sentinel-Z     ICU Bedside Units   [IBM z16 Telum]  [Alert Budget <2.0]   [Replay] [Load]│
├─────────────────────┬──────────────────────────────────────────────────────────────────────────┤
│ - Clinical Monitor  │                                                                          │
│   • ICU Bedside     │  [Bed 01: p000028 - 92.4% RED]    [Bed 02: p000001 - 12.1% GREEN]       │
│   • Txn Ledger      │  (INTERCEPT & ESCALATE)            (COMMITTED TO EHR)                    │
│ - Decision Intel    │  Latency: 0.074 ms                 Latency: 0.052 ms                     │
│   • TreeSHAP Studio │  [ View Clinical Dossier ]         [ View Clinical Dossier ]             │
│   • watsonx Copilot │                                                                          │
│ - Hardware & Intel  │                                                                          │
│   • PhysioNet Cohort│                                                                          │
│   • Telum Specs     │                                                                          │
│   • Alert Budget    │                                                                          │
│   • Db2 Ledger      │                                                                          │
└─────────────────────┴──────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Top Header Controls (Button-by-Button Guide)

### 2.1 Cohort Replay Dropdown & Button
* **Where It Lives:** Top bar, middle-left.
* **Options in Dropdown:**
  * `p000028`: Acute Sepsis Deterioration (Onset Hour 22, 31 hours total) — **Septic Patient**.
  * `p000011`: Rapid Sepsis-3 Trajectory (Onset Hour 25, 34 hours total) — **Septic Patient**.
  * `p000001`: Stable Non-Septic ICU Stay (54 hours total) — **Control Patient**.
  * `p000002`: Post-Operative Monitored Recovery (23 hours total) — **Control Patient**.
* **What Happens When You Click `Replay`:**
  1. The platform connects to `/api/v1/patients/benchmark/{patient_id}` and streams the patient's hourly physiological records sequentially.
  2. For septic patients (e.g., `p000028`), the monitor starts green (normal postoperative recovery), and at **Hour 21**, as lactate and blood pressure collapse, the bed turns **RED** with a high-priority bedside alarm — **5.2 hours before irreversible septic shock**.
* **Why It Exists:** Proves clinical validity on **authentic de-identified ICU data** from the *PhysioNet / Computing in Cardiology Challenge 2019* rather than arbitrary mock data.

---

### 2.2 "Stream Load" Button
* **Where It Lives:** Top bar, next to the replay cluster.
* **What It Does:**
  * Toggles continuous background synthetic telemetry generation across multiple ICU beds.
  * Streams physiological vitals at 1–2 transactions per second, calculating sub-millisecond PyTorch + XGBoost risk scores on the fly.
* **Visual Indicator:** The small circle turns pulsing green when active, and the button label switches to **Stop Stream**.
* **Why It Exists:** Demonstrates enterprise high-throughput capacity, showing that LinuxONE scores incoming vitals inside the transaction loop without batch delays or server slowdowns.

---

### 2.3 "Audio Toggle" Button
* **Where It Lives:** Top bar, speaker icon.
* **States:**
  * `Audio Muted` (Gray border / default): Visual alerts only.
  * `Audio Active` (Blue fill / active): Emits a pleasant, dual-tone medical chime (880 Hz / 440 Hz sine tone synthesized via standard Web Audio API).
* **When It Sounds:** Only when a patient breaches the active Sepsis-3 threshold ($\ge 70\%$).
* **Why It Exists:** Complies with hospital ICU auditory alarm standards (**IEC 60601-1-8**). Nurses caring for multiple beds cannot stare at a screen 24/7; the audio chime alerts them to imminent hemodynamic decompensation immediately.

---

### 2.4 "Online / Connection Status" Pill
* **Where It Lives:** Top bar, far right.
* **States:**
  * `Online` (Green): Backend gateway is active and responding to `/health` probes.
  * `Degraded / Offline` (Amber/Red): Gateway is unreachable or the **Fail-Visible Circuit Breaker** has tripped.
* **Why It Exists:** Continuous enterprise health and circuit breaker state verification.

---

### 2.5 "⚡ Guided Tour" Button (Interactive Onboarding)
* **Where It Lives:** Top bar, right side.
* **What It Does:** Launches the interactive step-by-step spotlight tour across the platform. Automatically fires on initial load/refresh, highlighting key buttons one-by-one with contextual tooltips, progress dots, and a **"Skip Tour"** button for immediate dismissal.
* **Keyboard Shortcuts:** `Right Arrow` (Next Step), `Left Arrow` (Previous Step), `Escape` (Skip Tour).

---

### 2.6 "📖 User Manual" Button
* **Where It Lives:** Top bar, adjacent to Guided Tour.
* **What It Does:** Opens the in-app modal manual explaining every button, screen, clinical signal, and HIPAA/FHIR data policy on demand, with a 1-click button to launch the Guided Tour.

---

## 3. Left Navigation Sidebar (Screen-by-Screen Guide)

### 3.1 "ICU Bedside Units" (Default Monitor View)
* **What It Shows:** Multi-bed interactive telemetry cards. Each card displays:
  * Patient ID, Age, Gender, and Current Hour.
  * Risk Score Gauge (0% to 100%).
  * Current Vitals Grid: Heart Rate (HR), Blood Pressure (MAP), Respiratory Rate, Temp, SpO2, Lactate, WBC.
  * In-Transaction Latency badge (e.g. `0.074 ms`).
  * Action Banner: `COMMITTED TO EHR` (Green) vs. `INTERCEPT & ESCALATE` (Red).

### 3.2 "Transaction Ledger"
* **What It Shows:** An exhaustive, real-time tabular ledger of every single clinical observation processed since gateway startup.
* **Key Columns:** Timestamp, Patient ID, Action, Latency (ms), and Circuit Breaker state.

### 3.3 "TreeSHAP XAI Studio"
* **What It Shows:** Mathematical Explainable AI (XAI) breakdown.
* **Features:**
  * Bar chart ranking the exact physiological features driving the risk score.
  * Proves whether hypotension (MAP), hyperlactatemia, or tachypnea caused the alarm.
  * Shows the sum of Shapley values ($\sum \phi_i$) for full clinical auditability.

### 3.4 "watsonx.ai Copilot"
* **What It Shows:** Asynchronous clinical decision-support summaries synthesized by **IBM Granite 3.0** on watsonx.ai.
* **Safety Features:** Operates behind the **FDA CDS Granite Output Guardrail**, ensuring the summary explains physiological evidence without prescribing unauthorized medication dosages or hallucinating numbers.

### 3.5 "PhysioNet 2019 Cohort Registry"
* **What It Shows:** Complete patient profiles of the 8 ICU benchmark cases with demographic data, total stay hours, septic onset timestamps, and clinical case descriptions.

### 3.6 "IBM Telum Specs"
* **What It Shows:** Detailed hardware and architectural specification of the **IBM Telum on-chip AI accelerator (NNPA)**, direct-attached cache interconnects, and comparison against commodity x86 cloud servers.

### 3.7 "Alert Budget Controller" (Novel AI Differentiator)
* **What It Shows:**
  * Active dynamic threshold (dynamically modulated between 60.0% and 85.0%).
  * Target alarm budget: $< 2.0$ false alarms per bed per day.
  * Projected 24-hour alarm frequency.
  * Status badge: `CONTROLLED` vs. `ELEVATED`.
* **Clinical Purpose:** Solves the #1 clinical adoption barrier—**alarm fatigue**—documented in Wong et al. (*JAMA Internal Medicine*, 2021).

### 3.8 "Db2 Audit Ledger" (Mainframe Persistence)
* **What It Shows:**
  * Live immutable table of transactions committed to the persistent database (`SENTINEL_AUDIT`).
  * Total commits count, average in-transaction latency, and transaction IDs (`Txn #`).
  * Demonstrates how Sentinel-Z acts as an in-transaction interceptor before final commit.

---

## 4. Patient Card & Dossier Controls

### 4.1 "View Clinical Dossier" Button
* **Where It Lives:** Bottom of each bedside card.
* **What It Does:** Opens the comprehensive **Patient Clinical Dossier Modal Drawer**, showing:
  1. Complete high-resolution vitals grid with normal reference ranges.
  2. qSOFA (quick Sepsis-related Organ Failure Assessment) score calculation.
  3. Ranked TreeSHAP physiological attribution percentages.
  4. IBM Granite 3.0 Clinical Triage Rationale.

### 4.2 "Export FHIR R4 Bundle (.json)" Button
* **Where It Lives:** Inside the Clinical Dossier modal footer.
* **What It Does:** Dynamically generates and downloads an official **HL7 FHIR R4 JSON document** containing:
  * `Patient` resource with clinical identifiers.
  * `RiskAssessment` resource with exact prediction probabilities and algorithmic attribution.
* **Clinical Purpose:** Enables 1-click interoperability with hospital electronic health record systems (Epic Systems, Cerner / Oracle Health).

---

## 5. Sidebar Bottom Controls

### 5.1 Host Hardware Badge
* **Displays:** Current host architecture (`s390x` on LinuxONE or `AMD64/ARM64` in emulation).
* **Status Dot:** Green indicator confirming hardware execution health.

### 5.2 "Gateway Configuration" Button
* **What It Does:** Opens the Gateway Configuration modal allowing users or evaluators to point the frontend to a remote IBM LinuxONE Community Cloud IP address (e.g. `http://148.100.x.x:8000`).
