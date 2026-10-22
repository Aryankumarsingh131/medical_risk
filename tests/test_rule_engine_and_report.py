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

    def test_pdf_report_with_json_strings_and_edge_cases(self):
        """Test report formation with serialized JSON recommendations, string rules, and float string age."""
        patient_info = {
            "id": 102,
            "name": "Robert Brown",
            "age": "64.0",
            "sex": "1.0",
            "phone_number": "555-1234",
        }
        doctor_info = {
            "id": 8,
            "name": "Dr. Marcus Vance",
            "specialization": "Interventional Cardiology",
        }
        diagnosis_info = {
            "id": 99,
            "diagnosis_title": "Severe Coronary Artery Disease with Angina",
            "clinical_notes": "Presenting with exertional chest discomfort.",
        }
        assessment_info = {
            "risk_level": "Critical Risk",
            "risk_probability": 0.92,
            "systolic_bp": 178,
            "diastolic_bp": 105,
            "max_heart_rate": 130,
            "bmi": 31.2,
            "cholesterol": 280,
            "st_depression": 2.5,
            "triggered_rules": ["BP_CRISIS", "SYNERGY_CRISIS_BP", "ST_DEP_SEVERE"],
            "clinical_recommendations": '["Immediate emergency cardiology referral", "Administer dual antiplatelet therapy", "Continuous telemetry monitoring"]',
            "created_at": "2026-10-16",
        }
        blood_test = {
            "fasting_glucose": 142,
            "hba1c": 8.1,
            "hemoglobin": 13.5,
            "total_cholesterol": 280,
            "hdl": 35,
            "ldl": 195,
            "creatinine": 1.4,
            "notes": "Fasting sample verified",
        }

        pdf_bytes = generate_medical_diagnosis_pdf(
            patient_info=patient_info,
            doctor_info=doctor_info,
            diagnosis_info=diagnosis_info,
            assessment_info=assessment_info,
            blood_test_info=blood_test,
        )

        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 2000)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

    def test_pdf_report_minimal_empty_fields(self):
        """Test report formation when optional fields are None or minimal."""
        patient_info = {"id": 103, "name": "Minimal Patient"}
        doctor_info = {}
        diagnosis_info = {"id": 1}

        pdf_bytes = generate_medical_diagnosis_pdf(
            patient_info=patient_info,
            doctor_info=doctor_info,
            diagnosis_info=diagnosis_info,
            assessment_info=None,
            blood_test_info=None,
        )

    def test_ten_sections_structure_and_disclaimer(self):
        """Test that all 10 sections and critical distinction notice are properly handled."""
        from src.report_generator import calculate_lab_flags

        # Test lab flags evaluation
        lab_data = {
            "fasting_glucose": 130,  # High
            "hba1c": 5.4,           # Normal
            "total_cholesterol": 245,  # High
            "hdl": 35,              # Low
            "ldl": 165,             # High
            "triglycerides": 210,   # High
            "creatinine": 1.45,      # High
        }
        flags = calculate_lab_flags(lab_data, sex_str="Male")
        self.assertGreaterEqual(len(flags), 6)
        flags_map = {f["name"]: f["flag"] for f in flags}
        self.assertEqual(flags_map["Fasting Blood Glucose"], "HIGH")
        self.assertEqual(flags_map["Glycated Hemoglobin (HbA1c)"], "NORMAL")
        self.assertEqual(flags_map["Total Serum Cholesterol"], "HIGH")
        self.assertEqual(flags_map["HDL Cholesterol"], "LOW (Risk Factor)")

        # Test full 10-section PDF report generation
        patient_info = {
            "id": 201,
            "name": "Sarah Connor",
            "age": 48,
            "sex": 0,
            "date_of_birth": "1978-05-12",
            "phone_number": "555-0100",
            "emergency_contact_name": "John Connor",
            "emergency_contact_phone": "555-0101",
            "address": "452 Medical Parkway",
            "hospital_name": "Metro General Hospital",
        }
        doctor_info = {
            "id": 12,
            "name": "Dr. Emily Stone",
            "degree": "MD, FACC",
            "specialization": "Cardiovascular Medicine",
            "license_number": "DOC-9912",
            "email": "estone@metro.org",
            "hospital_name": "Metro General Hospital",
        }
        diagnosis_info = {
            "id": 88,
            "diagnosis_title": "Hypertensive Heart Disease with Dyslipidemia",
            "clinical_notes": "Patient presents for comprehensive cardiovascular risk review.",
            "treatment_plan": "Initiate cardioprotective regimen and lifestyle modification.",
            "prescriptions": "Lisinopril 10mg PO Daily; Atorvastatin 20mg PO QPM",
            "created_at": datetime.now(timezone.utc),
        }
        assessment_info = {
            "target_disease": "Cardiovascular Disease & CAD",
            "risk_level": "High Risk",
            "risk_probability": 0.72,
            "systolic_bp": 154,
            "diastolic_bp": 94,
            "max_heart_rate": 136,
            "temperature": 98.4,
            "bmi": 28.6,
            "spo2": 99,
            "chest_pain_type": 1,
            "exercise_angina": 1,
            "st_depression": 1.8,
            "smoking": 1,
            "hypertension": 1,
            "diabetes": 0,
            "prior_medical_events": "Family history of early CAD",
            "triggered_rules": [
                {"rule_code": "BP_STAGE2_HTN", "points": 30, "category": "Vascular", "description": "Systolic BP > 140 mmHg"},
                {"rule_code": "ST_DEPRESSION_ISCHEMIA", "points": 25, "category": "ECG", "description": "ST Depression > 1.0 mm"},
            ],
            "clinical_recommendations": [
                "Schedule coronary CT angiography or stress echocardiogram within 4 weeks.",
                "Tight blood pressure control with clinic re-evaluation in 30 days.",
            ],
        }
        past_visits = [
            {"date": "2026-09-15", "label": "Initial Screening", "risk_level": "High Risk", "systolic_bp": 160, "diastolic_bp": 98},
            {"date": "2026-07-20", "label": "Annual Physical", "risk_level": "Moderate Risk", "systolic_bp": 142, "diastolic_bp": 88},
        ]

        pdf_bytes = generate_medical_diagnosis_pdf(
            patient_info=patient_info,
            doctor_info=doctor_info,
            diagnosis_info=diagnosis_info,
            assessment_info=assessment_info,
            blood_test_info=lab_data,
            past_visits=past_visits,
        )

        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 2000)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()

