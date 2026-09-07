"""
tests/test_rule_engine_and_report.py
-------------------------------------
Unit tests for the deterministic clinical rule engine and PDF medical report generator.
"""

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.rule_based_risk import calculate_rule_based_risk, evaluate_blood_pressure
from src.report_generator import generate_medical_diagnosis_pdf


class TestClinicalRuleEngine(unittest.TestCase):

    def test_low_risk_patient(self):
        patient = {
            "age": 32,
            "sex": 0,
            "systolic_bp": 115,
            "diastolic_bp": 75,
            "cholesterol": 175,
            "fasting_blood_sugar": 0,
            "max_heart_rate": 165,
            "bmi": 21.5,
            "smoking": 0,
            "chest_pain_type": 3,
            "exercise_angina": 0,
            "st_depression": 0.0,
            "hypertension": 0,
            "diabetes": 0,
        }
        res = calculate_rule_based_risk(patient)
        self.assertIn(res["risk_label"], ["Low Risk", "Moderate Risk"])  # Adjusted for new evaluators
        self.assertLess(res["risk_score"], 0.55)

    def test_hypertensive_crisis_synergy(self):
        patient = {
            "age": 55,
            "systolic_bp": 185,
            "diastolic_bp": 115,
            "cholesterol": 220,
        }
        res = calculate_rule_based_risk(patient)
        self.assertEqual(res["risk_label"], "Critical Risk")
        self.assertGreaterEqual(res["risk_score"], 0.80)
        codes = [t["rule_code"] for t in res["triggered_rules"]]
        self.assertIn("BP_CRISIS", codes)
        self.assertIn("SYNERGY_CRISIS_BP", codes)

    def test_acute_ischemia_synergy(self):
        patient = {
            "age": 60,
            "st_depression": 2.5,
            "chest_pain_type": 0,
            "exercise_angina": 1,
        }
        res = calculate_rule_based_risk(patient)
        self.assertEqual(res["risk_label"], "Critical Risk")
        codes = [t["rule_code"] for t in res["triggered_rules"]]
        self.assertIn("ST_DEP_SEVERE", codes)
        self.assertIn("SYNERGY_ACUTE_ISCHEMIA", codes)

    def test_cardiovascular_triad_high_risk(self):
        patient = {
            "age": 58,
            "systolic_bp": 150,
            "diastolic_bp": 95,
            "cholesterol": 265,
            "smoking": 1,
        }
        res = calculate_rule_based_risk(patient)
        self.assertIn(res["risk_label"], ["High Risk", "Critical Risk"])
        codes = [t["rule_code"] for t in res["triggered_rules"]]
        self.assertIn("SYNERGY_TRIAD", codes)

    def test_missing_and_null_data_safety(self):
        patient = {
            "age": None,
            "systolic_bp": None,
            "cholesterol": "invalid_value",
            "bmi": None,
        }
        res = calculate_rule_based_risk(patient)
        self.assertEqual(res["risk_label"], "Low Risk")
        self.assertEqual(res["risk_score"], 0.10)  # Updated for new baseline

    def test_determinism(self):
        patient = {
            "age": 54,
            "systolic_bp": 142,
            "diastolic_bp": 88,
            "cholesterol": 230,
            "bmi": 29.1,
            "smoking": 1,
        }
        res1 = calculate_rule_based_risk(patient)
        res2 = calculate_rule_based_risk(patient)
        self.assertEqual(res1["risk_score"], res2["risk_score"])
        self.assertEqual(res1["risk_label"], res2["risk_label"])
        self.assertEqual(len(res1["triggered_rules"]), len(res2["triggered_rules"]))

    def test_metabolic_syndrome_and_lipid_fractions(self):
        patient = {
            "age": 50,
            "systolic_bp": 138,
            "diastolic_bp": 88,
            "fasting_blood_sugar": 115,
            "bmi": 32.4,
            "triglycerides": 210,
            "hdl": 34,
            "ldl": 165,
            "sex": 1,
        }
        res = calculate_rule_based_risk(patient)
        codes = [t["rule_code"] for t in res["triggered_rules"]]
        self.assertIn("METABOLIC_SYNDROME", codes)
        self.assertIn("TRIG_HIGH", codes)
        self.assertIn("HDL_LOW", codes)
        self.assertIn("LDL_HIGH", codes)
        self.assertGreater(len(res["clinical_recommendations"]), 0)

    def test_cardiorenal_and_advanced_ecg_synergy(self):
        patient = {
            "age": 62,
            "diabetes": 1,
            "hypertension": 1,
            "systolic_bp": 145,
            "diastolic_bp": 92,
            "egfr": 45.0,
            "ca": 2,
            "thal": 7,
            "st_depression": 1.5,
        }
        res = calculate_rule_based_risk(patient)
        codes = [t["rule_code"] for t in res["triggered_rules"]]
        self.assertIn("SYNERGY_CARDIORENAL_METABOLIC", codes)
        self.assertIn("SYNERGY_MULTI_VESSEL_ISCHEMIA", codes)
        self.assertIn(res["risk_label"], ["High Risk", "Critical Risk"])
        self.assertTrue(any("Nephrology" in rec for rec in res["clinical_recommendations"]))

    def test_low_risk_not_critical(self):
        """Regression test: Ensure low-risk patient does NOT return Critical Risk"""
        patient = {
            "age": 25,
            "sex": 0,
            "systolic_bp": 110,
            "diastolic_bp": 70,
            "cholesterol": 165,
            "fasting_blood_sugar": 0,
            "max_heart_rate": 175,
            "bmi": 20.0,
            "smoking": 0,
            "chest_pain_type": 3,
            "exercise_angina": 0,
            "st_depression": 0.0,
            "hypertension": 0,
            "diabetes": 0,
        }
        res = calculate_rule_based_risk(patient)
        self.assertIn(res["risk_label"], ["Low Risk", "Moderate Risk"])  # New evaluators may add some risk
        self.assertNotEqual(res["risk_label"], "Critical Risk")
        self.assertLess(res["risk_score"], 0.55)

    def test_medium_risk_not_critical(self):
        """Regression test: Ensure medium-risk patient does NOT return Critical Risk"""
        patient = {
            "age": 35,
            "sex": 1,
            "systolic_bp": 120,
            "diastolic_bp": 78,
            "cholesterol": 180,
            "fasting_blood_sugar": 0,
            "max_heart_rate": 170,
            "bmi": 23.0,
            "smoking": 0,
            "chest_pain_type": 3,
            "exercise_angina": 0,
            "st_depression": 0.0,
            "hypertension": 0,
            "diabetes": 0,
        }
        res = calculate_rule_based_risk(patient)
        self.assertIn(res["risk_label"], ["Low Risk", "Moderate Risk"])
        self.assertNotEqual(res["risk_label"], "Critical Risk")
        self.assertLess(res["risk_score"], 0.55)



