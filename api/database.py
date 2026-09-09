"""
SQLAlchemy schema and ORM models for Role-Based Clinical Risk System.

Models
------
- User / PatientProfile : admin / doctor / patient (single table, discriminated by role)
- PatientAssessment / PatientRecord : ML-backed clinical risk record per patient visit
- BloodTestResult       : Standalone lab panel, stored independently of PatientRecord
- AuditLog              : Immutable record of every mutating action in the system
- PredictionLog         : Legacy low-level prediction log (kept for backward compat)
- Medicine              : Per-doctor medicine inventory (requested + procured)
- PatientRegistrationRequest : Self-registered patient awaiting doctor assignment
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    text,
)
from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./medical_risk.db")

def init_engine():
    global DATABASE_URL
    if DATABASE_URL.startswith("postgresql"):
        try:
            test_engine = create_engine(
                DATABASE_URL,
                pool_pre_ping=True,
                connect_args={"connect_timeout": 5},
                echo=False,
            )
            with test_engine.connect() as conn:
                pass
            return test_engine
        except Exception as exc:
            print(f"[!] Remote database connection failed ({exc}). Falling back to local persistent SQLite.")
            DATABASE_URL = "sqlite:///./medical_risk.db"

    return create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
        echo=False,
        pool_pre_ping=True,
    )

engine = init_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()



# ---------------------------------------------------------------------------
# User / PatientProfile (admin / doctor / patient)
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=True)
    email = Column(String(120), unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String(20), default="patient")   # super_admin | hospital_admin | doctor | patient
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Hospital (tenant) - required for all users except super_admin
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=True, index=True)
    hospital_code = Column(String(10), nullable=True, index=True)  # Duplicate for easy lookup

    # Doctor-specific
    specialization = Column(String(100), nullable=True)
    license_number = Column(String(50), nullable=True)
    degree = Column(String(150), nullable=True)
    years_of_experience = Column(Integer, nullable=True)
    certifications = Column(Text, nullable=True)

    # Patient-specific demographics & contact
    # doctor_id is the assigned doctor FK; use reassign_doctor() / transfer_doctor() for transfers.
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    date_of_birth = Column(String(20), nullable=True)
    age = Column(Float, nullable=True)
    sex = Column(Float, nullable=True)             # 1 = Male, 0 = Female
    is_demographics_locked = Column(Boolean, default=False)
    phone_number = Column(String(30), nullable=True)
    emergency_contact_name = Column(String(100), nullable=True)
    emergency_contact_phone = Column(String(30), nullable=True)
    address = Column(String(255), nullable=True)
    # Patient pending assignment (self-registered but not yet assigned to a doctor)
    pending_assignment = Column(Boolean, default=False)

    # Relationships
    hospital = relationship("Hospital", back_populates="users", foreign_keys=[hospital_id])
    doctor = relationship("User", remote_side=[id], backref="assigned_patients")
    assessments = relationship(
        "PatientAssessment",
        back_populates="patient",
        foreign_keys="PatientAssessment.patient_id",
    )
    blood_tests = relationship(
        "BloodTestResult",
        back_populates="patient",
        foreign_keys="BloodTestResult.patient_id",
    )
    diagnoses = relationship(
        "DoctorDiagnosis",
        back_populates="patient",
        foreign_keys="DoctorDiagnosis.patient_id",
    )

    def reassign_doctor(self, new_doctor_id: Optional[int]) -> None:
        """Change the patient's assigned doctor. Persist via the ORM session."""
        self.doctor_id = new_doctor_id
        self.pending_assignment = False

    def transfer_doctor(self, new_doctor_id: Optional[int]) -> None:
        """Alias helper method for doctor transfers."""
        self.reassign_doctor(new_doctor_id)


# Alias for PatientProfile
PatientProfile = User


# ---------------------------------------------------------------------------
# Hospital
# ---------------------------------------------------------------------------

