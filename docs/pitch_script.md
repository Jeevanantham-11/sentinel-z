# Project Sentinel-Z: 3-Minute Video Demo Script & Recording Walkthrough

> **IBM Z Datathon 2026** — *Track 1: Real-Time AI for Critical Decisions*  
> Target Duration: **2 Minutes 50 Seconds to 3 Minutes (Strict Maximum: 3:00)**  
> Compulsory Submission Rule: *Video demo must show the LinuxONE instance and the model running.*

---

## 1. Video Structure & Timing

```
0:00 ─── 0:40 ─── 1:10 ────────────────────── 2:20 ────────────── 3:00
 │         │        │                          │                   │
Problem   Mainframe Continuous           Live Carbon UI      Conclusion, FDA CDS
& Impact  Surveillance & Hardware     & LinuxONE Benchmark   & Enterprise Value
```

---

## 2. Shot-by-Shot Teleprompter Script

### [0:00 - 0:40] The Problem: Sepsis Lead Time & Alert Fatigue
* **Visual:** Slide showing "Sepsis mortality rises 7.6% per hour of delay" and "The Alert Fatigue Crisis (Epic Sepsis Model: 67% False Alarms)".
* **Speaker:**
  > "In the ICU, timing is literal life and death. Sepsis mortality increases by 7.6% for every single hour treatment is delayed.
  > 
  > But today's hospital surveillance systems fail clinicians in two critical ways:
  > First, batch delays: standard EHR queries run only every 15 to 60 minutes, losing precious early intervention windows.
  > Second, alert fatigue: legacy systems like the Epic Sepsis Model suffer from up to 67% false alarms, causing doctors to ignore warnings. Meanwhile, sending telemetry to public cloud APIs violates HIPAA data sovereignty and introduces network failure risks.
  > 
  > We built **Project Sentinel-Z**: a continuous, in-transaction clinical deterioration interception engine running natively on IBM Z and LinuxONE."

---

### [0:40 - 1:10] The Mainframe Architecture: Bringing AI to Core Transactions
* **Visual:** Split-screen showing the 4-Plane Architecture (Hot Path vs. Warm Path) and an SSH terminal connected to LinuxONE showing `uname -m` = `s390x`.
* **Speaker:**
  > "Rather than exporting patient telemetry to external cloud servers, Sentinel-Z brings intelligence directly to the transactional system of record.
  > 
  > We decoupled the architecture into two dedicated planes:
  > 
  > 1. A sub-millisecond **Hot Path**: Incoming HL7 and FHIR vitals are embedded via PyTorch using the IBM Telum processor's on-chip matrix accelerator (NNPA via ONNX/zDNN) and classified by calibrated XGBoost on native s390x cores before transaction commit.
  > 
  > 2. An asynchronous **Warm Path**: Triggers only when risk exceeds threshold, using pure-Python TreeSHAP to calculate exact physiological feature impacts, and prompting IBM Granite 3.0 on watsonx.ai to generate grounded Clinical Decision Support briefings."

---

### [1:10 - 2:20] The Live Demonstration (IBM Carbon Console & LinuxONE Proof)
* **Visual (Tab 1 - ICU Bedside Surveillance):** Browser showing the IBM Carbon Command Center at `http://localhost:8000`. Click "Cohort Replay" for `p000028` (PhysioNet 2019 Acute Sepsis Shock). 
* **Speaker:**
  > "Here is our live platform running on the IBM LinuxONE Community Cloud environment.
  > 
  > In Tab 1, bedside units continuously stream physiological telemetry. Notice our in-transaction latency: median latency is just 73 microseconds, well inside our strict 4-millisecond SLA.
  > 
  > Watch as we replay Patient p000028 from the authentic PhysioNet 2019 ICU cohort. While standard hospital monitors miss early deterioration, Sentinel-Z flags acute risk at Hour 21—**5.2 hours before clinical shock onset**.
  > 
  > On the right, our watsonx.ai Granite copilot summarizes evidence for nursing triage under FDA Clinical Decision Support guidance—surfacing risk without hallucinating or prescribing."
* **Visual (Tab 2 - TreeSHAP Studio & Dossier):** Click "Clinical Dossier" on the patient card, then switch to Tab 2 (TreeSHAP Studio).
* **Speaker:**
  > "Clinicians reject black-box scores. In Tab 2, our pure-Python TreeSHAP engine proves the mathematical cause: Mean Arterial Pressure contributes +34.8% and Lactate contributes +28.5% to the risk escalation. Doctors see exactly why the alert fired."
* **Visual (Terminal - LinuxONE Benchmark & Specs):** Show LinuxONE terminal running `python3 deploy/benchmark_s390x.py` outputting >11,000 TPS, then switch to Tab 6 showing Telum specs.
* **Speaker:**
  > "In our LinuxONE terminal, our benchmark proves sustained throughput exceeding 11,000 evaluations per second on native s390x silicon. And if a model ever hangs, our fail-visible circuit breaker alerts staff and engages backup clinical rules with zero downtime."

---

### [2:20 - 3:00] Regulatory, Business Impact & Conclusion
* **Visual:** Slide showing: FDA CDS Compliance (Cures Act § 3060), \$12,400 Saved Per Intercepted ICU Patient, Zero Cloud Egress.
* **Speaker:**
  > "Sentinel-Z is architected as non-device Clinical Decision Support under FDA 21st Century Cures Act Section 3060, providing transparent mathematical rationale so physicians retain full clinical oversight.
  > 
  > By combining 5.2 hours of validated early lead time with 100% on-premise data sovereignty on IBM LinuxONE, Sentinel-Z protects patients and mainframes alike. 
  > 
  > Real-time AI. Grounded decisions. Zero compromise on IBM Z. Thank you."
