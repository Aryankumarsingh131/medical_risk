"""
scripts/seed_demo_data.py
-------------------------
Idempotent database seeding script for Medical Risk & XAI platform.

Creates exactly 2 demo hospitals, each with its OWN:
  - hospital_admin (scoped to that hospital tenant)
  - doctors (scoped to that hospital)
  - patients sampled from raw datasets (scoped to that hospital)
Plus one platform Super Admin who sees only hospital counts and total
people numbers -- never names of doctors or patients.

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
    DoctorDiagnosis,
    Hospital,
    HospitalDoctorAvailability,
    PatientAssessment,
    SessionLocal,
    User,
    create_tables,
)
from api.main import get_password_hash
from src.explain import explain_prediction
from src.schema_mapping import load_and_standardize, DATASET_CONFIGS, RAW_DIR

DEMO_PASSWORD = "Demo@123"
NUM_DOCTORS_PER_HOSPITAL = 3
NUM_PATIENTS_PER_HOSPITAL = 5
NUM_SAMPLE_PATIENTS = NUM_PATIENTS_PER_HOSPITAL * 2  # total across both hospitals

# ---------------------------------------------------------------------------
# Seed Data Definitions
# ---------------------------------------------------------------------------

SUPER_ADMIN_USER = {
    "name": "Platform Super Admin",
    "email": "superadmin@medrisk.com",
    "role": "super_admin",
    "password": DEMO_PASSWORD,
}

# Shared doctor specs; each hospital gets its own copies with tenant-scoped emails.
DOCTOR_SPECS = [
    {
        "specialization": "Cardiology",
        "degree": "MBBS, MD (Cardiology), FACC",
        "years_of_experience": 14,
        "certifications": "Board Certified Cardiologist, ACLS Certified, FACC",
    },
    {
        "specialization": "Internal Medicine",
        "degree": "MBBS, MD (General Medicine)",
        "years_of_experience": 11,
        "certifications": "Board Certified Internal Physician, Advanced Diabetes Specialist",
    },
    {
        "specialization": "Endocrinology",
        "degree": "MBBS, MD, DM (Endocrinology)",
        "years_of_experience": 9,
        "certifications": "Endocrine Society Fellow, Certified Thyroid & Metabolic Specialist",
    },
]

PATIENT_NAMES_POOL = [
    "Arjun", "Riya", "Rohan", "Ananya", "Vikram",
    "Pooja", "Siddharth", "Neha", "Aditya", "Kavya",
    "Raj", "Priya", "Amit", "Sneha", "Karan",
]

HOSPITALS_DATA = [
    {
        "name": "City Care Super Specialty Hospital",
        "code": "CITY01",
        "address": "123 Healthcare Ave, Medical District, Mumbai",
        "contact_number": "+91 98765 00100",
        "latitude": 19.0760,
        "longitude": 72.8777,
        "available_beds": 42,
        "icu_beds_available": 12,
        "ventilators_available": 6,
        "blood_bank_available": True,
        "emergency_services_available": True,
        "admin_name": "City Care Admin",
        "doctor_names": ["Dr. Sharma", "Dr. Mehta", "Dr. Khan"],
        "patient_names": ["Arjun", "Riya", "Rohan", "Ananya", "Vikram"],
        "availability": [
            {"specialization": "Cardiology", "available_doctors": 4},
            {"specialization": "Internal Medicine", "available_doctors": 6},
            {"specialization": "Endocrinology", "available_doctors": 3},
        ],
    },
    {
        "name": "Apollo Heart & Emergency Institute",
        "code": "APOLO2",
        "address": "45 Park Road, South City, Mumbai",
        "contact_number": "+91 98765 00200",
        "latitude": 19.1200,
        "longitude": 72.8500,
        "available_beds": 18,
        "icu_beds_available": 8,
        "ventilators_available": 4,
        "blood_bank_available": True,
        "emergency_services_available": True,
        "admin_name": "Apollo Admin",
        "doctor_names": ["Dr. Rao", "Dr. Iyer", "Dr. Menon"],
        "patient_names": ["Pooja", "Siddharth", "Neha", "Aditya", "Kavya"],
        "availability": [
            {"specialization": "Cardiology", "available_doctors": 5},
            {"specialization": "Internal Medicine", "available_doctors": 4},
            {"specialization": "Endocrinology", "available_doctors": 2},
        ],
    },
]

FEMALE_NAMES = {"Riya", "Ananya", "Pooja", "Neha", "Kavya", "Priya", "Sneha", "Meera", "Sunita", "Shweta"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tenant_email(prefix: str, hospital_code: str) -> str:
    """Scoped email unique per hospital tenant."""
    prefix = prefix.lower().replace(" ", ".").replace("..", ".")
    return f"{prefix}.{hospital_code.lower()}@hospital.com"


def sample_patients_from_raw_datasets(num_patients: int) -> pd.DataFrame:
    """Load + standardize raw clinical data, return a sample of patient rows."""
    all_data = []
    for dataset_name in DATASET_CONFIGS.keys():
        try:
            df = load_and_standardize(dataset_name, RAW_DIR)
            valid_rows = df.dropna(subset=['target_risk', 'age'])
            if len(valid_rows) > 0:
                all_data.append(valid_rows)
                print(f"  [Loaded] {dataset_name}: {len(valid_rows)} valid rows")
        except Exception as e:
            print(f"  [Warning] Could not load {dataset_name}: {e}")

    if not all_data:
        print("  [Warning] No valid data found in raw datasets, using minimal fallback")
        return pd.DataFrame()

    combined_df = pd.concat(all_data, ignore_index=True)
    print(f"  [Combined] Total dataset: {len(combined_df)} rows from {len(all_data)} sources")

    n = min(num_patients, len(combined_df))
    sample_indices = random.sample(range(len(combined_df)), n)
    return combined_df.iloc[sample_indices].reset_index(drop=True)


def _patient_clinical_record(row) -> dict:
    return {
        "age": int(row['age']) if pd.notna(row['age']) else 45,
        "systolic_bp": float(row['resting_bp']) if pd.notna(row['resting_bp']) else 120,
        "diastolic_bp": 80.0,
        "cholesterol": float(row['cholesterol']) if pd.notna(row['cholesterol']) else 200.0,
        "fasting_blood_sugar": float(row['fasting_blood_sugar']) if pd.notna(row['fasting_blood_sugar']) else 0.0,
        "max_heart_rate": float(row['max_heart_rate']) if pd.notna(row['max_heart_rate']) else 150.0,
        "bmi": float(row['bmi']) if pd.notna(row['bmi']) else 25.0,
        "smoking": float(row['smoking']) if pd.notna(row['smoking']) else 0.0,
        "family_history": "Not specified in dataset",
        "exercise_frequency": "Not specified in dataset",
        "diet_notes": "Not specified in dataset",
    }


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

        # 1. Super Admin (platform owner, no hospital tenant)
        sa_email = SUPER_ADMIN_USER["email"].strip().lower()
        super_admin = db.query(User).filter(User.email == sa_email).first()
        if not super_admin:
            super_admin = User(
                name=SUPER_ADMIN_USER["name"],
                email=sa_email,
                hashed_password=get_password_hash(SUPER_ADMIN_USER["password"]),
                role="super_admin",
                is_active=True,
            )
            db.add(super_admin)
            db.commit()
            db.refresh(super_admin)
            print(f"  [+] Created Super Admin: {super_admin.name} ({super_admin.email})")
        else:
            super_admin.hashed_password = get_password_hash(SUPER_ADMIN_USER["password"])
            db.commit()
            print(f"  [*] Super Admin already exists: {super_admin.name} ({super_admin.email})")

        # 2. Create exactly 2 hospitals with their own admins, doctors, patients.
        for h_def in HOSPITALS_DATA:
            print(f"\n--- Seeding hospital tenant: {h_def['name']} ({h_def['code']}) ---")
            hospital = db.query(Hospital).filter(Hospital.hospital_code == h_def["code"]).first()
            if not hospital:
                hospital = Hospital(
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
                    hospital_code=h_def["code"],
                    is_active=True,
                    subscription_tier="standard",
                )
                db.add(hospital)
                db.commit()
                db.refresh(hospital)
                for doc_avail in h_def["availability"]:
                    db.add(HospitalDoctorAvailability(
                        hospital_id=hospital.id,
                        specialization=doc_avail["specialization"],
                        available_doctors=doc_avail["available_doctors"],
                    ))
                db.commit()
                print(f"  [+] Created Hospital: {hospital.name} (code '{hospital.hospital_code}')")
            else:
                print(f"  [*] Hospital already exists: {hospital.name} (code '{hospital.hospital_code}')")

            hid, hcode = hospital.id, hospital.hospital_code

            # 2a. This hospital's admin
            admin_email = _tenant_email("admin", hcode)
            admin = db.query(User).filter(User.email == admin_email).first()
            if not admin:
                admin = User(
                    name=h_def["admin_name"],
                    email=admin_email,
                    hashed_password=get_password_hash(DEMO_PASSWORD),
                    role="hospital_admin",
                    hospital_id=hid,
                    hospital_code=hcode,
                    is_active=True,
                )
                db.add(admin)
                db.commit()
                db.refresh(admin)
                print(f"  [+] Created Hospital Admin: {admin.name} ({admin.email})")
                accounts_created.append({"role": "hospital_admin", "name": admin.name,
                                         "email": admin.email, "password": DEMO_PASSWORD,
                                         "details": f"Admin of {hcode}"})
            else:
                admin.hashed_password = get_password_hash(DEMO_PASSWORD)
                admin.hospital_id = hid
                admin.hospital_code = hcode
                admin.role = "hospital_admin"
                db.commit()
                print(f"  [*] Hospital Admin already exists: {admin.name} ({admin.email})")
                accounts_created.append({"role": "hospital_admin", "name": admin.name,
                                         "email": admin.email, "password": DEMO_PASSWORD,
                                         "details": f"Admin of {hcode} (Existing)"})

            # 2b. This hospital's doctors
            doctor_lookup: dict[str, User] = {}
            for idx, doc_name in enumerate(h_def["doctor_names"]):
                spec = DOCTOR_SPECS[idx % len(DOCTOR_SPECS)]
                doc_email = _tenant_email(doc_name.lower().replace(" ", "."), hcode)
                license_no = f"DOC-{hcode}-{doc_name.split()[-1].upper()}"
                doctor = db.query(User).filter(User.email == doc_email).first()
                if not doctor:
                    doctor = User(
                        name=doc_name,
                        email=doc_email,
                        hashed_password=get_password_hash(DEMO_PASSWORD),
                        role="doctor",
                        hospital_id=hid,
                        hospital_code=hcode,
                        specialization=spec["specialization"],
                        license_number=license_no,
                        degree=spec["degree"],
                        years_of_experience=spec["years_of_experience"],
                        certifications=spec["certifications"],
                        is_active=True,
                    )
                    db.add(doctor)
                    db.commit()
                    db.refresh(doctor)
                    db.add(AuditLog(
                        hospital_id=hid, actor_user_id=admin.id, actor_role="hospital_admin",
                        action="created_doctor", target_type="User", target_id=doctor.id,
                        details=json.dumps({"name": doctor.name, "email": doctor.email,
                                            "specialization": doctor.specialization}),
                    ))
                    db.commit()
                    print(f"  [+] Created Doctor: {doctor.name} ({doctor.email}) - {doctor.specialization}")
                    accounts_created.append({"role": "doctor", "name": doctor.name,
                                             "email": doctor.email, "password": DEMO_PASSWORD,
                                             "details": doctor.specialization})
                else:
                    doctor.hashed_password = get_password_hash(DEMO_PASSWORD)
                    doctor.hospital_id = hid
                    doctor.hospital_code = hcode
                    doctor.specialization = spec["specialization"]
                    doctor.license_number = license_no
                    doctor.degree = spec["degree"]
                    doctor.years_of_experience = spec["years_of_experience"]
                    doctor.certifications = spec["certifications"]
                    db.commit()
                    print(f"  [*] Doctor already exists: {doctor.name} ({doctor.email})")
                    accounts_created.append({"role": "doctor", "name": doctor.name,
                                             "email": doctor.email, "password": DEMO_PASSWORD,
                                             "details": f"{doctor.specialization} (Existing)"})
                doctor_lookup[doc_name] = doctor

            # 2c. This hospital's patients (from raw dataset sample)
            pat_rows = sample_patients_from_raw_datasets(NUM_PATIENTS_PER_HOSPITAL)
            dr_names = list(doctor_lookup.keys())
            for i, pat_name in enumerate(h_def["patient_names"]):
                if len(pat_rows) == 0:
                    break
                row = pat_rows.iloc[i % len(pat_rows)]
                clin = _patient_clinical_record(row)
                pat_sex = 0.0 if pat_name in FEMALE_NAMES else 1.0
                pat_email = _tenant_email(f"patient.{pat_name.lower()}", hcode)
                assigned_doc = doctor_lookup[dr_names[i % len(dr_names)]]
                phone_suffix = f"{10 + (i + 1):02d}"

                patient = db.query(User).filter(User.email == pat_email).first()
                if not patient:
                    patient = User(
                        name=pat_name, email=pat_email,
                        hashed_password=get_password_hash(DEMO_PASSWORD),
                        role="patient", hospital_id=hid, hospital_code=hcode,
                        doctor_id=assigned_doc.id, age=clin["age"], sex=pat_sex,
                        is_demographics_locked=True,
                        phone_number=f"+91 98765 432{phone_suffix}",
                        emergency_contact_name=f"Emergency Contact {i + 1}",
                        emergency_contact_phone=f"+91 98765 43{i+20:02d}",
                        address=f"Address {i + 1}, {h_def['address'].split(',')[-1].strip()}",
                        is_active=True,
                    )
                    db.add(patient)
                    db.commit()
                    db.refresh(patient)
                    db.add(AuditLog(
                        hospital_id=hid, actor_user_id=admin.id, actor_role="hospital_admin",
                        action="created_patient", target_type="User", target_id=patient.id,
                        details=json.dumps({"name": patient.name, "email": patient.email,
                                            "assigned_doctor": assigned_doc.name, "age": clin["age"]}),
                    ))
                    db.commit()
                    print(f"  [+] Created Patient: {patient.name} ({patient.email}) -> {assigned_doc.name}")
                    accounts_created.append({"role": "patient", "name": patient.name,
                                             "email": patient.email, "password": DEMO_PASSWORD,
                                             "details": f"Assigned to {assigned_doc.name}"})
                else:
                    patient.hospital_id = hid
                    patient.hospital_code = hcode
                    patient.hashed_password = get_password_hash(DEMO_PASSWORD)
                    patient.doctor_id = assigned_doc.id
                    patient.age = clin["age"]
                    patient.sex = pat_sex
                    patient.is_demographics_locked = True
                    patient.phone_number = f"+91 98765 432{phone_suffix}"
                    db.commit()
                    print(f"  [*] Patient already exists: {patient.name} ({patient.email})")
                    accounts_created.append({"role": "patient", "name": patient.name,
                                             "email": patient.email, "password": DEMO_PASSWORD,
                                             "details": f"Assigned to {assigned_doc.name} (Existing)"})

                # ML assessment
                if not db.query(PatientAssessment).filter(PatientAssessment.patient_id == patient.id).first():
                    patient_features = {
                        "age": clin["age"], "sex": pat_sex, "resting_bp": clin["systolic_bp"],
                        "cholesterol": clin["cholesterol"], "fasting_blood_sugar": clin["fasting_blood_sugar"],
                        "max_heart_rate": clin["max_heart_rate"], "bmi": clin["bmi"],
                        "smoking": clin["smoking"],
                    }
                    explanation = explain_prediction(patient_features)
                    risk_prob = float(explanation["risk_score"])
                    risk_label = str(explanation["risk_label"])
                    assessment = PatientAssessment(
                        hospital_id=hid, patient_id=patient.id, doctor_id=patient.doctor_id,
                        age=clin["age"], sex=pat_sex, systolic_bp=clin["systolic_bp"],
                        diastolic_bp=clin["diastolic_bp"], cholesterol=clin["cholesterol"],
                        fasting_blood_sugar=clin["fasting_blood_sugar"],
                        max_heart_rate=clin["max_heart_rate"], bmi=clin["bmi"],
                        smoking=clin["smoking"], prior_medical_events=clin.get("prior_medical_events"),
                        risk_level=risk_label, risk_probability=risk_prob,
                        triggered_rule_codes=json.dumps([item["feature"] for item in explanation["top_contributions"][:5]]),
                        clinical_recommendations=json.dumps(explanation.get("recommendations", [])),
                    )
                    db.add(assessment)
                    db.commit()
                    db.add(AuditLog(
                        hospital_id=hid, actor_user_id=patient.doctor_id or admin.id,
                        actor_role="doctor" if patient.doctor_id else "hospital_admin",
                        action="added_record", target_type="PatientAssessment", target_id=assessment.id,
                        details=json.dumps({"patient_name": patient.name, "risk_level": risk_label,
                                            "risk_probability": round(risk_prob, 4)}),
                    ))
                    db.commit()
                    print(f"      -> Generated ML Prediction: {risk_label} ({risk_prob*100:.1f}%)")

                # Doctor diagnosis
                if patient.doctor_id and not db.query(DoctorDiagnosis).filter(DoctorDiagnosis.patient_id == patient.id).first():
                    diag_title = "Stage 1 Essential Hypertension with Moderate Atherogenic Risk" if clin["systolic_bp"] >= 135 else "Routine Preventative Cardiovascular Screening"
                    diag_notes = f"Patient evaluated in clinic with resting BP {clin['systolic_bp']}/{clin['diastolic_bp']} mmHg and BMI {clin['bmi']}."
                    diag_plan = "Initiate dietary sodium restriction (<2g/day), aerobic exercise (30 mins daily), and follow-up in 6 weeks."
                    diag_rx = "Amlodipine 5mg OD, Atorvastatin 10mg HS" if clin["cholesterol"] > 200 else "Multivitamin daily, lifestyle modification"
                    db.add(DoctorDiagnosis(
                        hospital_id=hid, patient_id=patient.id, doctor_id=patient.doctor_id,
                        diagnosis_title=diag_title, clinical_notes=diag_notes,
                        treatment_plan=diag_plan, prescriptions=diag_rx,
                        risk_summary=f"Risk Score {risk_prob*100:.1f}% ({risk_label})",
                    ))
                    db.commit()

        # -------------------------------------------------------------------
        # Summary Table Output
        # -------------------------------------------------------------------
        print("\n" + "=" * 96)
        print("DEMO ACCOUNTS SUMMARY TABLE (Ready for frontend demo credentials)")
        print("=" * 96)
        print(f"{'Role':<16} | {'Name':<24} | {'Email':<42} | {'Details'}")
        print("-" * 96)
        print(f"{'super_admin':<16} | {SUPER_ADMIN_USER['name']:<24} | {SUPER_ADMIN_USER['email']:<42} | Platform owner")
        for acc in accounts_created:
            print(f"{acc['role']:<16} | {acc['name']:<24} | {acc['email']:<42} | {acc['details']}")
        print("\n--- Hospital Tenants ---")
        for h in db.query(Hospital).order_by(Hospital.id.asc()).all():
            docs = db.query(User).filter(User.hospital_id == h.id, User.role == "doctor").count()
            pats = db.query(User).filter(User.hospital_id == h.id, User.role == "patient").count()
            print(f"  {h.name}: code '{h.hospital_code}' | {docs} doctors, {pats} patients")
        print("=" * 96 + "\n")

    except Exception as exc:
        db.rollback()
        print(f"[!] Error during database seeding: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()