class Hospital(Base):
    __tablename__ = "hospitals"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    hospital_code = Column(String(10), unique=True, index=True, nullable=True)  # Unique tenant code (nullable for legacy rows)
    address = Column(String(255), nullable=False)
    contact_number = Column(String(30), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    available_beds = Column(Integer, default=0)
    icu_beds_available = Column(Integer, default=0)
    ventilators_available = Column(Integer, default=0)
    blood_bank_available = Column(Boolean, default=False)
    emergency_services_available = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)  # Enable/disable hospital tenant
    subscription_tier = Column(String(50), default="standard")  # For future SaaS pricing
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    doctors = relationship("HospitalDoctorAvailability", back_populates="hospital", cascade="all, delete-orphan")
    users = relationship("User", back_populates="hospital", foreign_keys="User.hospital_id")


class HospitalDoctorAvailability(Base):
    __tablename__ = "hospital_doctor_availability"

    id = Column(Integer, primary_key=True, index=True)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=False, index=True)
    specialization = Column(String(100), nullable=False)
    available_doctors = Column(Integer, default=0)

    hospital = relationship("Hospital", back_populates="doctors")


# ---------------------------------------------------------------------------
# DoctorDiagnosis (Physician clinical diagnosis, notes & treatment plan)
# ---------------------------------------------------------------------------

class DoctorDiagnosis(Base):
    __tablename__ = "doctor_diagnoses"

    id = Column(Integer, primary_key=True, index=True)

    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=False, index=True)

    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    diagnosis_title = Column(String(200), nullable=False)
    clinical_notes = Column(Text, nullable=False)
    treatment_plan = Column(Text, nullable=True)
    prescriptions = Column(Text, nullable=True)
    risk_summary = Column(String(150), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient = relationship("User", foreign_keys=[patient_id], back_populates="diagnoses")
    doctor = relationship("User", foreign_keys=[doctor_id])


# ---------------------------------------------------------------------------
# ClinicalDraft (Saved unassigned / guest patient drafts for doctors)
# ---------------------------------------------------------------------------

class ClinicalDraft(Base):
    __tablename__ = "clinical_drafts"

    id = Column(Integer, primary_key=True, index=True)

    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=False, index=True)

    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    draft_name = Column(String(100), default="Guest Patient Draft")
    guest_identifier = Column(String(100), nullable=True)
    raw_data_json = Column(Text, nullable=False)
    risk_level = Column(String(30), nullable=True)
    risk_probability = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    doctor = relationship("User", foreign_keys=[doctor_id])


# ---------------------------------------------------------------------------
# PatientAssessment / PatientRecord (ML risk record -- one per clinical visit)
# ---------------------------------------------------------------------------

class PatientAssessment(Base):
    __tablename__ = "patient_assessments"

    id = Column(Integer, primary_key=True, index=True)

    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=False, index=True)

    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Essential Patient Identifiers
    age = Column(Float, nullable=True)
    sex = Column(Float, nullable=True)              # 1 = Male, 0 = Female

    # Essential Input Vitals Used for Scoring
    systolic_bp = Column(Integer, nullable=True)    # mmHg (systolic blood pressure)
    diastolic_bp = Column(Integer, nullable=True)   # mmHg (diastolic blood pressure)
    max_heart_rate = Column(Float, nullable=True)
    bmi = Column(Float, nullable=True)

    # Essential Labs/Metabolic Used for Scoring
    cholesterol = Column(Float, nullable=True)
    fasting_blood_sugar = Column(Float, nullable=True)  # 1 if >120 mg/dL else 0
    st_depression = Column(Float, nullable=True)        # ST depression (ECG) in mm

    # Essential Clinical Signs Used for Scoring
    chest_pain_type = Column(Float, nullable=True)      # 0=typical, 1=atypical, 2=non-anginal, 3=asymptomatic
    exercise_angina = Column(Float, nullable=True)      # 1=yes, 0=no
    hypertension = Column(Float, nullable=True)         # 1=yes, 0=no
    diabetes = Column(Float, nullable=True)             # 1=yes, 0=no

    # Essential Additional Risk Factors
    smoking = Column(Float, nullable=True)
    prior_medical_events = Column(String(255), nullable=True)  # Prior cardiac events for context

    # Essential Risk Output
    risk_level = Column(String(30), nullable=False)
    risk_probability = Column(Float, nullable=False)
    triggered_rule_codes = Column(Text, nullable=True)  # JSON array of triggered rule codes
    clinical_recommendations = Column(Text, nullable=True)  # JSON array of recommendations

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship(
        "User", foreign_keys=[patient_id], back_populates="assessments"
    )


