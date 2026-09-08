"""
tests/test_api_and_ml.py
------------------------
Automated test suite verifying database models, authentication,
demographic locking, doctor transfer, shared collaborative area,
physician diagnoses, guest patient prediction, and clinical drafts.
"""

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.database import SessionLocal, User, PatientAssessment, DoctorDiagnosis, AuditLog, ClinicalDraft, Medicine, PatientRegistrationRequest, create_tables
from api.main import (
    LoginRequest,
    login_json,
    self_register_patient,
    get_all_active_doctors,
    get_doctor_patient_requests,
    accept_patient_request,
    forward_patient_request,
    request_medicine_procurement,
    get_doctor_medicines,
    get_admin_medicine_requests,
    procure_medicine,
    prescribe_patient_medicines,
    get_password_hash,
    verify_password,
    doctor_transfer_patient,
    record_patient_diagnosis,
    record_patient_assessment,
    preview_patient_assessment,
    evaluate_guest_patient,
    save_clinical_draft,
    get_clinical_drafts,
    delete_clinical_draft,
    convert_draft_to_patient,
    download_diagnosis_pdf,
    download_patient_latest_pdf,
)
from api.schemas import (
    DoctorTransferRequest,
    DoctorDiagnosisCreate,
    PatientRecordCreate,
    ClinicalDraftCreate,
    DraftConvertRequest,
    MedicineRequest,
    MedicineProcurePayload,
    PrescriptionCreate,
    PatientSelfRegister,
    ForwardPatientRequest,
)
from src.explain import explain_prediction
from src.clinical_advice import enrich_explanation


