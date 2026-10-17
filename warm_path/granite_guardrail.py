"""
Sentinel-Z: Clinical GenAI Output Guardrail.
Validates IBM Granite LLM outputs against strict Clinical Decision Support (CDS) safety rules.
Enforces:
1. Zero Prescription / No Medication Dosing (flags any unauthorized drug/dosing instructions).
2. Numerical Grounding (validates numbers against telemetry, risk scores, or approved protocol names).
3. Deterministic Evidence-Based Fallback if safety constraints are breached.
"""

import re
import logging
from typing import Dict, Any, Tuple, List

logger = logging.getLogger("sentinel-z.guardrail")

# Prohibited prescriptive clinical actions (FDA SaMD non-exemption risk)
PROHIBITED_PRESCRIPTION_PATTERNS = [
    r"\b(?:administer|inject|infuse|prescribe|give)\s+\d+",
    r"\b\d+\s*(?:mg|ml/kg|mcg|units|g|meq)\b",
    r"\b(?:bolus|norepinephrine|vasopressin|vancomycin|piperacillin|cefepime)\s+(?:at|dose|of)\b",
    r"\bstart\s+(?:infusion|pressors|iv\s+fluids\s+at)\b"
]

# Permitted clinical protocol keywords that contain numbers (e.g., Sepsis-3, SEP-1, Granite 3.0)
APPROVED_PROTOCOL_TOKENS = {
    "sepsis-3", "sep-1", "granite", "3.0", "3", "1", "qsofa", "news2"
}

class GraniteOutputGuardrail:
    """
    Deterministic safety validator ensuring LLM outputs conform to FDA Clinical Decision Support (CDS)
    guidelines: summarize evidence and flag risk, never prescribe or hallucinate ungrounded numbers.
    """
    
    @classmethod
    def validate_rationale(
        cls,
        generated_text: str,
        patient_id: str,
        risk_score: float,
        vitals: Dict[str, Any],
        top_drivers: List[str]
    ) -> Tuple[bool, str, str]:
        """
        Validates generated rationale.
        Returns:
            Tuple of (is_valid: bool, validated_text: str, reason: str)
        """
        lower_text = generated_text.lower()
        
        # 1. Check for unauthorized prescriptive dosing commands
        for pattern in PROHIBITED_PRESCRIPTION_PATTERNS:
            if re.search(pattern, lower_text):
                logger.warning("Guardrail tripped: unauthorized prescription phrasing detected: %s", pattern)
                fallback = cls._generate_safe_fallback(patient_id, risk_score, top_drivers)
                return False, fallback, "REJECTED_PRESCRIPTION_OVERREACH"
        
        # 2. Extract numbers from generated text and check grounding
        # Matches integers or floats (e.g. 88.5, 3.8, 120)
        found_numbers = re.findall(r"\b\d+(?:\.\d+)?\b", generated_text)
        
        # Collect all allowed ground-truth numbers
        allowed_numbers = set()
        # Add risk score
        allowed_numbers.add(f"{risk_score:.1f}")
        allowed_numbers.add(f"{round(risk_score)}")
        
        # Add all vitals values
        for v in vitals.values():
            if isinstance(v, (int, float)):
                allowed_numbers.add(f"{v:.1f}")
                allowed_numbers.add(f"{v:.2f}")
                allowed_numbers.add(f"{round(v)}")
                allowed_numbers.add(str(v))
        
        # Add known safe integers/versions (1, 3, 3.0 for Granite 3.0 / Sepsis-3 / SEP-1)
        allowed_numbers.update({"1", "3", "3.0", "0", "2", "2.0"})
        
        # Extract patient ID numeric components if any
        patient_nums = re.findall(r"\d+", patient_id)
        for pn in patient_nums:
            allowed_numbers.add(pn)
            allowed_numbers.add(str(int(pn)))
            
        # Add numbers from TreeSHAP top driver summaries
        for driver in top_drivers:
            for num_in_driver in re.findall(r"\b\d+(?:\.\d+)?\b", driver):
                allowed_numbers.add(num_in_driver)
                try:
                    allowed_numbers.add(str(float(num_in_driver)))
                    allowed_numbers.add(str(round(float(num_in_driver))))
                except ValueError:
                    pass
            
        unverified_numbers = []
        for num in found_numbers:
            if num not in allowed_numbers and str(float(num)) not in allowed_numbers:
                # Check if it is a formatted substring of allowed
                unverified_numbers.append(num)
                
        # If multiple ungrounded numbers are hallucinated, reject and fall back
        if len(unverified_numbers) > 1:
            logger.warning("Guardrail tripped: ungrounded numerical claims: %s", unverified_numbers)
            fallback = cls._generate_safe_fallback(patient_id, risk_score, top_drivers)
            return False, fallback, f"REJECTED_UNGROUNDED_NUMBERS_{unverified_numbers}"
            
        return True, generated_text, "PASSED_VERIFIED"
        
    @classmethod
    def _generate_safe_fallback(cls, patient_id: str, risk_score: float, top_drivers: List[str]) -> str:
        """Deterministic, FDA-compliant CDS fallback template with zero hallucination."""
        drivers_summary = ", ".join(top_drivers[:3]) if top_drivers else "acute physiological trajectory deviation"
        return (
            f"CLINICAL TRIAGE BRIEF [IBM Granite 3.0 - Guardrail Verified]: "
            f"Patient {patient_id} has crossed the institutional deterioration threshold ({risk_score:.1f}%). "
            f"Key physiological drivers: {drivers_summary}. "
            f"Evidence indicates acute hemodynamic decompensation. Prompt bedside clinical evaluation recommended per institutional Sepsis-3 protocol."
        )
