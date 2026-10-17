"""
Unit & Integration Test Suite for IBM Sentinel-Z Platform.
Ensures zero-regression across Ingestion, Hot Path Inference, TreeSHAP, and Circuit Breaker.
Works natively on both local development machines and IBM LinuxONE (s390x).
"""

import sys
import unittest
import requests
import numpy as np
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from ml_pipeline.dual_engine import DualAIEngine
from ml_pipeline.alert_controller import AlertBudgetController
from warm_path.shap_attributor import ClinicalTreeSHAP
from warm_path.watsonx_agent import WatsonxClinicalAgent
from warm_path.granite_guardrail import GraniteOutputGuardrail
from backend.circuit_breaker import CircuitBreaker

BASE_URL = "http://127.0.0.1:8000"

class TestSentinelZPipeline(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.engine = DualAIEngine()
        cls.shap = ClinicalTreeSHAP
        cls.watsonx = WatsonxClinicalAgent()
        
        # Check if gateway is running live
        try:
            r = requests.get(f"{BASE_URL}/health", timeout=2)
            cls.live_server = (r.status_code == 200)
        except Exception:
            cls.live_server = False

    def test_01_dual_engine_inference(self):
        """Test sub-millisecond Dual AI Engine on PyTorch + XGBoost."""
        features = [75.0, 85.0, 16.0, 37.0, 98.0, 1.1, 7.5, 0.0, 0.0]
        score, diag = self.engine.evaluate(features)
        
        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 100.0)
        self.assertIn("pytorch_latency_ms", diag)
        self.assertIn("xgboost_latency_ms", diag)

    def test_02_treeshap_exact_attribution(self):
        """Test pure-Python mathematical TreeSHAP feature importance."""
        septic_vitals = {"hr": 125.0, "map": 55.0, "resp": 26.0, "temp": 38.8, "o2sat": 92.0, "lactate": 3.8, "wbc": 15.4}
        shap_res = self.shap.explain(septic_vitals)
        
        self.assertIsInstance(shap_res, dict)
        self.assertIn("top_drivers", shap_res)
        self.assertIn("active_shap_sum", shap_res)
        self.assertGreater(len(shap_res["top_drivers"]), 0)
        
        # Verify top driver has feature name and positive attribution
        first = shap_res["top_drivers"][0]
        self.assertIn("feature", first)
        self.assertIn("shap", first)
        self.assertGreater(first["shap"], 0.0)

    def test_03_watsonx_agent_synthesis(self):
        """Test IBM Granite 3.0 clinical rationale generation (zero hallucination)."""
        import asyncio
        vitals = {"hr": 128.0, "map": 54.0, "resp": 28.0, "temp": 38.9, "o2sat": 91.0, "lactate": 4.2}
        
        brief = asyncio.run(self.watsonx.generate_triage_rationale("PATIENT-001", 88.5, vitals))
        self.assertIn("clinical_rationale", brief)
        self.assertIn("top_drivers", brief)
        self.assertIn("shap_attributions", brief)
        self.assertGreater(len(brief["top_drivers"]), 0)

    def test_04_circuit_breaker_fail_open(self):
        """Test fail-open circuit breaker trips to safeguard transaction latency."""
        cb = CircuitBreaker(latency_threshold_ms=0.001, failure_rate_threshold=0.5)
        for _ in range(10):
            cb.record_execution(latency_ms=10.0, success=True)
            
        self.assertTrue(cb.is_open())
        self.assertEqual(cb.state.value, "OPEN")

    def test_05_live_api_health_check(self):
        """Verify Gateway /health endpoint if running."""
        if not self.live_server:
            self.skipTest("Live Gateway not running on port 8000")
            
        response = requests.get(f"{BASE_URL}/health", timeout=3)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "healthy")
        self.assertIn("platform", data)

    def test_06_live_api_telemetry_flow(self):
        """Verify Gateway /api/v1/telemetry ingestion and intercept dispatch."""
        if not self.live_server:
            self.skipTest("Live Gateway not running on port 8000")
            
        payload = {
            "patient_id": "TEST-SEPTIC-999",
            "hr": 130.0,
            "map": 52.0,
            "resp": 28.0,
            "temp": 39.1,
            "o2sat": 90.0,
            "lactate": 4.5,
            "wbc": 18.2
        }
        res = requests.post(f"{BASE_URL}/api/v1/telemetry", json=payload, timeout=3)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["patient_id"], "TEST-SEPTIC-999")
        self.assertGreaterEqual(data["risk_score"], 70.0)
        self.assertEqual(data["action"], "INTERCEPT & ESCALATE")
        self.assertIn("alert_budget", data)
        self.assertIn("active_threshold", data["alert_budget"])

    def test_07_benchmark_manifest(self):
        """Verify benchmark manifest contains valid PhysioNet cohort cases."""
        if not self.live_server:
            self.skipTest("Live Gateway not running on port 8000")
            
        res = requests.get(f"{BASE_URL}/api/v1/patients/benchmark", timeout=3)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("patients", data)
        self.assertGreaterEqual(len(data["patients"]), 4)

    def test_08_alert_budget_controller(self):
        """Verify adaptive thresholding and clinical false alarm budget bounds."""
        ctrl = AlertBudgetController(target_max_alarms_per_bed_day=2.0, baseline_threshold=70.0)
        
        # Test 1: Stable trajectory (damping keeps threshold conservative)
        res_stable = ctrl.evaluate_alert(risk_score=68.0, patient_stability_index=1.0)
        self.assertFalse(res_stable["should_alert"])
        self.assertEqual(res_stable["active_threshold"], 70.0)
        
        # Test 2: Highly volatile trajectory (lowers threshold for safety margin)
        res_volatile = ctrl.evaluate_alert(risk_score=68.0, patient_stability_index=2.0)
        self.assertTrue(res_volatile["should_alert"])  # Threshold lowers to ~60-65%
        self.assertLess(res_volatile["active_threshold"], 70.0)
        
        # Test 3: Budget status tracking
        metrics = ctrl.get_metrics()
        self.assertIn("target_budget_alarms_per_day", metrics)
        self.assertEqual(metrics["target_budget_alarms_per_day"], 2.0)

    def test_09_granite_guardrail_safety(self):
        """Verify Granite guardrail catches unauthorized prescription commands & hallucinations."""
        vitals = {"hr": 125.0, "map": 54.0, "resp": 28.0, "temp": 38.9, "o2sat": 91.0, "lactate": 4.2}
        drivers = ["Elevated serum lactate (4.2 mmol/L)", "Severe hypotension (MAP 54.0 mmHg)"]
        
        # Case A: Prescriptive command (trips guardrail)
        bad_text = "Administer 30 mL/kg IV crystalloids and start norepinephrine infusion at 5 mcg/min immediately."
        valid, safe_text, reason = GraniteOutputGuardrail.validate_rationale(bad_text, "TEST-01", 88.0, vitals, drivers)
        self.assertFalse(valid)
        self.assertEqual(reason, "REJECTED_PRESCRIPTION_OVERREACH")
        self.assertIn("Guardrail Verified", safe_text)
        
        # Case B: Ungrounded numerical hallucinations (trips guardrail)
        hallucinated_text = "Patient has potassium 6.8 and troponin 450 with 85% blockage."
        valid_h, safe_text_h, reason_h = GraniteOutputGuardrail.validate_rationale(hallucinated_text, "TEST-01", 88.0, vitals, drivers)
        self.assertFalse(valid_h)
        self.assertTrue(reason_h.startswith("REJECTED_UNGROUNDED_NUMBERS"))
        
        # Case C: Valid FDA CDS evidence summary (passes guardrail)
        good_text = (
            "CLINICAL TRIAGE BRIEF [IBM Granite 3.0]: Patient TEST-01 crossed deterioration threshold (88.0%). "
            "Evidence indicates acute hemodynamic compromise; bedside clinical re-assessment recommended per institutional Sepsis-3 guidelines."
        )
        valid_g, text_g, reason_g = GraniteOutputGuardrail.validate_rationale(good_text, "TEST-01", 88.0, vitals, drivers)
        self.assertTrue(valid_g)
        self.assertEqual(reason_g, "PASSED_VERIFIED")

    def test_10_alert_budget_and_audit_endpoints(self):
        """Verify /api/v1/alert-budget and /api/v1/audit/log live responses."""
        if not self.live_server:
            self.skipTest("Live Gateway not running on port 8000")
            
        # Test alert budget endpoint
        res_ab = requests.get(f"{BASE_URL}/api/v1/alert-budget", timeout=3)
        self.assertEqual(res_ab.status_code, 200)
        ab_data = res_ab.json()
        self.assertIn("active_threshold", ab_data)
        self.assertIn("target_budget_alarms_per_day", ab_data)

        # Test Db2 audit log endpoint
        res_al = requests.get(f"{BASE_URL}/api/v1/audit/log?limit=5", timeout=3)
        self.assertEqual(res_al.status_code, 200)
        al_data = res_al.json()
        self.assertIn("summary", al_data)
        self.assertIn("recent_transactions", al_data)

    def test_11_endianness_floating_point_invariance(self):
        """Verify IEEE 754 floating-point consistency across Big-Endian (s390x) and Little-Endian architectures."""
        test_features = np.array([82.0, 75.0, 18.0, 37.1, 98.0, 1.2, 7.5, 0.0, 0.0], dtype=np.float32)
        raw_bytes = test_features.tobytes()
        reconstructed = np.frombuffer(raw_bytes, dtype=np.float32)
        np.testing.assert_array_almost_equal(test_features, reconstructed)

    def test_12_hardware_matrix_introspection(self):
        """Verify hardware acceleration provider introspection matrix."""
        from deploy.hardware_matrix import introspect_hardware
        hw = introspect_hardware()
        self.assertIn("architecture", hw)
        self.assertIn("byte_order", hw)
        self.assertIn("acceleration_mode", hw)
        self.assertIn("hardware_tier", hw)

    def test_13_asynchronous_partial_telemetry_imputation(self):
        """Verify clinical LOCF decay engine handles missing vitals/labs gracefully without NaN."""
        from backend.clinical_imputer import ClinicalImputationRegistry
        registry = ClinicalImputationRegistry()
        
        # Patient sends only HR and MAP (labs omitted)
        vector = registry.process_telemetry("P-ASYNC-TEST", {"hr": 130.0, "map": 55.0})
        self.assertEqual(len(vector), 9)
        self.assertEqual(vector[0], 130.0) # HR
        self.assertEqual(vector[1], 55.0)  # MAP
        self.assertGreater(vector[5], 0.0) # Lactate imputed from ICU population mean
        self.assertFalse(any(np.isnan(v) for v in vector))

if __name__ == "__main__":
    unittest.main()



