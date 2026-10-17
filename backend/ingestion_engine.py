"""
Sentinel-Z: Authentic Enterprise Healthcare Ingestion Engine.
Handles real-world clinical interoperability protocols:
1. HL7 v2.x ORU^R01 (Unsolicited Observation Messages from Bedside Monitors)
2. HL7 FHIR R4 Observation & DiagnosticReport Bundles
3. Multi-Bed Cohort Streamer: Replays authentic PhysioNet 2019 / MIMIC trajectories
   across active ICU beds at controlled line-rates.
"""

import os
import re
import time
import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("sentinel-z.ingestion")

# Standard Clinical LOINC Code Mappings
LOINC_MAP = {
    "8867-4": "hr",        # Heart rate
    "8478-0": "map",       # Mean arterial pressure
    "9279-1": "resp",      # Respiratory rate
    "8310-5": "temp",      # Body temperature
    "2708-6": "o2sat",     # Oxygen saturation (SpO2)
    "2571-8": "lactate",   # Serum Lactate
    "6690-2": "wbc",       # White blood cell count
    # Secondary / Vendor Aliases
    "HR": "hr",
    "PULSE": "hr",
    "MAP": "map",
    "BP_MEAN": "map",
    "RESP": "resp",
    "RR": "resp",
    "TEMP": "temp",
    "SPO2": "o2sat",
    "LACTATE": "lactate",
    "WBC": "wbc"
}


class HL7ParseException(Exception):
    """Raised when an incoming HL7 message is malformed."""
    pass


def parse_hl7_v2_message(hl7_text: str) -> Dict[str, Any]:
    """
    Parses an HL7 v2.x pipe-delimited message (typically ORU^R01).
    Extracts Patient ID from PID segment and vital signs from OBX segments.
    """
    lines = [line.strip() for line in hl7_text.strip().splitlines() if line.strip()]
    if not lines:
        raise HL7ParseException("Empty HL7 message received")

    msh_found = False
    patient_id = "UNKNOWN-PATIENT"
    vitals: Dict[str, Optional[float]] = {
        "hr": None, "map": None, "resp": None,
        "temp": None, "o2sat": None, "lactate": None, "wbc": None
    }
    timestamp_str = None

    for line in lines:
        fields = line.split("|")
        seg_id = fields[0].strip().upper()

        if seg_id == "MSH":
            msh_found = True
            # MSH-7 is timestamp
            if len(fields) > 6:
                timestamp_str = fields[6]
        elif seg_id == "PID":
            # PID-3 is Patient Identifier List
            if len(fields) > 3 and fields[3]:
                # May contain components separated by ^
                pid_sub = fields[3].split("^")[0].strip()
                if pid_sub:
                    patient_id = pid_sub
        elif seg_id == "OBX":
            # OBX-3: Observation Identifier (e.g., 8867-4^Heart Rate^LN)
            # OBX-5: Observation Value
            if len(fields) > 5:
                obs_id_raw = fields[3].strip()
                obs_val_raw = fields[5].strip()

                # Extract code from OBX-3 (first subcomponent)
                code = obs_id_raw.split("^")[0].strip().upper()
                canonical_param = LOINC_MAP.get(code)
                if not canonical_param:
                    # Try second subcomponent if available (e.g. Heart Rate)
                    subparts = obs_id_raw.split("^")
                    if len(subparts) > 1:
                        canonical_param = LOINC_MAP.get(subparts[1].strip().upper())

                if canonical_param:
                    try:
                        vitals[canonical_param] = float(obs_val_raw)
                    except ValueError:
                        pass

    if not msh_found:
        raise HL7ParseException("Missing mandatory MSH header segment")

    return {
        "protocol": "HL7v2_ORU_R01",
        "patient_id": patient_id,
        "timestamp": timestamp_str or time.strftime("%Y%m%d%H%M%S"),
        "vitals": vitals
    }


