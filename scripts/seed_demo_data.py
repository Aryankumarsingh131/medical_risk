"""
scripts/seed_demo_data.py
-------------------------
Idempotent database seeding script for Medical Risk & XAI platform.

Creates:
|- 1 Admin account (admin@hospital.com / Demo@123)
|- 5 Doctor accounts with specializations (Demo@123)
|- Patient accounts sampled from raw datasets (Demo@123)
|- PatientRecords with real clinical data from raw datasets
|- ML predictions using the trained model on real patient data
|- AuditLog entries for complete system history

Usage:
    python scripts/seed_demo_data.py
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from api.database import (
    AuditLog,
    BloodTestResult,
    DoctorDiagnosis,
    Hospital,
    HospitalDoctorAvailability,
    PatientAssessment,
    PatientRecord,
    SessionLocal,
    User,
    create_tables,
)
from api.main import get_password_hash
from src.explain import explain_prediction
from src.schema_mapping import load_and_standardize, DATASET_CONFIGS, RAW_DIR

DEMO_PASSWORD = "Demo@123"
NUM_SAMPLE_PATIENTS = 10  # Number of patients to sample from raw datasets

# ---------------------------------------------------------------------------
# Seed Data Definitions
# ---------------------------------------------------------------------------

ADMIN_USER = {
    "name": "Admin",
    "email": "admin@hospital.com",
    "role": "admin",
    "password": DEMO_PASSWORD,
}

DOCTORS_DATA = [
    {
        "name": "Dr. Sharma",
        "email": "dr.sharma@hospital.com",
        "role": "doctor",
        "specialization": "Cardiology",
        "license_number": "DOC-IN-101",
        "degree": "MBBS, MD (Cardiology), FACC",
        "years_of_experience": 14,
        "certifications": "Board Certified Cardiologist, ACLS Certified, Fellow of the American College of Cardiology",
        "password": DEMO_PASSWORD,
    },
    {
        "name": "Dr. Mehta",
        "email": "dr.mehta@hospital.com",
        "role": "doctor",
        "specialization": "Internal Medicine",
        "license_number": "DOC-IN-102",
        "degree": "MBBS, MD (General Medicine)",
        "years_of_experience": 11,
        "certifications": "Board Certified Internal Physician, Advanced Diabetes Specialist",
        "password": DEMO_PASSWORD,
    },
    {
        "name": "Dr. Khan",
        "email": "dr.khan@hospital.com",
        "role": "doctor",
        "specialization": "Endocrinology",
        "license_number": "DOC-IN-103",
        "degree": "MBBS, MD, DM (Endocrinology)",
        "years_of_experience": 9,
        "certifications": "Endocrine Society Fellow, Certified Thyroid & Metabolic Specialist",
        "password": DEMO_PASSWORD,
    },
    {
        "name": "Dr. Rao",
        "email": "dr.rao@hospital.com",
        "role": "doctor",
        "specialization": "Pulmonology",
        "license_number": "DOC-IN-104",
        "degree": "MBBS, DNB (Respiratory Medicine)",
        "years_of_experience": 12,
        "certifications": "FCCCP, Critical Care Pulmonologist",
        "password": DEMO_PASSWORD,
    },
    {
        "name": "Dr. Iyer",
        "email": "dr.iyer@hospital.com",
        "role": "doctor",
        "specialization": "Nephrology",
        "license_number": "DOC-IN-105",
        "degree": "MBBS, MD, DM (Nephrology)",
        "years_of_experience": 15,
        "certifications": "Renal Transplant Specialist, Dialysis Director Certification",
        "password": DEMO_PASSWORD,
    },
]

HOSPITALS_DATA = [
    {
        "name": "City Care Super Specialty Hospital",
        "address": "123 Healthcare Ave, Medical District, Mumbai",
        "contact_number": "+91 98765 00100",
        "latitude": 19.0760,
        "longitude": 72.8777,
        "available_beds": 42,
        "icu_beds_available": 12,
        "ventilators_available": 6,
        "blood_bank_available": True,
        "emergency_services_available": True,
        "doctors": [
            {"specialization": "Cardiology", "available_doctors": 4},
            {"specialization": "Internal Medicine", "available_doctors": 6},
            {"specialization": "Pulmonology", "available_doctors": 2},
        ],
    },
    {
        "name": "Apollo Heart & Emergency Institute",
        "address": "45 Park Road, South City, Mumbai",
        "contact_number": "+91 98765 00200",
        "latitude": 19.1200,
        "longitude": 72.8500,
        "available_beds": 18,
        "icu_beds_available": 8,
        "ventilators_available": 4,
        "blood_bank_available": True,
        "emergency_services_available": True,
        "doctors": [
            {"specialization": "Cardiology", "available_doctors": 5},
            {"specialization": "Endocrinology", "available_doctors": 3},
        ],
    },
    {
        "name": "Metro Critical Care Hospital",
        "address": "88 Station Road, North District, Mumbai",
        "contact_number": "+91 98765 00300",
        "latitude": 19.0100,
        "longitude": 72.8300,
        "available_beds": 15,
        "icu_beds_available": 3,
        "ventilators_available": 2,
        "blood_bank_available": False,
        "emergency_services_available": True,
        "doctors": [
            {"specialization": "Nephrology", "available_doctors": 2},
            {"specialization": "Internal Medicine", "available_doctors": 4},
        ],
    },
]

def sample_patients_from_raw_datasets(num_patients: int) -> list:
    """
    Sample patient data from raw datasets instead of using hardcoded values.
    This ensures the model trains on and uses real clinical data.
    """
    sampled_patients = []
    patient_counter = 1
    
    # Load and combine data from all available raw datasets
    all_data = []
    for dataset_name in DATASET_CONFIGS.keys():
        try:
            df = load_and_standardize(dataset_name, RAW_DIR)
            # Filter to rows with valid target values and basic clinical data
            valid_rows = df.dropna(subset=['target_risk', 'age'])
            if len(valid_rows) > 0:
                all_data.append(valid_rows)
                print(f"  [Loaded] {dataset_name}: {len(valid_rows)} valid rows")
        except Exception as e:
            print(f"  [Warning] Could not load {dataset_name}: {e}")
    
    if not all_data:
        print("  [Warning] No valid data found in raw datasets, using minimal fallback")
        return []
    
    combined_df = pd.concat(all_data, ignore_index=True)
    print(f"  [Combined] Total dataset: {len(combined_df)} rows from {len(all_data)} sources")
    
    # Sample random patients from the combined dataset
    sample_indices = random.sample(range(len(combined_df)), min(num_patients, len(combined_df)))
    
    names_pool = [
        "Arjun", "Riya", "Rohan", "Ananya", "Vikram", "Pooja", "Siddharth", 
        "Neha", "Aditya", "Kavya", "Raj", "Priya", "Amit", "Sneha", "Karan",
        "Meera", "Deepak", "Sunita", "Rajesh", "Shweta", "Arvind"
    ]
    
    for idx in sample_indices:
        row = combined_df.iloc[idx]
        patient_name = names_pool[(patient_counter - 1) % len(names_pool)]
        patient_email = f"patient.{patient_name.lower()}@hospital.com"
        
        # Extract clinical data from the raw dataset
        clinical_record = {
            "age": int(row['age']) if pd.notna(row['age']) else 45,
            "systolic_bp": float(row['resting_bp']) if pd.notna(row['resting_bp']) else 120,
            "diastolic_bp": 80.0,  # Default if not available
            "cholesterol": float(row['cholesterol']) if pd.notna(row['cholesterol']) else 200.0,
            "fasting_blood_sugar": float(row['fasting_blood_sugar']) if pd.notna(row['fasting_blood_sugar']) else 0.0,
            "max_heart_rate": float(row['max_heart_rate']) if pd.notna(row['max_heart_rate']) else 150.0,
            "bmi": float(row['bmi']) if pd.notna(row['bmi']) else 25.0,
            "smoking": float(row['smoking']) if pd.notna(row['smoking']) else 0.0,
            "family_history": "Not specified in dataset",
            "exercise_frequency": "Not specified in dataset",
            "diet_notes": "Not specified in dataset",
        }
        
        # Assign to doctors in round-robin fashion
        doctor_email = DOCTORS_DATA[(patient_counter - 1) % len(DOCTORS_DATA)]["email"]
        
        patient_data = {
            "name": patient_name,
            "email": patient_email,
            "role": "patient",
            "doctor_email": doctor_email,
            "phone_number": f"+91 98765 432{10 + patient_counter:02d}",
            "emergency_contact_name": f"Emergency Contact {patient_counter}",
            "emergency_contact_phone": f"+91 98765 432{20 + patient_counter:02d}",
            "address": f"Address {patient_counter}, Medical District",
            "password": DEMO_PASSWORD,
            "clinical_record": clinical_record,
        }
        
        sampled_patients.append(patient_data)
        patient_counter += 1
    
    return sampled_patients

PATIENTS_DATA = sample_patients_from_raw_datasets(NUM_SAMPLE_PATIENTS)


# ---------------------------------------------------------------------------
# Seed Logic
# ---------------------------------------------------------------------------

def seed_database():
    create_tables()
    db = SessionLocal()
    accounts_created = []

    try:
        print("\n" + "=" * 80)
        print("[SEEDING] MEDICAL RISK SYSTEM DEMO DATA")
        print("=" * 80)

        # 1. Admin User
        admin_email = ADMIN_USER["email"].strip().lower()
        admin = db.query(User).filter(User.email == admin_email).first()
        if not admin:
            admin = User(
                name=ADMIN_USER["name"],
                email=admin_email,
                hashed_password=get_password_hash(ADMIN_USER["password"]),
                role="admin",
                is_active=True,
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            print(f"  [+] Created Admin: {admin.name} ({admin.email})")
            accounts_created.append({
                "role": "admin",
                "name": admin.name,
                "email": admin.email,
                "password": ADMIN_USER["password"],
                "details": "Full System Administrator",
            })
        else:
            # Update password hash if needed
            admin.hashed_password = get_password_hash(ADMIN_USER["password"])
            db.commit()
            print(f"  [*] Admin already exists: {admin.name} ({admin.email})")
            accounts_created.append({
                "role": "admin",
                "name": admin.name,
                "email": admin.email,
                "password": ADMIN_USER["password"],
                "details": "Full System Administrator (Existing)",
            })

        # 2. Doctors
        doctor_lookup: dict[str, User] = {}
        for doc_def in DOCTORS_DATA:
            doc_email = doc_def["email"].strip().lower()
            doctor = db.query(User).filter(User.email == doc_email).first()
            if not doctor:
                doctor = User(
                    name=doc_def["name"],
                    email=doc_email,
                    hashed_password=get_password_hash(doc_def["password"]),
                    role="doctor",
                    specialization=doc_def["specialization"],
                    license_number=doc_def["license_number"],
                    degree=doc_def.get("degree"),
                    years_of_experience=doc_def.get("years_of_experience"),
                    certifications=doc_def.get("certifications"),
                    is_active=True,
                )
                db.add(doctor)
                db.commit()
                db.refresh(doctor)

                # AuditLog
                audit = AuditLog(
                    actor_user_id=admin.id,
                    actor_role="admin",
                    action="created_doctor",
                    target_type="User",
                    target_id=doctor.id,
                    details=json.dumps({
                        "name": doctor.name,
                        "email": doctor.email,
                        "specialization": doctor.specialization,
                    }),
                )
                db.add(audit)
                db.commit()
                print(f"  [+] Created Doctor: {doctor.name} ({doctor.email}) - {doctor.specialization}")
                accounts_created.append({
                    "role": "doctor",
                    "name": doctor.name,
                    "email": doctor.email,
                    "password": doc_def["password"],
                    "details": f"{doctor.specialization} ({doctor.license_number})",
                })
            else:
                doctor.hashed_password = get_password_hash(doc_def["password"])
                doctor.specialization = doc_def["specialization"]
                doctor.license_number = doc_def["license_number"]
                doctor.degree = doc_def.get("degree")
                doctor.years_of_experience = doc_def.get("years_of_experience")
                doctor.certifications = doc_def.get("certifications")
                db.commit()
                print(f"  [*] Doctor already exists: {doctor.name} ({doctor.email})")
                accounts_created.append({
                    "role": "doctor",
                    "name": doctor.name,
                    "email": doctor.email,
                    "password": doc_def["password"],
                    "details": f"{doctor.specialization} (Existing)",
                })
            doctor_lookup[doc_email] = doctor

        # 2b. Emergency Hospitals
        for h_def in HOSPITALS_DATA:
            existing_h = db.query(Hospital).filter(Hospital.name == h_def["name"]).first()
            if not existing_h:
                h = Hospital(
                    name=h_def["name"],
                    address=h_def["address"],
                    contact_number=h_def["contact_number"],
                    latitude=h_def["latitude"],
                    longitude=h_def["longitude"],
                    available_beds=h_def["available_beds"],
                    icu_beds_available=h_def["icu_beds_available"],
                    ventilators_available=h_def["ventilators_available"],
                    blood_bank_available=h_def["blood_bank_available"],
                    emergency_services_available=h_def["emergency_services_available"],
                )
                db.add(h)
                db.commit()
                db.refresh(h)
                for doc_avail in h_def["doctors"]:
                    da = HospitalDoctorAvailability(
                        hospital_id=h.id,
                        specialization=doc_avail["specialization"],
                        available_doctors=doc_avail["available_doctors"],
                    )
                    db.add(da)
                db.commit()
                print(f"  [+] Created Hospital: {h.name} ({h.address})")

        # 3. Patients & Initial Clinical Assessments
        for pat_def in PATIENTS_DATA:
            pat_email = pat_def["email"].strip().lower()
            patient = db.query(User).filter(User.email == pat_email).first()
            assigned_doctor = doctor_lookup.get(pat_def["doctor_email"].strip().lower())
            doc_id = assigned_doctor.id if assigned_doctor else None
            doc_name = assigned_doctor.name if assigned_doctor else "None"

            clin = pat_def["clinical_record"]
            pat_sex = 0.0 if pat_def["name"] in ["Riya", "Ananya", "Pooja", "Neha", "Kavya"] else 1.0

            if not patient:
                patient = User(
                    name=pat_def["name"],
                    email=pat_email,
                    hashed_password=get_password_hash(pat_def["password"]),
                    role="patient",
                    doctor_id=doc_id,
                    age=clin["age"],
                    sex=pat_sex,
                    is_demographics_locked=True,
                    phone_number=pat_def["phone_number"],
                    emergency_contact_name=pat_def["emergency_contact_name"],
                    emergency_contact_phone=pat_def["emergency_contact_phone"],
                    address=pat_def["address"],
                    is_active=True,
                )
                db.add(patient)
                db.commit()
                db.refresh(patient)

                # AuditLog
                audit = AuditLog(
                    actor_user_id=admin.id,
                    actor_role="admin",
                    action="created_patient",
                    target_type="User",
                    target_id=patient.id,
                    details=json.dumps({
                        "name": patient.name,
                        "email": patient.email,
                        "assigned_doctor": doc_name,
                        "age": clin["age"],
                        "sex": pat_sex,
                    }),
                )
                db.add(audit)
                db.commit()
                print(f"  [+] Created Patient: {patient.name} ({patient.email}) -> Assigned to {doc_name}")
                accounts_created.append({
                    "role": "patient",
                    "name": patient.name,
                    "email": patient.email,
                    "password": pat_def["password"],
                    "details": f"Assigned to {doc_name}",
                })
            else:
                patient.hashed_password = get_password_hash(pat_def["password"])
                patient.doctor_id = doc_id
                patient.age = clin["age"]
                patient.sex = pat_sex
                patient.is_demographics_locked = True
                patient.phone_number = pat_def["phone_number"]
                patient.emergency_contact_name = pat_def["emergency_contact_name"]
                patient.emergency_contact_phone = pat_def["emergency_contact_phone"]
                patient.address = pat_def["address"]
                db.commit()
                print(f"  [*] Patient already exists: {patient.name} ({patient.email})")
                accounts_created.append({
                    "role": "patient",
                    "name": patient.name,
                    "email": patient.email,
                    "password": pat_def["password"],
                    "details": f"Assigned to {doc_name} (Existing)",
                })

            # Check if PatientAssessment already exists for this patient
            existing_assessment = db.query(PatientAssessment).filter(PatientAssessment.patient_id == patient.id).first()
            if not existing_assessment:
                # Run ML XAI model
                patient_features = {
                    "age": clin["age"],
                    "sex": pat_sex,
                    "resting_bp": clin["systolic_bp"],
                    "cholesterol": clin["cholesterol"],
                    "fasting_blood_sugar": clin["fasting_blood_sugar"],
                    "max_heart_rate": clin["max_heart_rate"],
                    "bmi": clin["bmi"],
                    "smoking": clin["smoking"],
                }

                explanation = explain_prediction(patient_features)
                risk_prob = float(explanation["risk_score"])
                risk_label = str(explanation["risk_label"])

                top_3 = []
                for item in explanation["top_contributions"][:3]:
                    feat = item["feature"]
                    impact = item["impact"]
                    direction = item["direction"]
                    val = item["value"]
                    top_3.append(f"{feat} (value={val}): {impact.upper()}, {direction}")

                assessment = PatientAssessment(
                    patient_id=patient.id,
                    doctor_id=patient.doctor_id,
                    age=clin["age"],
                    sex=pat_sex,
                    systolic_bp=clin["systolic_bp"],
                    diastolic_bp=clin["diastolic_bp"],
                    cholesterol=clin["cholesterol"],
                    fasting_blood_sugar=clin["fasting_blood_sugar"],
                    max_heart_rate=clin["max_heart_rate"],
                    bmi=clin["bmi"],
                    smoking=clin["smoking"],
                    prior_medical_events=clin.get("prior_medical_events"),
                    risk_level=risk_label,
                    risk_probability=risk_prob,
                    triggered_rule_codes=json.dumps([item["feature"] for item in explanation["top_contributions"][:5]]),
                    clinical_recommendations=json.dumps(explanation.get("recommendations", [])),
                )
                db.add(assessment)
                db.commit()
                db.refresh(assessment)

                # AuditLog
                rec_audit = AuditLog(
                    actor_user_id=patient.doctor_id or admin.id,
                    actor_role="doctor" if patient.doctor_id else "admin",
                    action="added_record",
                    target_type="PatientAssessment",
                    target_id=assessment.id,
                    details=json.dumps({
                        "patient_name": patient.name,
                        "risk_level": risk_label,
                        "risk_probability": round(risk_prob, 4),
                        "systolic_bp": clin["systolic_bp"],
                        "diastolic_bp": clin["diastolic_bp"],
                    }),
                )
                db.add(rec_audit)
                db.commit()
                print(f"      -> Generated ML Prediction: {risk_label} ({risk_prob*100:.1f}%) | BP: {clin['systolic_bp']}/{clin['diastolic_bp']}")

            # Seed a sample DoctorDiagnosis if not exists
            existing_diag = db.query(DoctorDiagnosis).filter(DoctorDiagnosis.patient_id == patient.id).first()
            if not existing_diag and patient.doctor_id:
                diag_title = "Stage 1 Essential Hypertension with Moderate Atherogenic Risk" if clin["systolic_bp"] >= 135 else "Routine Preventative Cardiovascular Screening"
                diag_notes = f"Patient evaluated in clinic with resting BP {clin['systolic_bp']}/{clin['diastolic_bp']} mmHg and BMI {clin['bmi']}. Family history notes {clin['family_history']}. Recommended continuous monitoring."
                diag_plan = "Initiate dietary sodium restriction (<2g/day), aerobic exercise (30 mins daily), and follow-up clinical assessment in 6 weeks."
                diag_rx = "Amlodipine 5mg OD, Atorvastatin 10mg HS (if lipid profile indicates)" if clin["cholesterol"] > 200 else "Multivitamin daily, lifestyle modification"

                new_diag = DoctorDiagnosis(
                    patient_id=patient.id,
                    doctor_id=patient.doctor_id,
                    diagnosis_title=diag_title,
                    clinical_notes=diag_notes,
                    treatment_plan=diag_plan,
                    prescriptions=diag_rx,
                    risk_summary=f"Risk Score {assessment.risk_probability*100:.1f}% ({assessment.risk_level})",
                )
                db.add(new_diag)
                db.commit()

        # Seed sample transfer histories to showcase cross-doctor collaborative area
        if len(PATIENTS_DATA) >= 2:
            sample_transfers = [
                {"patient_name": PATIENTS_DATA[0]["name"], "from_doc": DOCTORS_DATA[0]["name"], "to_doc": DOCTORS_DATA[1]["name"], "reason": "Referred for comprehensive internal medicine evaluation"},
                {"patient_name": PATIENTS_DATA[1]["name"], "from_doc": DOCTORS_DATA[1]["name"], "to_doc": DOCTORS_DATA[2]["name"], "reason": "Endocrinology consultation for diabetic glycaemic control"},
            ]
            for st in sample_transfers:
                pat = db.query(User).filter(User.name == st["patient_name"], User.role == "patient").first()
                from_d = db.query(User).filter(User.name == st["from_doc"]).first()
                to_d = db.query(User).filter(User.name == st["to_doc"]).first()
                if pat and from_d and to_d:
                    existing_tx = db.query(AuditLog).filter(
                        AuditLog.target_id == pat.id,
                        AuditLog.action == "reassigned_patient",
                    ).first()
                    if not existing_tx:
                        tx_audit = AuditLog(
                            actor_user_id=from_d.id,
                            actor_role="doctor",
                            action="reassigned_patient",
                            target_type="User",
                            target_id=pat.id,
                            details=json.dumps({
                                "patient_id": pat.id,
                                "patient_name": pat.name,
                                "old_doctor_id": from_d.id,
                                "old_doctor_name": from_d.name,
                                "new_doctor_id": to_d.id,
                                "new_doctor_name": to_d.name,
                                "reason": st["reason"],
                            }),
                        )
                        db.add(tx_audit)
                        db.commit()

        # -------------------------------------------------------------------
        # Summary Table Output
        # -------------------------------------------------------------------
        print("\n" + "=" * 96)
        print("DEMO ACCOUNTS SUMMARY TABLE (Ready for frontend demo credentials)")
        print("=" * 96)
        print(f"{'Role':<10} | {'Name':<18} | {'Email':<32} | {'Password':<12} | {'Details'}")
        print("-" * 96)
        for acc in accounts_created:
            print(f"{acc['role']:<10} | {acc['name']:<18} | {acc['email']:<32} | {acc['password']:<12} | {acc['details']}")
        print("=" * 96 + "\n")

    except Exception as exc:
        db.rollback()
        print(f"[!] Error during database seeding: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