# Alias for PatientRecord
PatientRecord = PatientAssessment


# ---------------------------------------------------------------------------
# BloodTestResult (standalone lab panel -- stored independently of PatientRecord)
# ---------------------------------------------------------------------------

class BloodTestResult(Base):
    __tablename__ = "blood_test_results"

    id = Column(Integer, primary_key=True, index=True)

    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=False, index=True)

    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    recorded_by_doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Complete Blood Count (CBC)
    hemoglobin = Column(Float, nullable=True)       # g/dL
    wbc_count = Column(Float, nullable=True)        # 10^3/uL
    platelet_count = Column(Float, nullable=True)   # 10^3/uL

    # Metabolic panel
    fasting_glucose = Column(Float, nullable=True)  # mg/dL
    hba1c = Column(Float, nullable=True)            # %
    total_cholesterol = Column(Float, nullable=True)# mg/dL
    hdl = Column(Float, nullable=True)              # mg/dL
    ldl = Column(Float, nullable=True)              # mg/dL
    triglycerides = Column(Float, nullable=True)    # mg/dL

    # Renal
    creatinine = Column(Float, nullable=True)       # mg/dL

    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship(
        "User", foreign_keys=[patient_id], back_populates="blood_tests"
    )
    recorded_by = relationship("User", foreign_keys=[recorded_by_doctor_id])


# ---------------------------------------------------------------------------
# AuditLog (immutable record of every mutating action in the system)
# ---------------------------------------------------------------------------

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=True, index=True)

    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    actor_role = Column(String(20), nullable=False)   # super_admin | hospital_admin | doctor | patient

    # Action slug e.g. 'created_patient', 'created_doctor', 'reassigned_patient',
    # 'added_record', 'added_blood_test'
    action = Column(String(60), nullable=False, index=True)

    target_type = Column(String(50), nullable=True)   # 'User', 'PatientRecord', 'BloodTestResult', ...
    target_id = Column(Integer, nullable=True)

    # JSON blob with additional context (stored as TEXT in SQLite)
    details = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    actor = relationship("User", foreign_keys=[actor_user_id])


# ---------------------------------------------------------------------------
# PredictionLog (legacy -- kept for backward compat with old /predict route)
# ---------------------------------------------------------------------------

class PredictionLog(Base):
    __tablename__ = "prediction_logs"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(String(100), index=True, nullable=True)
    risk_score = Column(Float, nullable=False)
    risk_label = Column(String(20), nullable=False)
    model_version = Column(String(50), nullable=False)
    predicted_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# Medicine (Per-doctor inventory: requested + procured by admin)
# ---------------------------------------------------------------------------

class Medicine(Base):
    __tablename__ = "medicines"

    id = Column(Integer, primary_key=True, index=True)

    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=False, index=True)

    name = Column(String(150), nullable=False)
    generic_name = Column(String(150), nullable=True)
    category = Column(String(100), nullable=True)          # e.g. Antihypertensive, Anticoagulant
    unit = Column(String(30), nullable=True)               # e.g. tablet, vial, mg
    quantity = Column(Integer, default=0)

    # Doctor who requested this medicine
    requested_by_doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    # Doctor whose inventory it belongs to once procured
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    status = Column(String(30), default="requested")       # requested | procured
    notes = Column(Text, nullable=True)

    requested_at = Column(DateTime, default=datetime.utcnow)
    procured_at = Column(DateTime, nullable=True)

    requested_by = relationship("User", foreign_keys=[requested_by_doctor_id])
    doctor = relationship("User", foreign_keys=[doctor_id])


# ---------------------------------------------------------------------------
# PatientRegistrationRequest (Self-registered patients awaiting assignment)
# ---------------------------------------------------------------------------

