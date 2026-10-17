# Project Sentinel-Z: 3-Minute Video Demo Script & Recording Walkthrough

> **IBM Z Datathon 2026** — *Track 1: Real-Time AI for Critical Decisions*  
> Target Duration: **2 Minutes 50 Seconds to 3 Minutes (Strict Maximum: 3:00)**  
> Compulsory Submission Rule: *Video demo must show the LinuxONE instance and the model running.*

---

## 1. Video Structure & Timing

```
0:00 ─── 0:40 ─── 1:10 ────────────────────── 2:25 ────────────── 3:00
 │         │        │                          │                   │
Problem   Mainframe Hardware             Live Carbon UI      Conclusion &
& Impact   SLA & Telum Pitch          & LinuxONE Benchmark   Enterprise Value
```

---

## 2. Shot-by-Shot Teleprompter Script

### [0:00 - 0:40] The Problem & The Latency Dilemma
* **Visual:** Slide showing "Sepsis mortality increases by 7.6% per hour of delay" and the clinical dilemma.
* **Speaker:**
  > "In the Intensive Care Unit, timing is literal life and death. Hospital sepsis mortality increases by 7.6% for every single hour intervention is delayed.
  > 
  > But today's healthcare architectures fail this critical latency window. Existing EHR systems rely on batch queries running 15 to 60 minutes after data is committed. On the other hand, routing patient telemetry to external cloud AI APIs introduces 200 to 500 milliseconds of network round-trip latency, risking database queue lockups and violating HIPAA data sovereignty.
  > 
  > We built **Project Sentinel-Z** to solve this: an in-transaction clinical deterioration interception engine built natively for the IBM Z mainframe."

---

### [0:40 - 1:10] The Mainframe Solution & Architecture
* **Visual:** Split-screen showing the 4-Plane Architecture (Hot Path vs. Warm Path) and an SSH terminal connected to LinuxONE running `uname -m` showing `s390x`.
* **Speaker:**
  > "Rather than bringing the data to external cloud AI, Sentinel-Z brings the AI directly to the transactional boundary. 
  > 
  > We decoupled the architecture into two dedicated paths:
  > First, an ultra-fast **Hot Path** executing inside the transaction loop using ONNX and PyTorch, leveraging the IBM Telum processor's on-chip matrix acceleration. It scores incoming HL7 vitals in under 0.5 milliseconds before the record commits.
  > 
  > Second, an asynchronous **Warm Path** that triggers only on high-risk detections, prompting IBM watsonx.ai to generate grounded, explainable triage briefs for bedside nurses—without slowing down core transaction throughput."

---

### [1:10 - 2:25] The Live Demonstration (IBM Carbon Command Center & LinuxONE)
* **Visual (Tab 1 - Live ICU Surveillance):** Browser showing the IBM Carbon Command Center. Click "Replay Patient" for `p000028` (PhysioNet 2019 Acute Sepsis Shock). 
* **Speaker:**
  > "Here is our live deployment running on the LinuxONE Community Cloud environment. 
  > 
  > In Tab 1, our Live ICU Surveillance console ingests continuous HL7 and FHIR streams. Notice our in-transaction latency: our median p50 latency is just 73 microseconds, and p99 stays well under our strict 4-millisecond SLA. 
  > 
  > Watch what happens when Patient p000028 begins to deteriorate. Within milliseconds, the risk score spikes to 91%. On the right, the asynchronous watsonx.ai engine generates this precise, hallucination-free clinical brief, pinpointing severe hypotension and lactic acidosis."
* **Visual (Tab 2 - TreeSHAP & Dossier Modal):** Click "Clinical Dossier" on the patient card, then switch to Tab 2 (TreeSHAP Explainability).
* **Speaker:**
  > "Clinicians cannot trust black-box scores. In Tab 2, our mathematical TreeSHAP engine breaks down the exact marginal contribution of each vital sign: MAP contributes 34.8%, and Lactate contributes 28.5%. Every LLM summary is mathematically grounded in these exact SHAP values."
* **Visual (Terminal & Tab 4 - LinuxONE Benchmark):** Show LinuxONE terminal running `python deploy/benchmark_s390x.py` outputting >11,000 TPS, then switch to Tab 4 showing IBM Telum NNPA hardware specifications.
* **Speaker:**
  > "Over in our LinuxONE terminal, our benchmark proves sustained throughput exceeding 11,000 transactions per second on native s390x hardware."

---

### [2:25 - 3:00] Business Impact & Summary
* **Visual:** Slide 9 & 10 from Pitch Deck showing: \$1.8M Annual Savings, Zero Cloud Egress, Sub-Millisecond Determinism.
* **Speaker:**
  > "With Sentinel-Z, sensitive patient data never leaves on-premise mainframe memory boundaries. We eliminate cloud egress latency, prevent clinical alert fatigue, and intercept septic shock 5.2 hours before irreversible organ damage. 
  > 
  > That is the power of Real-Time AI for Critical Decisions on IBM Z. Thank you."