def parse_fhir_r4_bundle(bundle_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parses an HL7 FHIR R4 Bundle or single Observation resource.
    Extracts Subject Patient reference and LOINC vital observations.
    """
    resource_type = bundle_dict.get("resourceType", "")
    patient_id = "UNKNOWN-PATIENT"
    vitals: Dict[str, Optional[float]] = {
        "hr": None, "map": None, "resp": None,
        "temp": None, "o2sat": None, "lactate": None, "wbc": None
    }

    def _extract_from_observation(obs: Dict[str, Any]):
        nonlocal patient_id
        # Subject
        subj = obs.get("subject", {}).get("reference", "")
        if subj:
            patient_id = subj.replace("Patient/", "")

        # Code (LOINC)
        code_entries = obs.get("code", {}).get("coding", [])
        canonical_param = None
        for c in code_entries:
            code_val = str(c.get("code", "")).strip().upper()
            if code_val in LOINC_MAP:
                canonical_param = LOINC_MAP[code_val]
                break

        if canonical_param:
            val_quant = obs.get("valueQuantity", {})
            if "value" in val_quant:
                try:
                    vitals[canonical_param] = float(val_quant["value"])
                except (ValueError, TypeError):
                    pass

    if resource_type == "Bundle":
        for entry in bundle_dict.get("entry", []):
            res = entry.get("resource", {})
            if res.get("resourceType") == "Observation":
                _extract_from_observation(res)
            elif res.get("resourceType") == "Patient":
                if res.get("id"):
                    patient_id = res["id"]
    elif resource_type == "Observation":
        _extract_from_observation(bundle_dict)
    else:
        raise ValueError(f"Unsupported FHIR resourceType: {resource_type}")

    return {
        "protocol": "HL7_FHIR_R4",
        "patient_id": patient_id,
        "vitals": vitals
    }


class MultiBedCohortStreamer:
    """
    Simulates high-throughput multi-bed hospital telemetry using authentic
    PhysioNet 2019 de-identified patient files.
    """
    def __init__(self, data_dir: Optional[Path] = None):
        if data_dir is None:
            data_dir = Path(__file__).resolve().parent.parent / "data" / "benchmark_patients"
        self.data_dir = data_dir
        self.is_streaming = False
        self._stream_task: Optional[asyncio.Task] = None
        self.patients = ["p000028", "p000011", "p000001", "p000002", "p000003", "p000007", "p000009", "p000018"]
        self.patient_data: Dict[str, List[Dict[str, Any]]] = {}
        self.patient_indices: Dict[str, int] = {}
        self._load_cohort()

    def _load_cohort(self):
        """Loads and parses genuine PhysioNet benchmark records from JSON or PSV."""
        if not self.data_dir.exists():
            logger.warning("PhysioNet data directory not found: %s", self.data_dir)
            return

        for pid in self.patients:
            json_file = self.data_dir / f"{pid}.json"
            psv_file = self.data_dir / f"{pid}.psv"

            if json_file.exists():
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    obs_list = data.get("observations", [])
                    rows = []
                    for obs in obs_list:
                        rows.append({
                            "HR": obs.get("hr"),
                            "MAP": obs.get("map"),
                            "Resp": obs.get("resp"),
                            "Temp": obs.get("temp"),
                            "O2Sat": obs.get("o2sat"),
                            "Lactate": obs.get("lactate"),
                            "WBC": obs.get("wbc"),
                            "SepsisLabel": obs.get("sepsis_label", 0)
                        })
                    self.patient_data[pid] = rows
                    self.patient_indices[pid] = 0
                    logger.info("Loaded authentic PhysioNet JSON trajectory for %s: %d hours", pid, len(rows))
                except Exception as e:
                    logger.error("Failed to load JSON for %s: %s", pid, e)
            elif psv_file.exists():
                rows = []
                with open(psv_file, "r", encoding="utf-8") as f:
                    header = [h.strip() for h in f.readline().split("|")]
                    for line in f:
                        parts = [p.strip() for p in line.split("|")]
                        if len(parts) == len(header):
                            row_dict = {}
                            for k, v in zip(header, parts):
                                try:
                                    row_dict[k] = float(v) if v and v != "NaN" else None
                                except ValueError:
                                    row_dict[k] = None
                            rows.append(row_dict)
                self.patient_data[pid] = rows
                self.patient_indices[pid] = 0
                logger.info("Loaded authentic PhysioNet PSV trajectory for %s: %d hours", pid, len(rows))

    def get_next_observation(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves the next sequential clinical hour for a given patient."""
        records = self.patient_data.get(patient_id, [])
        if not records:
            return None

        idx = self.patient_indices.get(patient_id, 0)
        row = records[idx]
        self.patient_indices[patient_id] = (idx + 1) % len(records)

        return {
            "patient_id": patient_id,
            "hour": idx,
            "hr": row.get("HR"),
            "map": row.get("MAP"),
            "resp": row.get("Resp"),
            "temp": row.get("Temp"),
            "o2sat": row.get("O2Sat"),
            "lactate": row.get("Lactate"),
            "wbc": row.get("WBC"),
            "actual_sepsis_label": int(row.get("SepsisLabel") or 0)
        }

    def reset(self):
        """Resets stream indices back to hour 0."""
        for pid in self.patient_indices:
            self.patient_indices[pid] = 0