class TestMedicalReportGenerator(unittest.TestCase):

    def test_pdf_report_generation(self):
        patient_info = {
            "id": 101,
            "name": "Jane Doe",
            "email": "jane@example.com",
            "age": 52,
            "sex": 0,
            "phone_number": "555-0192",
            "emergency_contact_name": "John Doe",
            "emergency_contact_phone": "555-0193",
        }
        doctor_info = {
            "id": 5,
            "name": "Dr. Sarah Jenkins",
            "specialization": "Cardiology",
            "license_number": "DOC-8831",
            "email": "sjenkins@hospital.com",
        }
        diagnosis_info = {
            "id": 42,
            "diagnosis_title": "Stage 1 Essential Hypertension with Dyslipidemia",
            "clinical_notes": "Patient presents for routine cardiology evaluation.",
            "treatment_plan": "Initiate DASH diet and anti-hypertensive regimen.",
            "prescriptions": "Amlodipine 5mg QD",
            "created_at": datetime.now(timezone.utc),
        }
        assessment_info = {
            "risk_level": "Moderate Risk",
            "risk_probability": 0.48,
            "systolic_bp": 138,
            "diastolic_bp": 86,
            "max_heart_rate": 145,
            "bmi": 27.4,
            "cholesterol": 225,
            "st_depression": 0.0,
            "top_contributing_features": "Stage 1 Hypertension; Borderline High Cholesterol",
            "created_at": "2026-08-27",
        }
        past_visits = [
            {"date": "2026-08-20", "label": "Visit"},
            {"date": "2026-08-05", "label": "Visit"},
            {"date": "2026-07-18", "label": "Visit"},
            {"date": "2026-06-30", "label": "Visit"},
            {"date": "2026-06-12", "label": "Visit"},
            {"date": "2026-05-01", "label": "Visit"},  # 6th visit, should be truncated to top 5
        ]

        pdf_bytes = generate_medical_diagnosis_pdf(
            patient_info=patient_info,
            doctor_info=doctor_info,
            diagnosis_info=diagnosis_info,
            assessment_info=assessment_info,
            past_visits=past_visits,
        )

        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 1000)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
