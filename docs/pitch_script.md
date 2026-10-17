# Project Sentinel-Z: 3-Minute Video Demo Script & Pitch Guide

> **IBM Z Datathon 2026** — *Track 1: Real-Time AI for Critical Decisions*  
> Target Duration: **2 Minutes 50 Seconds to 3 Minutes**

---

## 1. Video Structure & Timing

```
0:00 ─── 0:40 ─── 1:15 ────────────── 2:20 ────────────── 3:00
 │         │        │                  │                   │
Problem   Mainframe Hardware     Live Pipeline Demo    Conclusion &
& Impact   SLA & Telum Pitch     & LinuxONE Telemetry  Enterprise Value
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
  > We built **Project Sentinel-Z** to solve this: an in-transaction clinical intelligence engine built natively for the IBM Z mainframe."

---

### [0:40 - 1:15] The Mainframe Solution & Architecture
* **Visual:** Split-screen showing the 4-Plane Architecture (Hot Path vs. Warm Path) and an SSH terminal connected to LinuxONE running `uname -m`.
* **Speaker:**
  > "Rather than bringing the data to external cloud AI, Sentinel-Z brings the AI directly to the transactional boundary. 
  > 
  > We decoupled the architecture into two dedicated paths:
  > First, a **Hot Path** executing inside the transaction loop using ONNX and IBM Machine Learning for z/OS (WMLz), leveraging the Telum processor's on-chip matrix acceleration. It scores incoming HL7 vitals in under 4 milliseconds before the record commits.
  > 
  > Second, an asynchronous **Warm Path** that triggers only on high-risk detections, prompting IBM watsonx.ai to generate grounded, explainable triage briefs for bedside nurses—without slowing down core transaction throughput."

---

### [1:15 - 2:25] The Live Demonstration (LinuxONE & Web Dashboard)
* **Visual:** Browser showing the Sentinel-Z Dark-Mode Command Center, live transactions streaming, latency meter staying under 4ms, and an alert card popping up.
* **Speaker:**
  > "Here is our live deployment running on the LinuxONE Community Cloud environment. 
  > 
  > As you see on the dashboard, we are streaming high-concurrency HL7 and FHIR clinical telemetry into our z/OS Connect ingestion gateway. 
  > 
  > Notice our in-transaction latency meter: our median p50 latency is under 1 millisecond, and p99 stays well under our 4-millisecond SLA. 
  > 
  > Watch what happens when Patient ICU-114 experiences an acute drop in Mean Arterial Pressure and a spike in lactate. 
  > 
  > Instantly, the transaction is intercepted. Within the same millisecond, the risk score hits 91%. And on the right, the asynchronous watsonx.ai engine generates this precise, hallucination-free clinical brief: *'Patient ICU-114: Severe hypotension (MAP 58) and hyperlactatemia (3.4 mmol/L). High risk of septic shock onset. Immediate vasopressor evaluation recommended per Sepsis-3 protocol.'*"

---

### [2:25 - 3:00] Business Impact & Summary
* **Visual:** Summary slide showing: Zero Cloud Egress, Sub-4ms Determinism, Grounded AI for Good.
* **Speaker:**
  > "With Sentinel-Z, sensitive patient data never leaves on-premise mainframe memory boundaries. We eliminate cloud egress latency, prevent clinical alert fatigue, and empower rapid response teams hours before irreversible shock sets in. 
  > 
  > That is the power of Transactional AI on IBM Z. Thank you."