class TestMedicalRiskPlatform(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        create_tables()
        cls.db = SessionLocal()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_01_user_seeding_exists(self):
        admin = self.db.query(User).filter(User.email == "admin@hospital.com").first()
        self.assertIsNotNone(admin, "Admin user should exist in seeded database")
        self.assertEqual(admin.role, "admin")

        doctors = self.db.query(User).filter(User.role == "doctor").all()
        self.assertGreaterEqual(len(doctors), 5, "At least 5 doctors should be seeded")

        patients = self.db.query(User).filter(User.role == "patient").all()
        self.assertGreaterEqual(len(patients), 10, "At least 10 patients should be seeded")

    def test_02_password_hashing(self):
        plain = "Demo@123"
        hashed = get_password_hash(plain)
        self.assertTrue(verify_password(plain, hashed))
        self.assertFalse(verify_password("WrongPassword", hashed))

    def test_03_login_authentication(self):
        req = LoginRequest(email="dr.sharma@hospital.com", password="Demo@123")
        res = login_json(req, self.db)
        self.assertTrue(bool(res.access_token))
        self.assertEqual(res.role, "doctor")
        self.assertEqual(res.email, "dr.sharma@hospital.com")

    def test_04_ml_and_shap_inference(self):
        sample_input = {
            "age": 62.0,
            "sex": 1.0,
            "systolic_bp": 150,
            "diastolic_bp": 95,
            "cholesterol": 245.0,
            "fasting_blood_sugar": 1.0,
            "max_heart_rate": 130.0,
            "bmi": 31.2,
            "smoking": 1.0,
            "chest_pain_type": 0.0,
            "exercise_angina": 1.0,
            "st_depression": 2.0,
            "hypertension": 1.0,
            "diabetes": 1.0,
        }

        explanation = explain_prediction(sample_input)
        self.assertIn("risk_score", explanation)
        self.assertIn("risk_label", explanation)
        self.assertIn("top_contributions", explanation)
        self.assertGreater(len(explanation["top_contributions"]), 0)

        enriched = enrich_explanation(
            explanation=explanation,
            patient_data=sample_input,
        )
        self.assertIn("risk_category", enriched)
        self.assertIn("reasons", enriched)
        self.assertIn("recommendations", enriched)
        self.assertGreater(len(enriched["recommendations"]), 0)

    def test_05_demographic_locking(self):
        arjun = self.db.query(User).filter(User.email == "patient.arjun@hospital.com").first()
        self.assertIsNotNone(arjun)
        dr_sharma = self.db.query(User).filter(User.email == "dr.sharma@hospital.com").first()
        arjun.doctor_id = dr_sharma.id
        arjun.is_demographics_locked = True
        if arjun.age is None:
            arjun.age = 54.0
        if arjun.sex is None:
            arjun.sex = 1.0
        self.db.commit()
        self.db.refresh(arjun)

        initial_age = arjun.age
        initial_sex = arjun.sex

        req = PatientRecordCreate(
            age=99.0,
            sex=0.0,
            systolic_bp=130,
            diastolic_bp=85,
        )
        record_patient_assessment(arjun.id, req, self.db, dr_sharma)
        self.db.refresh(arjun)

        self.assertEqual(arjun.age, initial_age)
        self.assertEqual(arjun.sex, initial_sex)

    def test_06_doctor_transfer_patient(self):
        dr_sharma = self.db.query(User).filter(User.email == "dr.sharma@hospital.com").first()
        dr_mehta = self.db.query(User).filter(User.email == "dr.mehta@hospital.com").first()
        arjun = self.db.query(User).filter(User.email == "patient.arjun@hospital.com").first()
        arjun.doctor_id = dr_sharma.id
        self.db.commit()
        self.db.refresh(arjun)

        req = DoctorTransferRequest(
            new_doctor_id=dr_mehta.id,
            reason="Specialized cardiology to internal medicine referral",
        )
        res = doctor_transfer_patient(arjun.id, req, self.db, dr_sharma)
        self.assertEqual(res.status, "success")
        self.assertEqual(res.doctor_id, dr_mehta.id)

    def test_07_doctor_diagnosis_and_pdf(self):
        dr_mehta = self.db.query(User).filter(User.email == "dr.mehta@hospital.com").first()
        arjun = self.db.query(User).filter(User.email == "patient.arjun@hospital.com").first()

        diag_req = DoctorDiagnosisCreate(
            diagnosis_title="Atherosclerotic Vascular Evaluation",
            clinical_notes="Patient referred from Cardiology. Vitals stable under current statin regimen.",
            treatment_plan="Continue DASH dietary protocol, periodic blood panel in 3 months.",
            prescriptions="Atorvastatin 10mg HS, Aspirin 75mg OD",
            risk_summary="Moderate Risk (45.0%)",
        )
        diag_res = record_patient_diagnosis(arjun.id, diag_req, self.db, dr_mehta)
        self.assertIsNotNone(diag_res.id)
        self.assertEqual(diag_res.diagnosis_title, "Atherosclerotic Vascular Evaluation")

        pdf_response = download_diagnosis_pdf(diag_res.id, self.db, dr_mehta)
        self.assertEqual(pdf_response.media_type, "application/pdf")
        self.assertGreater(len(pdf_response.body), 1000)

    def test_08_guest_patient_immediate_prediction_and_drafts(self):
        dr_sharma = self.db.query(User).filter(User.email == "dr.sharma@hospital.com").first()

        # 1. Immediate Guest Prediction
        guest_payload = PatientRecordCreate(
            age=54.0,
            sex=1.0,
            systolic_bp=142,
            diastolic_bp=90,
            cholesterol=230.0,
            fasting_blood_sugar=1.0,
            max_heart_rate=135.0,
            bmi=29.0,
            smoking=1.0,
            chest_pain_type=0.0,
            exercise_angina=1.0,
            st_depression=1.5,
            hypertension=1.0,
            diabetes=1.0,
        )
        res = evaluate_guest_patient(guest_payload, "Walk-in Guest #101", self.db, dr_sharma)
        self.assertIsNotNone(res.risk_level)
        self.assertGreater(res.risk_probability, 0)
        self.assertGreater(len(res.reasons), 0)

        # 2. Save assessment as a Draft
        draft_payload = ClinicalDraftCreate(
            draft_name="Walk-in Guest #101",
            guest_identifier="Walk-in Guest #101",
            data={
                "guest_name": "Walk-in Guest #101",
                "age": 54.0,
                "sex": 1.0,
                "systolic_bp": 142,
                "diastolic_bp": 90,
                "cholesterol": 230.0,
                "fasting_blood_sugar": 1.0,
                "max_heart_rate": 135.0,
                "bmi": 29.0,
                "smoking": 1.0,
            },
            risk_level=res.risk_level,
            risk_probability=res.risk_probability,
        )
        draft = save_clinical_draft(draft_payload, self.db, dr_sharma)
        self.assertIsNotNone(draft.id)
        self.assertEqual(draft.draft_name, "Walk-in Guest #101")

        # 3. Retrieve doctor's drafts
        drafts_list = get_clinical_drafts(self.db, dr_sharma)
        self.assertTrue(any(d.id == draft.id for d in drafts_list))

        # 4. Convert draft into registered patient
        test_email = "priya.guest.registered@hospital.com"
        existing = self.db.query(User).filter(User.email == test_email).first()
        if existing:
            self.db.query(PatientAssessment).filter(PatientAssessment.patient_id == existing.id).delete()
            self.db.delete(existing)
            self.db.commit()

        convert_req = DraftConvertRequest(
            patient_name="Priya Guest Registered",
            patient_email=test_email,
            password="Demo@123",
            phone_number="+91 9988776655",
            emergency_contact_name="Ravi",
            emergency_contact_phone="+91 9988776654",
            address="Indiranagar, Bangalore",
        )
        convert_res = convert_draft_to_patient(draft.id, convert_req, self.db, dr_sharma)
        self.assertEqual(convert_res["status"], "success")
        new_patient_id = convert_res["patient_id"]

        # Verify new patient exists and has assessment
        converted_user = self.db.query(User).filter(User.id == new_patient_id).first()
        self.assertIsNotNone(converted_user)
        self.assertEqual(converted_user.name, "Priya Guest Registered")
        self.assertEqual(converted_user.age, 54.0)
        self.assertTrue(converted_user.is_demographics_locked)

    def test_09_patient_self_registration_and_queue(self):
        dr_sharma = self.db.query(User).filter(User.email == "dr.sharma@hospital.com").first()
        dr_mehta = self.db.query(User).filter(User.email == "dr.mehta@hospital.com").first()

        # 1. Clean up if test email exists
        test_email = "selfreg.patient@hospital.com"
        old = self.db.query(User).filter(User.email == test_email).first()
        if old:
            self.db.query(PatientRegistrationRequest).filter(PatientRegistrationRequest.patient_id == old.id).delete()
            self.db.delete(old)
            self.db.commit()

        # 2. Self register
        reg_payload = PatientSelfRegister(
            name="New Walkin Patient",
            email=test_email,
            password="Demo@123",
            preferred_doctor_id=dr_sharma.id,
            department_preference="Cardiology",
        )
        login_res = self_register_patient(reg_payload, self.db)
        self.assertEqual(login_res.role, "patient")
        self.assertEqual(login_res.name, "New Walkin Patient")

        # 3. Doctor checks request queue
        reqs = get_doctor_patient_requests(self.db, dr_sharma)
        found_req = next((r for r in reqs if r.patient_email == test_email), None)
        self.assertIsNotNone(found_req)
        self.assertEqual(found_req.department_preference, "Cardiology")

        # 4. Doctor forwards request to Dr. Mehta
        fwd_res = forward_patient_request(
            found_req.id,
            ForwardPatientRequest(new_doctor_id=dr_mehta.id, notes="Needs Internal Medicine follow-up"),
            self.db,
            dr_sharma,
        )
        self.assertEqual(fwd_res["status"], "success")

        # 5. Dr. Mehta accepts request
        accept_res = accept_patient_request(found_req.id, self.db, dr_mehta)
        self.assertEqual(accept_res["status"], "success")

        # Verify patient is now in Dr. Mehta's assigned roster
        pat = self.db.query(User).filter(User.id == found_req.patient_id).first()
        self.assertEqual(pat.doctor_id, dr_mehta.id)
        self.assertFalse(pat.pending_assignment)

    def test_10_doctor_medicine_request_procurement_prescription(self):
        admin = self.db.query(User).filter(User.role == "admin").first()
        dr_sharma = self.db.query(User).filter(User.email == "dr.sharma@hospital.com").first()
        arjun = self.db.query(User).filter(User.email == "patient.arjun@hospital.com").first()

        # 1. Doctor requests medicine
        med_req = MedicineRequest(
            name="Metoprolol Succinate 50mg",
            generic_name="Metoprolol",
            category="Beta-Blocker / Antihypertensive",
            unit="tablet",
            quantity=100,
            notes="For hypertension and angina management",
        )
        req_res = request_medicine_procurement(med_req, self.db, dr_sharma)
        self.assertIsNotNone(req_res.id)
        self.assertEqual(req_res.status, "requested")

        # 2. Admin views pending requests
        admin_reqs = get_admin_medicine_requests(self.db, admin)
        self.assertTrue(any(m.id == req_res.id for m in admin_reqs))

        # 3. Admin procures the medicine
        procure_res = procure_medicine(req_res.id, MedicineProcurePayload(quantity=150), self.db, admin)
        self.assertEqual(procure_res.status, "procured")
        self.assertEqual(procure_res.quantity, 150)
        self.assertEqual(procure_res.doctor_id, dr_sharma.id)

        # 4. Doctor checks their medicine inventory
        doc_meds = get_doctor_medicines(self.db, dr_sharma)
        available = [m for m in doc_meds if m.status == "procured"]
        self.assertTrue(any(m.id == req_res.id for m in available))

        # 5. Doctor prescribes the medicine to patient
        arjun.doctor_id = dr_sharma.id
        self.db.commit()
        self.db.refresh(arjun)

        rx_res = prescribe_patient_medicines(
            arjun.id,
            PrescriptionCreate(
                medicine_ids=[req_res.id],
                instructions="1 tablet daily after breakfast",
            ),
            self.db,
            dr_sharma,
        )
        self.assertEqual(rx_res["status"], "success")
        self.assertIn("Metoprolol Succinate 50mg", rx_res["prescription_text"])

    def test_11_two_step_assessment_preview_and_approval(self):
        arjun = self.db.query(User).filter(User.email == "patient.arjun@hospital.com").first()
        doc = arjun.doctor or self.db.query(User).filter(User.id == arjun.doctor_id).first()

        assessment_payload = PatientRecordCreate(
            age=48.0,
            sex=1.0,
            systolic_bp=138,
            diastolic_bp=88,
            cholesterol=215.0,
            fasting_blood_sugar=0.0,
            max_heart_rate=142.0,
            bmi=26.8,
            smoking=0.0,
            chest_pain_type=2.0,
            exercise_angina=0.0,
            st_depression=0.5,
            hypertension=1.0,
            diabetes=0.0,
        )

        # Count assessments before preview
        count_before = self.db.query(PatientAssessment).filter(PatientAssessment.patient_id == arjun.id).count()

        # Step 1: Doctor runs preview assessment
        preview_res = preview_patient_assessment(arjun.id, assessment_payload, self.db, doc)
        self.assertIsNotNone(preview_res.risk_level)
        self.assertGreater(preview_res.risk_percentage, 0)
        self.assertIsNotNone(preview_res.auto_diagnosis_suggestion)
        self.assertGreater(len(preview_res.reasons), 0)

        # Confirm nothing was committed to DB during preview
        count_after_preview = self.db.query(PatientAssessment).filter(PatientAssessment.patient_id == arjun.id).count()
        self.assertEqual(count_before, count_after_preview)

        # Step 2: Doctor approves assessment
        approved_res = record_patient_assessment(arjun.id, assessment_payload, self.db, doc)
        self.assertEqual(approved_res.risk_level, preview_res.risk_level)

        # Confirm assessment is now committed to DB
        count_after_approval = self.db.query(PatientAssessment).filter(PatientAssessment.patient_id == arjun.id).count()
        self.assertEqual(count_after_approval, count_before + 1)


if __name__ == "__main__":
    unittest.main()