class PatientRegistrationRequest(Base):
    __tablename__ = "patient_registration_requests"

    id = Column(Integer, primary_key=True, index=True)

    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=False, index=True)

    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    preferred_doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    department_preference = Column(String(100), nullable=True)  # e.g. Cardiology, General
    status = Column(String(20), default="pending")              # pending | accepted | forwarded
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient = relationship("User", foreign_keys=[patient_id])
    preferred_doctor = relationship("User", foreign_keys=[preferred_doctor_id])


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def transfer_patient_doctor(
    db: Session,
    patient_id: int,
    new_doctor_id: Optional[int],
    actor_user_id: Optional[int] = None,
    actor_role: str = "admin",
) -> User:
    """
    Helper function to reassign a patient's doctor and record an AuditLog entry.
    """
    patient = db.query(User).filter(User.id == patient_id, User.role == "patient").first()
    if not patient:
        raise ValueError(f"Patient with ID {patient_id} not found.")

    old_doctor_id = patient.doctor_id
    patient.reassign_doctor(new_doctor_id)

    log_entry = AuditLog(
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        action="reassigned_patient",
        target_type="User",
        target_id=patient.id,
        details=json.dumps({"old_doctor_id": old_doctor_id, "new_doctor_id": new_doctor_id}),
    )
    db.add(log_entry)
    db.commit()
    db.refresh(patient)
    return patient


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)

    # SQLite-only: add missing columns for legacy databases that predate migrations.
    # Skipped on PostgreSQL — SQLAlchemy create_all() handles the full schema.
    if not DATABASE_URL.startswith("sqlite"):
        return

    with engine.connect() as conn:
        try:
            # Check hospitals table columns
            result_h = conn.execute(text("PRAGMA table_info(hospitals)"))
            hospital_cols = [row[1] for row in result_h.fetchall()]
            if "hospital_code" not in hospital_cols:
                conn.execute(text("ALTER TABLE hospitals ADD COLUMN hospital_code VARCHAR(10)"))
            if "is_active" not in hospital_cols:
                conn.execute(text("ALTER TABLE hospitals ADD COLUMN is_active BOOLEAN DEFAULT 1"))
            if "subscription_tier" not in hospital_cols:
                conn.execute(text("ALTER TABLE hospitals ADD COLUMN subscription_tier VARCHAR(50) DEFAULT 'standard'"))
            if "created_at" not in hospital_cols:
                conn.execute(text("ALTER TABLE hospitals ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP"))
            conn.commit()

            # Check users table columns
            result = conn.execute(text("PRAGMA table_info(users)"))
            cols = [row[1] for row in result.fetchall()]
            if "date_of_birth" not in cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN date_of_birth VARCHAR(20)"))
            if "pending_assignment" not in cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN pending_assignment BOOLEAN DEFAULT 0"))
            if "hospital_id" not in cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN hospital_id INTEGER"))
            if "hospital_code" not in cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN hospital_code VARCHAR(10)"))
            conn.commit()

            # Add hospital_id to all relevant tables
            tables_to_update = [
                "doctor_diagnoses",
                "patient_assessments",
                "blood_test_results",
                "clinical_drafts",
                "medicines",
                "patient_registration_requests",
                "audit_logs",
            ]
            for table in tables_to_update:
                try:
                    result_t = conn.execute(text(f"PRAGMA table_info({table})"))
                    t_cols = [row[1] for row in result_t.fetchall()]
                    if "hospital_id" not in t_cols:
                        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN hospital_id INTEGER"))
                except Exception:
                    pass
            conn.commit()
        except Exception:
            pass


def load_initial_data(db: Session) -> None:
    """
    Load initial hardcoded data for demo purposes.
    Ensures all platform demo accounts (Admin, Doctor, Patient, Super Admin)
    exist so the application works out of the box.
    """
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    # Check if we already have users to avoid duplication
    if db.query(User).first():
        return  # Data already loaded

    # 1. Hospitals
    h1 = Hospital(
        name="City Care Super Specialty Hospital",
        hospital_code="CITY01",
        address="123 Healthcare Ave, Medical District, Mumbai",
        contact_number="+91 98765 00100",
        latitude=19.076,
        longitude=72.8777,
        available_beds=42,
        icu_beds_available=12,
        ventilators_available=6,
        blood_bank_available=True,
        emergency_services_available=True,
        is_active=True,
        subscription_tier="enterprise",
    )
    db.add(h1)
    db.flush()

    h2 = Hospital(
        name="Apollo Heart & Emergency Institute",
        hospital_code="APOLLO",
        address="45 Park Road, South City, Mumbai",
        contact_number="+91 98765 00200",
        latitude=19.12,
        longitude=72.85,
        available_beds=18,
        icu_beds_available=8,
        ventilators_available=4,
        blood_bank_available=True,
        emergency_services_available=True,
        is_active=True,
        subscription_tier="enterprise",
    )
    db.add(h2)
    db.flush()

    demo_pw = pwd_context.hash("Demo@123")

    # 2. Standard Demo Accounts (Matching Login.jsx quick-login buttons)
    super_admin = User(
        name="Platform Super Admin",
        email="superadmin@medrisk.com",
        hashed_password=demo_pw,
        role="super_admin",
        is_active=True,
        hospital_id=h1.id,
        hospital_code=h1.hospital_code,
    )
    db.add(super_admin)

    h_admin = User(
        name="Hospital Admin (City Care)",
        email="admin@hospital.com",
        hashed_password=demo_pw,
        role="hospital_admin",
        is_active=True,
        hospital_id=h1.id,
        hospital_code=h1.hospital_code,
    )
    db.add(h_admin)

    doc_sharma = User(
        name="Dr. Priya Sharma",
        email="dr.sharma@hospital.com",
        hashed_password=demo_pw,
        role="doctor",
        specialization="Cardiology",
        license_number="MCI-2015-00123",
        degree="MBBS, MD (Cardiology), FACC",
        years_of_experience=14,
        certifications="Board Certified Cardiologist, ACLS Certified",
        is_active=True,
        hospital_id=h1.id,
        hospital_code=h1.hospital_code,
    )
    db.add(doc_sharma)
    db.flush()

    patient_arjun = User(
        name="Arjun Mehta",
        email="patient.arjun@hospital.com",
        hashed_password=demo_pw,
        role="patient",
        is_active=True,
        hospital_id=h1.id,
        hospital_code=h1.hospital_code,
        age=54.0,
        sex=1.0,
        is_demographics_locked=True,
        phone_number="+91 98765 43210",
        emergency_contact_name="Sunita Mehta",
        emergency_contact_phone="+91 98765 43211",
        address="Flat 4B, Sunflower Heights, Andheri West, Mumbai",
        doctor_id=doc_sharma.id,
    )
    db.add(patient_arjun)

    # 3. Simple demo aliases
    db.add(User(
        name="Super Admin",
        email="superadmin@demo.com",
        hashed_password=demo_pw,
        role="super_admin",
        is_active=True,
        hospital_id=h1.id,
        hospital_code=h1.hospital_code,
    ))
    db.add(User(
        name="Hospital Admin",
        email="hospitaladmin@demo.com",
        hashed_password=demo_pw,
        role="hospital_admin",
        is_active=True,
        hospital_id=h1.id,
        hospital_code=h1.hospital_code,
    ))
    db.add(User(
        name="Dr. Demo Doctor",
        email="doctor@demo.com",
        hashed_password=demo_pw,
        role="doctor",
        specialization="Cardiology",
        license_number="DOC12345",
        degree="MD",
        years_of_experience=10,
        certifications="Board Certified in Cardiology",
        is_active=True,
        hospital_id=h1.id,
        hospital_code=h1.hospital_code,
    ))
    db.add(User(
        name="Demo Patient",
        email="patient@demo.com",
        hashed_password=demo_pw,
        role="patient",
        is_active=True,
        hospital_id=h1.id,
        hospital_code=h1.hospital_code,
        age=45.0,
        sex=1.0,
        is_demographics_locked=True,
        phone_number="0987654321",
        emergency_contact_name="Emergency Contact",
        emergency_contact_phone="0987654320",
        address="456 Patient Ave, Demo City",
        doctor_id=doc_sharma.id,
    ))

    # Commit all the initial data
    db.commit()