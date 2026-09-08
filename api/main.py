"""
api/main.py
-----------
Role-based Medical Risk & XAI Backend API.
"""

from __future__ import annotations

import json
import os
import secrets
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.database import (
    AuditLog,
    BloodTestResult,
    ClinicalDraft,
    DoctorDiagnosis,
    Hospital,
    HospitalDoctorAvailability,
    Medicine,
    PatientAssessment,
    PatientRegistrationRequest,
    PredictionLog,
    User,
    create_tables,
    get_db,
)
from api.schemas import (
    AssessmentResult,
    BloodTestResultCreate,
    BloodTestResultOut,
    ClinicalDraftCreate,
    ClinicalDraftOut,
    DoctorCreate,
    DoctorDiagnosisCreate,
    DoctorDiagnosisOut,
    DoctorPatientCreate,
    DoctorProfileUpdate,
    DoctorTransferRequest,
    DoctorTransferResponse,
    DraftConvertRequest,
    ForwardPatientRequest,
    HospitalCreate,
    HospitalDoctorAvailabilityCreate,
    HospitalDoctorAvailabilityOut,
    HospitalLoginPayload,
    HospitalOut,
    HospitalRegisterPayload,
    HospitalUpdate,
    MedicineProcurePayload,
    MedicineOut,
    MedicineRequest,
    PatientCreate,
    PatientProfileUpdate,
    PatientRecordCreate,
    PatientRegistrationRequestOut,
    PatientSelfRegister,
    PrescriptionCreate,
    PredictionRequest,
    PredictionResponse,
    RiskCategory,
    RiskReason,
    SHAPContribution,
    SuperAdminLoginPayload,
    UserOut,
)
from src.explain import explain_prediction
from src.clinical_advice import enrich_explanation
from src.rule_based_risk import calculate_rule_based_risk
from src.report_generator import generate_medical_diagnosis_pdf
from src.geometry import haversine_distance
from api.security import SecurityHeadersMiddleware

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY environment variable must be set. "
        "Generate with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
    )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)


# ---------------------------------------------------------------------------
# Auth Schemas
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    email: str
    password: str
    # MULTI-TENANT: Scopes the session to a hospital. If provided it must match
    # the user's hospital_code. If omitted, we still scope server-side via
    # hospital_id (from the token) and restrict non-super-admins to their tenant.
    hospital_code: Optional[str] = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    name: str
    email: str
    id: int
    hospital_id: Optional[int] = None
    hospital_code: Optional[str] = None


# Backward compatibility alias
PatientRecordInput = PatientRecordCreate


# ---------------------------------------------------------------------------
# Clinical Diagnosis & Auto-Suggestion Helper
# ---------------------------------------------------------------------------

def generate_auto_diagnosis_title(risk_level: str, features: dict, reasons: list) -> str:
    """Generates an intelligent, clinically relevant diagnostic headline based on risk level and clinical markers."""
    systolic = features.get("systolic_bp") or features.get("resting_bp") or 120
    diastolic = features.get("diastolic_bp") or 80
    chol = features.get("cholesterol") or 0
    cp = features.get("chest_pain_type")
    ex_ang = features.get("exercise_angina")
    st_dep = features.get("st_depression") or 0.0
    dm = features.get("diabetes")
    htn = features.get("hypertension") or (systolic >= 140 or diastolic >= 90)

    tags = []
    if cp in [0, 1] or ex_ang == 1:
        tags.append("Suspected Angina Pectoris / Ischemic Heart Presentation")
    if htn or systolic >= 140 or diastolic >= 90:
        tags.append("Essential Hypertension")
    if dm == 1 or features.get("fasting_blood_sugar") == 1:
        tags.append("Metabolic Dysregulation / Hyperglycemia")
    if chol >= 240:
        tags.append("Severe Hypercholesterolemia")
    elif chol >= 200:
        tags.append("Dyslipidemia")
    if st_dep >= 1.0:
        tags.append("ECG Repolarization Abnormality (ST Depression)")

    if not tags:
        if risk_level == "High Risk":
            tags.append("Multifactorial Cardiovascular Risk State")
        elif risk_level == "Moderate Risk":
            tags.append("Atherosclerotic Risk Factor Burden")
        else:
            tags.append("Routine Preventive Health Evaluation")

    primary = tags[0]
    secondary = f" with {tags[1]}" if len(tags) > 1 else ""
    return f"{risk_level} - {primary}{secondary}"


# ---------------------------------------------------------------------------
# Auth Helpers
# ---------------------------------------------------------------------------

def get_password_hash(password: str) -> str:
    # Use bcrypt's built-in salt generation for secure hashing
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: Optional[str] = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    if not token:
        raise HTTPException(status_code=401, detail="Authentication token missing")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user = db.query(User).filter(User.email == email).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not active or found")
    return user


def get_current_user_optional(token: Optional[str] = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Optional[User]:
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if not email:
            return None
        user = db.query(User).filter(User.email == email).first()
        return user if (user and user.is_active) else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Multi-tenant helpers
# ---------------------------------------------------------------------------

def require_hospital_access(target_hospital_id, current_user: User) -> None:
    """Raise 403 if a non-super_admin user tries to access a different hospital."""
    if getattr(current_user, "role", None) == "super_admin":
        return
    user_hid = getattr(current_user, "hospital_id", None)
    if (
        user_hid is None
        or target_hospital_id is None
        or int(user_hid) != int(target_hospital_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this hospital",
        )


def verify_hospital_access(
    hospital_id: int,
    current_user: User = Depends(get_current_user),
) -> None:
    """FastAPI dependency enforcing tenant isolation on explicit hospital_id routes."""
    require_hospital_access(hospital_id, current_user)


def require_admin(current_user: User) -> None:
    """Raise 403 unless the user is a platform or hospital admin."""
    if current_user.role not in ("admin", "hospital_admin", "super_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")


def tenant_scope(current_user: User):
    """Return a hospital_id filter value that scopes queries to the current tenant.

    super_admin -> None (global scope); everyone else -> their own hospital.
    """
    if current_user.role == "super_admin":
        return None
    return current_user.hospital_id


def verify_patient_access(
    patient_id: int,
    current_user: User,
    db: Session,
    require_assigned: bool = True
) -> User:
    """Verify doctor has authorization to access patient data.

    Args:
        patient_id: ID of patient to access
        current_user: Currently authenticated user
        db: Database session
        require_assigned: If True, doctor must be assigned to patient

    Returns:
        Patient User object if authorized

    Raises:
        HTTPException: 404 if patient not found, 403 if unauthorized
    """
    patient = db.query(User).filter(
        User.id == patient_id,
        User.role == "patient",
        User.is_active == True
    ).first()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # MULTI-TENANT: block cross-hospital access for every tenant-scoped role.
    require_hospital_access(patient.hospital_id, current_user)

    # Legacay single-tenant "admin" (preferred role: hospital_admin / super_admin)
    if current_user.role in ("admin", "hospital_admin"):
        return patient

    # Doctor must be assigned to patient
    if current_user.role == "doctor":
        if require_assigned and patient.doctor_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Access denied: Patient not assigned to you"
            )
        return patient

    # Patients can only access their own data
    if current_user.role == "patient" and current_user.id != patient_id:
        raise HTTPException(status_code=403, detail="Access denied")

    raise HTTPException(status_code=403, detail="Unauthorized access")


# ---------------------------------------------------------------------------
# App & Startup
# ---------------------------------------------------------------------------

app = FastAPI(title="Medical Risk XAI Backend", version="1.0.0")

# SECURITY: Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# CORS configuration - restrictive for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:5173",
        # Add your production domain here
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.on_event("startup")
def startup_event():
    create_tables()
    # Note: Database seeding is now handled by scripts/seed_demo_data.py
    # which samples real patient data from raw datasets instead of hardcoded values
    print("[startup] Database tables created. Run scripts/seed_demo_data.py to populate with sample data from raw datasets.")


@app.get("/health")
def health_check():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler - prevents stack trace exposure in production."""
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal error occurred. Please contact support if the issue persists."
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP exception handler with logging."""
    import logging
    logger = logging.getLogger(__name__)

    if exc.status_code >= 500:
        logger.error(f"HTTP {exc.status_code}: {exc.detail}")

    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


# ---------------------------------------------------------------------------
# Auth Endpoints
# ---------------------------------------------------------------------------

@app.post("/auth/login", response_model=LoginResponse)
def login_json(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.strip().lower()).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        # SECURITY: Generic error message prevents user enumeration
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    # MULTI-TENANT: If a hospital code was supplied, it must match the user's tenant.
    if payload.hospital_code:
        payload_code = payload.hospital_code.strip().upper()
        user_code = (user.hospital_code or "").strip().upper()
        if user.role != "super_admin" and payload_code != user_code:
            raise HTTPException(status_code=403, detail="Hospital code does not match this account")

    token = create_access_token({
        "sub": user.email,
        "role": user.role,
        "id": user.id,
        "hospital_id": user.hospital_id,
    })
    return LoginResponse(
        access_token=token,
        role=user.role,
        name=user.name or user.email,
        email=user.email,
        id=user.id,
        hospital_id=user.hospital_id,
        hospital_code=user.hospital_code,
    )


@app.post("/auth/register", response_model=LoginResponse)
def self_register_patient(payload: PatientSelfRegister, db: Session = Depends(get_db)):
    email_clean = payload.email.strip().lower()
    existing = db.query(User).filter(User.email == email_clean).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists")

    # MULTI-TENANT: Resolve the hospital tenant from the code.
    hospital = db.query(Hospital).filter(
        Hospital.hospital_code == payload.hospital_code.strip().upper()
    ).first()
    if not hospital or not hospital.is_active:
        raise HTTPException(status_code=400, detail="Invalid or inactive hospital code")

    doc = None
    if payload.preferred_doctor_id:
        doc = db.query(User).filter(
            User.id == payload.preferred_doctor_id,
            User.role == "doctor",
            User.is_active == True,
            User.hospital_id == hospital.id,
        ).first()

    patient = User(
        name=payload.name.strip(),
        email=email_clean,
        hashed_password=get_password_hash(payload.password),
        role="patient",
        hospital_id=hospital.id,
        hospital_code=hospital.hospital_code,
        doctor_id=doc.id if doc else None,
        pending_assignment=True if not doc else False,
        is_active=True,
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)

    # Create PatientRegistrationRequest for doctor review queue
    req = PatientRegistrationRequest(
        hospital_id=hospital.id,
        patient_id=patient.id,
        preferred_doctor_id=doc.id if doc else None,
        department_preference=payload.department_preference or (doc.specialization if doc else "Cardiology"),
        status="pending",
        notes=f"Self-registered by patient. Preferred doctor: {doc.name if doc else 'General Department Queue'}",
    )
    db.add(req)

    # Audit log
    audit = AuditLog(
        hospital_id=hospital.id,
        actor_user_id=patient.id,
        actor_role="patient",
        action="self_registered",
        target_type="User",
        target_id=patient.id,
        details=json.dumps({
            "patient_id": patient.id,
            "patient_name": patient.name,
            "preferred_doctor_id": doc.id if doc else None,
            "department": payload.department_preference,
        }),
    )
    db.add(audit)
    db.commit()

    token = create_access_token({
        "sub": patient.email,
        "role": patient.role,
        "id": patient.id,
        "hospital_id": patient.hospital_id,
    })
    return LoginResponse(
        access_token=token,
        role=patient.role,
        name=patient.name or patient.email,
        email=patient.email,
        id=patient.id,
        hospital_id=patient.hospital_id,
        hospital_code=patient.hospital_code,
    )


@app.post("/auth/hospital-register", response_model=HospitalOut)
def hospital_register(
    payload: HospitalRegisterPayload,
    db: Session = Depends(get_db),
    super_admin: User = Depends(get_current_user),
):
    """Super Admin provisions a new hospital tenant + its hospital admin account."""
    if super_admin.role != "super_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super Admin access required")

    email_clean = payload.hospital_admin_email.strip().lower()
    existing = db.query(User).filter(User.email == email_clean).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists")

    # Generate a unique hospital code.
    code = None
    used = {row[0] for row in db.query(Hospital.hospital_code).all() if row[0]}
    for _ in range(200):
        candidate = "".join(secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(6))
        if candidate not in used:
            code = candidate
            break
    if not code:
        raise HTTPException(status_code=500, detail="Could not generate a unique hospital code")

    hospital = Hospital(
        name=payload.name.strip(),
        hospital_code=code,
        address=payload.address.strip(),
        contact_number=payload.contact_number.strip(),
        latitude=payload.latitude,
        longitude=payload.longitude,
        is_active=True,
        subscription_tier="standard",
    )
    db.add(hospital)
    db.flush()

    admin = User(
        name=payload.hospital_admin_name.strip(),
        email=email_clean,
        hashed_password=get_password_hash(payload.hospital_admin_password),
        role="hospital_admin",
        hospital_id=hospital.id,
        hospital_code=code,
        is_active=True,
    )
    db.add(admin)
    db.flush()

    audit = AuditLog(
        hospital_id=hospital.id,
        actor_user_id=super_admin.id,
        actor_role="super_admin",
        action="created_hospital",
        target_type="Hospital",
        target_id=hospital.id,
        details=json.dumps({"hospital_name": hospital.name, "hospital_code": code}),
    )
    db.add(audit)
    db.commit()
    db.refresh(hospital)
    return hospital


@app.post("/auth/hospital-login", response_model=LoginResponse)
def hospital_login(
    payload: HospitalLoginPayload,
    db: Session = Depends(get_db),
):
    """Login for hospital users (hospital_admin / doctor / patient) scoped by hospital code."""
    email_clean = payload.email.strip().lower()
    user = db.query(User).filter(User.email == email_clean).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")
    if user.role == "super_admin":
        raise HTTPException(status_code=403, detail="Use super-admin login")

    code = payload.hospital_code.strip().upper()
    user_code = (user.hospital_code or "").strip().upper()
    if not user_code or code != user_code:
        raise HTTPException(status_code=403, detail="Hospital code does not match this account")

    token = create_access_token({
        "sub": user.email,
        "role": user.role,
        "id": user.id,
        "hospital_id": user.hospital_id,
    })
    return LoginResponse(
        access_token=token,
        role=user.role,
        name=user.name or user.email,
        email=user.email,
        id=user.id,
        hospital_id=user.hospital_id,
        hospital_code=user.hospital_code,
    )


@app.post("/auth/super-admin-login", response_model=LoginResponse)
def super_admin_login(
    payload: SuperAdminLoginPayload,
    db: Session = Depends(get_db),
):
    """Login for the platform Super Admin (no tenant scoping)."""
    email_clean = payload.email.strip().lower()
    user = db.query(User).filter(User.email == email_clean).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if user.role != "super_admin":
        raise HTTPException(status_code=403, detail="Super Admin access required")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    token = create_access_token({
        "sub": user.email,
        "role": user.role,
        "id": user.id,
        "hospital_id": user.hospital_id,
    })
    return LoginResponse(
        access_token=token,
        role=user.role,
        name=user.name or user.email,
        email=user.email,
        id=user.id,
        hospital_id=user.hospital_id,
        hospital_code=user.hospital_code,
    )


@app.get("/auth/me")
def get_current_user_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns the currently authenticated user's profile information.

    SECURITY: Only returns non-sensitive fields based on role.
    """
    assigned_doctor_name = None
    if current_user.doctor_id:
        doc = db.query(User).filter(User.id == current_user.doctor_id).first()
        assigned_doctor_name = doc.name if doc else None

    # Base profile fields (safe for all roles)
    profile = {
        "id": current_user.id,
        "name": current_user.name or current_user.email,
        "email": current_user.email,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "doctor_id": current_user.doctor_id,
        "assigned_doctor": assigned_doctor_name,
    }

    # Add role-specific fields
    if current_user.role == "patient":
        profile.update({
            "age": current_user.age,
            "sex": current_user.sex,
            "is_demographics_locked": bool(current_user.is_demographics_locked),
            "phone_number": current_user.phone_number,
            "emergency_contact_name": current_user.emergency_contact_name,
            "emergency_contact_phone": current_user.emergency_contact_phone,
            "address": current_user.address,
        })
    elif current_user.role == "doctor":
        profile.update({
            "specialization": current_user.specialization,
            "license_number": current_user.license_number,
            "degree": current_user.degree,
            "years_of_experience": current_user.years_of_experience,
            "certifications": current_user.certifications,
        })

    # SECURITY: Never expose password hashes or sensitive internal fields
    return profile


@app.get("/auth/demo-accounts")
def get_demo_accounts(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Returns active user profiles for the login demo dropdown.

    Demo UX note: This is intentionally accessible without authentication so the
    login page can display all seeded credentials. Tenant-scoping still applies
    when an authenticated non-super-admin calls it.
    """
    q = db.query(User).filter(User.is_active == True)

    hid = tenant_scope(current_user) if current_user and current_user.role != "super_admin" else None
    if hid is not None:
        q = q.filter(User.hospital_id == hid)

    users = q.order_by(User.role.asc(), User.id.asc()).all()
    out = []
    for user in users:
        name = user.name or user.email
        role_display = {
            "admin": "Admin",
            "doctor": "Doctor",
            "patient": "Patient",
        }.get(user.role, user.role.title())
        label = f"{role_display} ID {user.id}: {name}"
        if user.role == "doctor" and not name.lower().startswith("dr."):
            label = f"Dr. {name} (Doctor ID {user.id})"
        out.append({
            "id": user.id,
            "name": name,
            "email": user.email,
            "role": user.role,
            "hospital_code": user.hospital_code,
            "label": label,
            "is_active": user.is_active,
        })
    return out


@app.get("/doctor/all-doctors")
def get_all_active_doctors(db: Session = Depends(get_db), hospital_code: Optional[str] = None):
    """Returns list of active doctors for transfers, registration routing, and patient selection.

    MULTI-TENANT: If a hospital_code is supplied (e.g. from the self-registration form),
    only that tenant's doctors are returned so patient registration never surfaces
    doctor names from other hospitals.
    """
    q = db.query(User).filter(User.role == "doctor", User.is_active == True)
    if hospital_code:
        q = q.filter(User.hospital_code == hospital_code.strip().upper())
    docs = q.order_by(User.name.asc()).all()
    return [
        {
            "id": d.id,
            "name": d.name or d.email,
            "email": d.email,
            "specialization": d.specialization or "Clinical Specialist",
            "license_number": d.license_number or "DOC-REG",
            "degree": d.degree,
            "years_of_experience": d.years_of_experience,
            "certifications": d.certifications,
        }
        for d in docs
    ]


# ---------------------------------------------------------------------------
# Admin Endpoints (role: admin)
# ---------------------------------------------------------------------------

@app.post("/admin/doctors")
def add_doctor(doc_in: DoctorCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_admin(current_user)
    hid = tenant_scope(current_user)

    existing = db.query(User).filter(User.email == doc_in.email.strip().lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # MULTI-TENANT: The doctor belongs to the admin's hospital.
    hospital = db.query(Hospital).filter(Hospital.id == hid).first() if hid else None
    hospital_code = hospital.hospital_code if hospital else None

    doctor = User(
        name=doc_in.name,
        email=doc_in.email.strip().lower(),
        hashed_password=get_password_hash(doc_in.password),
        role="doctor",
        hospital_id=hid,
        hospital_code=hospital_code,
        specialization=doc_in.specialization,
        license_number=doc_in.license_number,
        degree=doc_in.degree,
        years_of_experience=doc_in.years_of_experience,
        certifications=doc_in.certifications,
        is_active=True,
    )
    db.add(doctor)
    db.commit()
    db.refresh(doctor)

    # Write AuditLog
    audit = AuditLog(
        hospital_id=hid,
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        action="created_doctor",
        target_type="User",
        target_id=doctor.id,
        details=json.dumps({
            "doctor_id": doctor.id,
            "name": doctor.name,
            "email": doctor.email,
            "specialization": doctor.specialization,
            "license_number": doctor.license_number,
        }),
    )
    db.add(audit)
    db.commit()

    return {"status": "success", "message": f"Doctor {doc_in.name} added successfully.", "doctor_id": doctor.id}


@app.post("/admin/patients")
def add_patient(pat_in: PatientCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_admin(current_user)
    hid = tenant_scope(current_user)

    existing = db.query(User).filter(User.email == pat_in.email.strip().lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    if pat_in.doctor_id:
        doc = db.query(User).filter(User.id == pat_in.doctor_id, User.role == "doctor").first()
        if not doc:
            raise HTTPException(status_code=400, detail="Assigned doctor ID not found")
        # MULTI-TENANT: assigned doctor must be in the same hospital.
        if hid is not None and doc.hospital_id != hid:
            raise HTTPException(status_code=403, detail="Assigned doctor is in a different hospital")

    hospital = db.query(Hospital).filter(Hospital.id == hid).first() if hid else None
    hospital_code = hospital.hospital_code if hospital else None

    patient = User(
        name=pat_in.name,
        email=pat_in.email.strip().lower(),
        hashed_password=get_password_hash(pat_in.password),
        role="patient",
        hospital_id=hid,
        hospital_code=hospital_code,
        doctor_id=pat_in.doctor_id,
        is_active=True,
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)

    # Write AuditLog
    audit = AuditLog(
        hospital_id=hid,
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        action="created_patient",
        target_type="User",
        target_id=patient.id,
        details=json.dumps({
            "patient_id": patient.id,
            "name": patient.name,
            "email": patient.email,
            "assigned_doctor_id": patient.doctor_id,
        }),
    )
    db.add(audit)
    db.commit()

    return {"status": "success", "message": f"Patient {pat_in.name} added successfully.", "patient_id": patient.id}


@app.put("/admin/patients/{patient_id}/reassign-doctor", response_model=DoctorTransferResponse)
def reassign_patient_doctor(
    patient_id: int,
    payload: DoctorTransferRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    hid = tenant_scope(current_user)

    patient = db.query(User).filter(User.id == patient_id, User.role == "patient").first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    if hid is not None and patient.hospital_id != hid:
        raise HTTPException(status_code=403, detail="Access denied to this patient")

    new_doc = db.query(User).filter(User.id == payload.new_doctor_id, User.role == "doctor").first()
    if not new_doc:
        raise HTTPException(status_code=404, detail="Doctor not found")
    if not new_doc.is_active:
        raise HTTPException(status_code=400, detail="Doctor account is inactive")
    # MULTI-TENANT: transfers stay within the same hospital.
    if hid is not None and new_doc.hospital_id != hid:
        raise HTTPException(status_code=403, detail="Cannot transfer to a doctor in a different hospital")

    old_doctor_id = patient.doctor_id
    patient.reassign_doctor(payload.new_doctor_id)

    pending_req = db.query(PatientRegistrationRequest).filter(
        PatientRegistrationRequest.patient_id == patient_id,
        PatientRegistrationRequest.status.in_(["pending", "forwarded"]),
    ).first()
    if pending_req:
        pending_req.status = "accepted"
        pending_req.preferred_doctor_id = payload.new_doctor_id
        pending_req.updated_at = datetime.now(timezone.utc)

    # Write AuditLog entry
    audit = AuditLog(
        hospital_id=hid,
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        action="reassigned_patient",
        target_type="User",
        target_id=patient.id,
        details=json.dumps({
            "patient_id": patient.id,
            "patient_name": patient.name,
            "old_doctor_id": old_doctor_id,
            "new_doctor_id": new_doc.id,
            "new_doctor_name": new_doc.name,
        }),
    )
    db.add(audit)
    db.commit()
    db.refresh(patient)

    return DoctorTransferResponse(
        status="success",
        message=f"Patient {patient.name or patient.email} successfully reassigned to Dr. {new_doc.name}.",
        patient_id=patient.id,
        doctor_id=new_doc.id,
        doctor_name=new_doc.name,
    )


@app.get("/admin/users")
def list_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_admin(current_user)
    hid = tenant_scope(current_user)

    q = db.query(User)
    if hid is not None:
        q = q.filter(User.hospital_id == hid)
    users = q.order_by(User.id.asc()).all()
    # MULTI-TENANT PRIVACY: A platform Super Admin must never see the names or
    # emails of hospital doctors/patients -- only aggregate totals. Hospital
    # admins see their own tenants' full records.
    out = []
    for u in users:
        doctor_name = u.doctor.name if u.doctor else None
        is_pii = u.role in ("doctor", "patient")
        if current_user.role == "super_admin" and is_pii:
            name = "Doctor" if u.role == "doctor" else "Patient"
            email = None
            doctor_name = None  # do not reveal the assigned physician
        else:
            name = u.name or u.email
            email = u.email
        out.append(
            {
                "id": u.id,
                "name": name,
                "email": email,
                "role": u.role,
                "is_active": u.is_active,
                "specialization": u.specialization,
                "license_number": u.license_number,
                "degree": u.degree,
                "years_of_experience": u.years_of_experience,
                "certifications": u.certifications,
                "doctor_id": u.doctor_id,
                "assigned_doctor": doctor_name,
                "phone_number": u.phone_number,
            }
        )
    return out


@app.put("/admin/users/{user_id}/deactivate")
def deactivate_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_admin(current_user)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # MULTI-TENANT: hospital_admin can only manage users within their own hospital.
    hid = tenant_scope(current_user)
    if hid is not None and (user.hospital_id != hid or user.role == "super_admin"):
        raise HTTPException(status_code=403, detail="Access denied to this user")
    user.is_active = not user.is_active  # Toggle status
    db.commit()
    status_str = "activated" if user.is_active else "deactivated"
    return {"status": "success", "message": f"User {user.name} {status_str}."}


@app.get("/admin/activity")
def get_admin_activity(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_admin(current_user)
    hid = tenant_scope(current_user)

    q = db.query(AuditLog)
    if hid is not None:
        q = q.filter(AuditLog.hospital_id == hid)
    logs = (
        q.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(100)
        .all()
    )
    out = []
    for log in logs:
        actor_name = log.actor.name if (log.actor and log.actor.name) else (
            f"User #{log.actor_user_id}" if log.actor_user_id else "System"
        )
        out.append(
            {
                "id": log.id,
                "actor_user_id": log.actor_user_id,
                "actor_name": actor_name,
                "actor_role": log.actor_role,
                "action": log.action,
                "target_type": log.target_type,
                "target_id": log.target_id,
                "details": log.details,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
        )
    return out


@app.get("/admin/overview")
def get_admin_overview(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_admin(current_user)
    hid = tenant_scope(current_user)

    def scoped(model):
        q = db.query(model)
        if hid is not None:
            q = q.filter(model.hospital_id == hid)
        return q

    total_doctors = scoped(User).filter(User.role == "doctor").count()
    total_patients = scoped(User).filter(User.role == "patient").count()
    total_predictions = scoped(PatientAssessment).count() + db.query(PredictionLog).count()
    total_blood_tests = scoped(BloodTestResult).count()

    # Risk level distribution
    risk_q = db.query(PatientAssessment.risk_level, func.count(PatientAssessment.id))
    if hid is not None:
        risk_q = risk_q.filter(PatientAssessment.hospital_id == hid)
    risk_query = risk_q.group_by(PatientAssessment.risk_level).all()
    distribution = {"Low": 0, "Medium": 0, "High": 0}
    for level, count in risk_query:
        if not level:
            continue
        level_str = str(level).strip().lower()
        if "low" in level_str:
            distribution["Low"] += count
        elif "med" in level_str or "mod" in level_str:
            distribution["Medium"] += count
        elif "high" in level_str:
            distribution["High"] += count
        else:
            distribution[level] = count

    return {
        "total_doctors": total_doctors,
        "total_patients": total_patients,
        "total_predictions": total_predictions,
        "total_blood_tests": total_blood_tests,
        "risk_distribution": distribution,
    }


# ---------------------------------------------------------------------------
# Hospital Directory & Emergency Availability (admin)
# ---------------------------------------------------------------------------

def _serialize_hospital(h):
    avail = [
        {
            "id": a.id,
            "hospital_id": a.hospital_id,
            "specialization": a.specialization,
            "available_doctors": a.available_doctors,
        }
        for a in h.doctors
    ]
    return {
        "id": h.id,
        "name": h.name,
        "hospital_code": h.hospital_code,
        "address": h.address,
        "contact_number": h.contact_number,
        "latitude": h.latitude,
        "longitude": h.longitude,
        "available_beds": h.available_beds,
        "icu_beds_available": h.icu_beds_available,
        "ventilators_available": h.ventilators_available,
        "blood_bank_available": h.blood_bank_available,
        "emergency_services_available": h.emergency_services_available,
        "is_active": h.is_active,
        "subscription_tier": h.subscription_tier,
        "updated_at": h.updated_at,
        "doctor_availability": avail,
        "distance_km": None,
    }


@app.get("/admin/hospitals", response_model=List[HospitalOut])
def list_hospitals_admin(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_admin(current_user)
    hid = tenant_scope(current_user)

    q = db.query(Hospital)
    if hid is not None:
        q = q.filter(Hospital.id == hid)
    hospitals = q.all()
    result = [_serialize_hospital(h) for h in hospitals]

    # MULTI-TENANT: Only the platform Super Admin sees the full hospital map, so
    # only they get the km distance between each pair (haversine). A hospital
    # admin sees only their own hospital and gets no distance.
    if current_user.role == "super_admin":
        for h in result:
            partner = next(
                (x for x in result
                 if x["id"] != h["id"] and x["latitude"] and x["longitude"]
                 and h["latitude"] and h["longitude"]),
                None,
            )
            if partner:
                h["distance_km"] = round(
                    haversine_distance(
                        h["latitude"], h["longitude"],
                        partner["latitude"], partner["longitude"],
                    ),
                    1,
                )
    return result


@app.get("/admin/hospitals/{hospital_id}", response_model=HospitalOut)
def get_hospital_admin(hospital_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_admin(current_user)

    h = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Hospital not found")
    require_hospital_access(h.id, current_user)
    return _serialize_hospital(h)


@app.post("/admin/hospitals", response_model=HospitalOut)
def create_hospital(hospital_in: HospitalCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # MULTI-TENANT: Only the platform Super Admin provisions hospitals.
    if current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="Super Admin access required")

    # Generate a unique hospital code.
    code = None
    used = {row[0] for row in db.query(Hospital.hospital_code).all() if row[0]}
    for _ in range(200):
        candidate = "".join(secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(6))
        if candidate not in used:
            code = candidate
            break
    if not code:
        raise HTTPException(status_code=500, detail="Could not generate a unique hospital code")

    h = Hospital(
        name=hospital_in.name,
        hospital_code=code,
        address=hospital_in.address,
        contact_number=hospital_in.contact_number,
        latitude=hospital_in.latitude,
        longitude=hospital_in.longitude,
        available_beds=hospital_in.available_beds,
        icu_beds_available=hospital_in.icu_beds_available,
        ventilators_available=hospital_in.ventilators_available,
        blood_bank_available=hospital_in.blood_bank_available,
        emergency_services_available=hospital_in.emergency_services_available,
        is_active=True,
        subscription_tier="standard",
    )
    db.add(h)
    db.commit()
    db.refresh(h)
    return _serialize_hospital(h)


@app.put("/admin/hospitals/{hospital_id}", response_model=HospitalOut)
def update_hospital(hospital_id: int, hospital_in: HospitalUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_admin(current_user)

    h = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Hospital not found")
    require_hospital_access(h.id, current_user)

    update_data = hospital_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(h, field, value)
    h.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(h)
    return _serialize_hospital(h)


@app.delete("/admin/hospitals/{hospital_id}")
def delete_hospital(hospital_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # MULTI-TENANT: Only the platform Super Admin can remove a hospital tenant.
    if current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="Super Admin access required")

    h = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Hospital not found")

    db.delete(h)
    db.commit()
    return {"status": "success", "message": "Hospital deleted"}


@app.post("/admin/hospitals/{hospital_id}/doctor-availability", response_model=HospitalDoctorAvailabilityOut)
def add_hospital_doctor_availability(hospital_id: int, avail_in: HospitalDoctorAvailabilityCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_admin(current_user)

    h = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Hospital not found")
    require_hospital_access(h.id, current_user)

    # Check if already exists for this specialization
    existing = db.query(HospitalDoctorAvailability).filter(
        HospitalDoctorAvailability.hospital_id == hospital_id,
        HospitalDoctorAvailability.specialization == avail_in.specialization,
    ).first()
    if existing:
        existing.available_doctors = avail_in.available_doctors
        db.commit()
        db.refresh(existing)
        return existing

    avail = HospitalDoctorAvailability(
        hospital_id=hospital_id,
        specialization=avail_in.specialization,
        available_doctors=avail_in.available_doctors,
    )
    db.add(avail)
    db.commit()
    db.refresh(avail)
    return avail


@app.delete("/admin/hospitals/{hospital_id}/doctor-availability/{avail_id}")
def remove_hospital_doctor_availability(hospital_id: int, avail_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    avail = db.query(HospitalDoctorAvailability).filter(
        HospitalDoctorAvailability.id == avail_id,
        HospitalDoctorAvailability.hospital_id == hospital_id,
    ).first()
    if not avail:
        raise HTTPException(status_code=404, detail="Doctor availability entry not found")

    db.delete(avail)
    db.commit()
    return {"status": "success", "message": "Doctor availability removed"}


# ---------------------------------------------------------------------------
# Hospital Directory & Emergency Availability (doctor/admin)
# ---------------------------------------------------------------------------

@app.get("/doctor/hospitals", response_model=List[HospitalOut])
def list_hospitals_doctor(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in ["doctor", "admin"]:
        raise HTTPException(status_code=403, detail="Doctor or Admin access required")

    hospitals = db.query(Hospital).all()
    out = []
    for h in hospitals:
        avail = [
            {
                "id": a.id,
                "hospital_id": a.hospital_id,
                "specialization": a.specialization,
                "available_doctors": a.available_doctors,
            }
            for a in h.doctors
        ]
        out.append({
            "id": h.id,
            "name": h.name,
            "address": h.address,
            "contact_number": h.contact_number,
            "latitude": h.latitude,
            "longitude": h.longitude,
            "available_beds": h.available_beds,
            "icu_beds_available": h.icu_beds_available,
            "ventilators_available": h.ventilators_available,
            "blood_bank_available": h.blood_bank_available,
            "emergency_services_available": h.emergency_services_available,
            "updated_at": h.updated_at,
            "doctor_availability": avail,
            "distance_km": None,
        })
    return out


@app.get("/doctor/hospitals/{hospital_id}", response_model=HospitalOut)
def get_hospital_doctor(hospital_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in ["doctor", "admin"]:
        raise HTTPException(status_code=403, detail="Doctor or Admin access required")

    h = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Hospital not found")

    avail = [
        {
            "id": a.id,
            "hospital_id": a.hospital_id,
            "specialization": a.specialization,
            "available_doctors": a.available_doctors,
        }
        for a in h.doctors
    ]
    return {
        "id": h.id,
        "name": h.name,
        "address": h.address,
        "contact_number": h.contact_number,
        "latitude": h.latitude,
        "longitude": h.longitude,
        "available_beds": h.available_beds,
        "icu_beds_available": h.icu_beds_available,
        "ventilators_available": h.ventilators_available,
        "blood_bank_available": h.blood_bank_available,
        "emergency_services_available": h.emergency_services_available,
        "updated_at": h.updated_at,
        "doctor_availability": avail,
        "distance_km": None,
    }


@app.get("/doctor/hospitals/nearby", response_model=List[HospitalOut])
@app.get("/patient/hospitals/nearby", response_model=List[HospitalOut])
@app.get("/hospitals/nearby", response_model=List[HospitalOut])
def get_nearby_hospitals(latitude: float, longitude: float, radius_km: float = 50, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    hospitals = db.query(Hospital).all()
    out = []
    for h in hospitals:
        dist = haversine_distance(latitude, longitude, h.latitude, h.longitude)
        if dist <= radius_km:
            avail = [
                {
                    "id": a.id,
                    "hospital_id": a.hospital_id,
                    "specialization": a.specialization,
                    "available_doctors": a.available_doctors,
                }
                for a in h.doctors
            ]
            out.append({
                "id": h.id,
                "name": h.name,
                "address": h.address,
                "contact_number": h.contact_number,
                "latitude": h.latitude,
                "longitude": h.longitude,
                "available_beds": h.available_beds,
                "icu_beds_available": h.icu_beds_available,
                "ventilators_available": h.ventilators_available,
                "blood_bank_available": h.blood_bank_available,
                "emergency_services_available": h.emergency_services_available,
                "updated_at": h.updated_at,
                "doctor_availability": avail,
                "distance_km": round(dist, 2),
            })
    out.sort(key=lambda x: x["distance_km"])
    return out


@app.put("/doctor/profile", response_model=UserOut)
def update_doctor_profile(
    profile_in: DoctorProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "doctor":
        raise HTTPException(status_code=403, detail="Doctor access required")

    if profile_in.name is not None:
        current_user.name = profile_in.name
    if profile_in.specialization is not None:
        current_user.specialization = profile_in.specialization
    if profile_in.license_number is not None:
        current_user.license_number = profile_in.license_number
    if profile_in.degree is not None:
        current_user.degree = profile_in.degree
    if profile_in.years_of_experience is not None:
        current_user.years_of_experience = profile_in.years_of_experience
    if profile_in.certifications is not None:
        current_user.certifications = profile_in.certifications

    db.commit()
    db.refresh(current_user)
    return current_user


# ---------------------------------------------------------------------------
# Doctor Endpoints (role: doctor)
# ---------------------------------------------------------------------------

@app.get("/doctor/patients")
def get_doctor_patients(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in ["doctor", "admin", "hospital_admin"]:
        raise HTTPException(status_code=403, detail="Doctor access required")

    # MULTI-TENANT: non-super-admins only see patients in their own hospital.
    hid = tenant_scope(current_user)
    query = db.query(User).filter(User.role == "patient")
    if hid is not None:
        query = query.filter(User.hospital_id == hid)
    if current_user.role == "doctor":
        query = query.filter(User.doctor_id == current_user.id)

    patients = query.all()
    return [
        {
            "id": p.id,
            "name": p.name or p.email,
            "email": p.email,
            "age": p.age,
            "sex": p.sex,
            "is_demographics_locked": bool(p.is_demographics_locked or (p.age is not None and p.sex is not None)),
            "phone_number": p.phone_number,
            "emergency_contact_name": p.emergency_contact_name,
            "emergency_contact_phone": p.emergency_contact_phone,
            "address": p.address,
            "doctor_id": p.doctor_id,
            "assigned_doctor": p.doctor.name if p.doctor else None,
            "is_active": p.is_active,
        }
        for p in patients
    ]


@app.post("/doctor/patients")
def doctor_create_patient(
    payload: DoctorPatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Allows doctors to directly create and register a new patient assigned to them."""
    if current_user.role != "doctor":
        raise HTTPException(status_code=403, detail="Doctor access required")

    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="A user with this email already exists")

    pwd = payload.password or "Demo@123"
    patient = User(
        name=payload.name,
        email=payload.email,
        hashed_password=get_password_hash(pwd),
        role="patient",
        # MULTI-TENANT: new patient inherits the doctor's hospital.
        hospital_id=current_user.hospital_id,
        hospital_code=current_user.hospital_code,
        doctor_id=current_user.id,
        age=payload.age,
        sex=payload.sex,
        is_demographics_locked=bool(payload.age is not None or payload.sex is not None),
        phone_number=payload.phone_number,
        emergency_contact_name=payload.emergency_contact_name,
        emergency_contact_phone=payload.emergency_contact_phone,
        address=payload.address,
        is_active=True,
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)

    # Write AuditLog
    audit = AuditLog(
        hospital_id=current_user.hospital_id,
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        action="created_patient",
        target_type="User",
        target_id=patient.id,
        details=json.dumps({
            "patient_id": patient.id,
            "patient_name": patient.name,
            "patient_email": patient.email,
            "assigned_doctor_id": current_user.id,
            "assigned_doctor_name": current_user.name,
            "age": payload.age,
            "sex": payload.sex,
        }),
    )
    db.add(audit)
    db.commit()

    return {
        "id": patient.id,
        "name": patient.name,
        "email": patient.email,
        "age": patient.age,
        "sex": patient.sex,
        "is_demographics_locked": patient.is_demographics_locked,
        "phone_number": patient.phone_number,
        "emergency_contact_name": patient.emergency_contact_name,
        "emergency_contact_phone": patient.emergency_contact_phone,
        "address": patient.address,
        "doctor_id": patient.doctor_id,
        "is_active": patient.is_active,
    }


@app.post("/doctor/patients/{patient_id}/transfer", response_model=DoctorTransferResponse)
def doctor_transfer_patient(
    patient_id: int,
    payload: DoctorTransferRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Allows doctors (or admins) to transfer / refer a patient to another doctor in the hospital."""
    if current_user.role not in ["doctor", "admin", "hospital_admin"]:
        raise HTTPException(status_code=403, detail="Doctor or Admin access required")

    patient = db.query(User).filter(User.id == patient_id, User.role == "patient").first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    # MULTI-TENANT: patient must be in the same hospital.
    require_hospital_access(patient.hospital_id, current_user)

    if current_user.role == "doctor" and patient.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only transfer patients currently assigned to you")

    new_doc = db.query(User).filter(User.id == payload.new_doctor_id, User.role == "doctor").first()
    if not new_doc:
        raise HTTPException(status_code=404, detail="Target doctor not found")
    if not new_doc.is_active:
        raise HTTPException(status_code=400, detail="Target doctor account is inactive")
    # MULTI-TENANT: transfers stay within the same hospital.
    require_hospital_access(new_doc.hospital_id, current_user)
    if new_doc.id == patient.doctor_id:
        raise HTTPException(status_code=400, detail="Patient is already assigned to this doctor")

    old_doc_id = patient.doctor_id
    old_doc = db.query(User).filter(User.id == old_doc_id).first()
    old_doc_name = old_doc.name if old_doc else "Unassigned"

    patient.reassign_doctor(new_doc.id)

    # Write AuditLog entry with transfer reason
    audit = AuditLog(
        hospital_id=patient.hospital_id,
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        action="reassigned_patient",
        target_type="User",
        target_id=patient.id,
        details=json.dumps({
            "patient_id": patient.id,
            "patient_name": patient.name,
            "old_doctor_id": old_doc_id,
            "old_doctor_name": old_doc_name,
            "new_doctor_id": new_doc.id,
            "new_doctor_name": new_doc.name,
            "reason": payload.reason or "Clinical referral / transfer of care",
        }),
    )
    db.add(audit)
    db.commit()
    db.refresh(patient)

    return DoctorTransferResponse(
        status="success",
        message=f"Patient {patient.name} has been transferred to Dr. {new_doc.name} ({new_doc.specialization or 'Specialist'}).",
        patient_id=patient.id,
        doctor_id=new_doc.id,
        doctor_name=new_doc.name,
    )


@app.post("/doctor/patients/{patient_id}/preview-assessment", response_model=AssessmentResult)
def preview_patient_assessment(
    patient_id: int,
    record: PatientRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Step 1 of Assessment Workflow:
    Runs ML prediction and TreeSHAP feature attributions in real time for doctor preview.
    Does NOT save to permanent patient record or lock demographics until approved.
    """
    if current_user.role not in ["doctor", "admin", "hospital_admin"]:
        raise HTTPException(status_code=403, detail="Doctor access required")

    # MULTI-TENANT: verify access (cross-hospital + assignment).
    patient = verify_patient_access(patient_id, current_user, db, require_assigned=(current_user.role == "doctor"))

    effective_age = patient.age if patient.age is not None else record.age
    effective_sex = patient.sex if patient.sex is not None else record.sex

    bp_for_model = record.systolic_bp if record.systolic_bp is not None else getattr(record, "resting_bp", None)
    patient_feature_dict = {k: v for k, v in {
        "age": effective_age,
        "sex": effective_sex,
        "resting_bp": bp_for_model,
        "systolic_bp": record.systolic_bp,
        "diastolic_bp": record.diastolic_bp,
        "cholesterol": record.cholesterol,
        "fasting_blood_sugar": record.fasting_blood_sugar,
        "max_heart_rate": record.max_heart_rate,
        "bmi": record.bmi,
        "smoking": record.smoking,
        "chest_pain_type": record.chest_pain_type,
        "exercise_angina": record.exercise_angina,
        "st_depression": record.st_depression,
        "hypertension": record.hypertension,
        "diabetes": record.diabetes,
    }.items() if v is not None}

    explanation = explain_prediction(patient_feature_dict)
    enriched = enrich_explanation(explanation, patient_feature_dict)

    risk_prob = float(enriched["risk_score"])
    risk_level = str(enriched["risk_category"]["label"])
    risk_pct = float(enriched["risk_percentage"])

    top_3 = [r["reason"] for r in enriched["reasons"][:3]]
    if not top_3:
        for item in explanation["top_contributions"][:3]:
            top_3.append(f"{item['feature']} ({item['impact']}): {item['direction']}")

    auto_diag = generate_auto_diagnosis_title(risk_level, patient_feature_dict, top_3)

    return AssessmentResult(
        risk_level=risk_level,
        risk_probability=round(risk_prob, 4),
        risk_percentage=risk_pct,
        risk_category=RiskCategory(**enriched["risk_category"]),
        top_features=top_3,
        reasons=[RiskReason(**r) for r in enriched["reasons"]],
        recommendations=enriched["recommendations"],
        assessed_at=datetime.now(timezone.utc),
        auto_diagnosis_suggestion=auto_diag,
    )


@app.post("/doctor/patients/{patient_id}/record", response_model=AssessmentResult)
def record_patient_assessment(
    patient_id: int,
    record: PatientRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ["doctor", "admin", "hospital_admin"]:
        raise HTTPException(status_code=403, detail="Doctor access required")

    # MULTI-TENANT: verify access (cross-hospital + assignment).
    patient = verify_patient_access(patient_id, current_user, db, require_assigned=(current_user.role == "doctor"))

    # Demographic Lock Enforcement (Age and Sex cannot be changed once set)
    effective_age = patient.age if patient.age is not None else record.age
    effective_sex = patient.sex if patient.sex is not None else record.sex

    if patient.age is None and record.age is not None:
        patient.age = record.age
        patient.is_demographics_locked = True
    if patient.sex is None and record.sex is not None:
        patient.sex = record.sex
        patient.is_demographics_locked = True

    # Map inputs to model features
    bp_for_model = record.systolic_bp if record.systolic_bp is not None else getattr(record, "resting_bp", None)
    patient_feature_dict = {k: v for k, v in {
        "age": effective_age,
        "sex": effective_sex,
        "resting_bp": bp_for_model,
        "systolic_bp": record.systolic_bp,
        "diastolic_bp": record.diastolic_bp,
        "cholesterol": record.cholesterol,
        "fasting_blood_sugar": record.fasting_blood_sugar,
        "max_heart_rate": record.max_heart_rate,
        "bmi": record.bmi,
        "smoking": record.smoking,
        "chest_pain_type": record.chest_pain_type,
        "exercise_angina": record.exercise_angina,
        "st_depression": record.st_depression,
        "hypertension": record.hypertension,
        "diabetes": record.diabetes,
    }.items() if v is not None}

    explanation = explain_prediction(patient_feature_dict)
    enriched = enrich_explanation(explanation, patient_feature_dict)

    risk_prob = float(enriched["risk_score"])
    risk_level = str(enriched["risk_category"]["label"])
    risk_pct = float(enriched["risk_percentage"])

    # Build legacy top_3 strings and new structured reasons
    top_3 = [r["reason"] for r in enriched["reasons"][:3]]
    if not top_3:
        for item in explanation["top_contributions"][:3]:
            top_3.append(f"{item['feature']} ({item['impact']}): {item['direction']}")

    # Save assessment to database (cleaned up to essential fields only)
    triggered_codes = [r.get("rule_code") for r in enriched.get("triggered_rules", [])]
    recommendations = enriched.get("recommendations", [])
    
    assessment = PatientAssessment(
        hospital_id=patient.hospital_id,
        patient_id=patient.id,
        doctor_id=current_user.id,
        age=effective_age,
        sex=effective_sex,
        systolic_bp=record.systolic_bp,
        diastolic_bp=record.diastolic_bp,
        cholesterol=record.cholesterol,
        fasting_blood_sugar=record.fasting_blood_sugar,
        max_heart_rate=record.max_heart_rate,
        bmi=record.bmi,
        smoking=record.smoking,
        chest_pain_type=record.chest_pain_type,
        exercise_angina=record.exercise_angina,
        st_depression=record.st_depression,
        hypertension=record.hypertension,
        diabetes=record.diabetes,
        prior_medical_events=record.prior_medical_events,
        risk_level=risk_level,
        risk_probability=risk_prob,
        triggered_rule_codes=json.dumps(triggered_codes) if triggered_codes else None,
        clinical_recommendations=json.dumps(recommendations) if recommendations else None,
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    # Write AuditLog
    audit = AuditLog(
        hospital_id=patient.hospital_id,
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        action="added_record",
        target_type="PatientAssessment",
        target_id=assessment.id,
        details=json.dumps({
            "patient_id": patient.id,
            "patient_name": patient.name,
            "assessment_id": assessment.id,
            "risk_level": risk_level,
            "risk_probability": round(risk_prob, 4),
            "systolic_bp": record.systolic_bp,
            "diastolic_bp": record.diastolic_bp,
            "age": effective_age,
            "sex": effective_sex,
        }),
    )
    db.add(audit)
    db.commit()

    auto_diag = generate_auto_diagnosis_title(risk_level, patient_feature_dict, top_3)

    return AssessmentResult(
        risk_level=risk_level,
        risk_probability=round(risk_prob, 4),
        risk_percentage=risk_pct,
        risk_category=RiskCategory(**enriched["risk_category"]),
        top_features=top_3,
        reasons=[RiskReason(**r) for r in enriched["reasons"]],
        recommendations=enriched["recommendations"],
        assessed_at=assessment.created_at,
        auto_diagnosis_suggestion=auto_diag,
    )


# ---------------------------------------------------------------------------
# Guest Patient Immediate Prediction & Clinical Drafts
# ---------------------------------------------------------------------------

@app.post("/doctor/guest-assessment", response_model=AssessmentResult)
def evaluate_guest_patient(
    record: PatientRecordCreate,
    guest_name: Optional[str] = "Walk-in Guest Patient",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Evaluates a walk-in / guest patient immediately without requiring a pre-registered account.
    Returns full XGBoost risk prediction, TreeSHAP feature attributions, and clinical advice.
    """
    if current_user.role not in ["doctor", "admin"]:
        raise HTTPException(status_code=403, detail="Doctor access required")

    bp_for_model = record.systolic_bp if record.systolic_bp is not None else getattr(record, "resting_bp", None)
    patient_feature_dict = {k: v for k, v in {
        "age": record.age,
        "sex": record.sex,
        "resting_bp": bp_for_model,
        "systolic_bp": record.systolic_bp,
        "diastolic_bp": record.diastolic_bp,
        "cholesterol": record.cholesterol,
        "fasting_blood_sugar": record.fasting_blood_sugar,
        "max_heart_rate": record.max_heart_rate,
        "bmi": record.bmi,
        "smoking": record.smoking,
        "chest_pain_type": record.chest_pain_type,
        "exercise_angina": record.exercise_angina,
        "st_depression": record.st_depression,
        "hypertension": record.hypertension,
        "diabetes": record.diabetes,
    }.items() if v is not None}

    explanation = explain_prediction(patient_feature_dict)
    enriched = enrich_explanation(explanation, patient_feature_dict)

    risk_prob = float(enriched["risk_score"])
    risk_level = str(enriched["risk_category"]["label"])
    risk_pct = float(enriched["risk_percentage"])

    top_3 = [r["reason"] for r in enriched["reasons"][:3]]
    if not top_3:
        for item in explanation["top_contributions"][:3]:
            top_3.append(f"{item['feature']} ({item['impact']}): {item['direction']}")

    # Write AuditLog
    audit = AuditLog(
        hospital_id=current_user.hospital_id,
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        action="guest_assessment",
        target_type="GuestEvaluation",
        details=json.dumps({
            "doctor_id": current_user.id,
            "guest_name": guest_name,
            "risk_level": risk_level,
            "risk_probability": round(risk_prob, 4),
            "age": record.age,
            "sex": record.sex,
        }),
    )
    db.add(audit)
    db.commit()

    auto_diag = generate_auto_diagnosis_title(risk_level, patient_feature_dict, top_3)

    return AssessmentResult(
        risk_level=risk_level,
        risk_probability=round(risk_prob, 4),
        risk_percentage=risk_pct,
        risk_category=RiskCategory(**enriched["risk_category"]),
        top_features=top_3,
        reasons=[RiskReason(**r) for r in enriched["reasons"]],
        recommendations=enriched["recommendations"],
        assessed_at=datetime.now(timezone.utc),
        auto_diagnosis_suggestion=auto_diag,
    )


@app.post("/doctor/drafts", response_model=ClinicalDraftOut)
def save_clinical_draft(
    payload: ClinicalDraftCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Saves unassigned guest data or incomplete assessment as a draft to resume later."""
    if current_user.role not in ["doctor", "admin"]:
        raise HTTPException(status_code=403, detail="Doctor access required")

    draft = ClinicalDraft(
        # MULTI-TENANT: draft belongs to the doctor's hospital.
        hospital_id=current_user.hospital_id,
        doctor_id=current_user.id,
        draft_name=payload.draft_name or "Guest Patient Draft",
        guest_identifier=payload.guest_identifier or "Walk-in Guest",
        raw_data_json=json.dumps(payload.data),
        risk_level=payload.risk_level,
        risk_probability=payload.risk_probability,
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)

    return draft


@app.get("/doctor/drafts", response_model=List[ClinicalDraftOut])
def get_clinical_drafts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists all saved drafts for the current doctor."""
    if current_user.role not in ["doctor", "admin"]:
        raise HTTPException(status_code=403, detail="Doctor access required")

    drafts = (
        db.query(ClinicalDraft)
        .filter(ClinicalDraft.doctor_id == current_user.id)
        .order_by(ClinicalDraft.updated_at.desc())
        .all()
    )
    return drafts


@app.delete("/doctor/drafts/{draft_id}")
def delete_clinical_draft(
    draft_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Deletes a saved clinical draft."""
    if current_user.role not in ["doctor", "admin", "hospital_admin"]:
        raise HTTPException(status_code=403, detail="Doctor access required")

    draft = db.query(ClinicalDraft).filter(ClinicalDraft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    if draft.doctor_id != current_user.id and current_user.role not in ("admin", "hospital_admin"):
        raise HTTPException(status_code=403, detail="Access denied")
    require_hospital_access(draft.hospital_id, current_user)

    db.delete(draft)
    db.commit()
    return {"status": "success", "message": "Draft deleted successfully"}


@app.post("/doctor/drafts/{draft_id}/convert")
def convert_draft_to_patient(
    draft_id: int,
    payload: DraftConvertRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Converts a guest clinical draft into a registered patient with an official assessment."""
    if current_user.role not in ["doctor", "admin"]:
        raise HTTPException(status_code=403, detail="Doctor access required")

    draft = db.query(ClinicalDraft).filter(ClinicalDraft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    # MULTI-TENANT: ownership check scoped to the same hospital.
    if draft.doctor_id != current_user.id and current_user.role not in ("admin", "hospital_admin"):
        raise HTTPException(status_code=403, detail="Access denied")
    require_hospital_access(draft.hospital_id, current_user)

    existing = db.query(User).filter(User.email == payload.patient_email).first()
    if existing:
        raise HTTPException(status_code=400, detail="A user with this email already exists")

    data = json.loads(draft.raw_data_json) if draft.raw_data_json else {}

    patient_age = data.get("age")
    patient_sex = data.get("sex")

    new_patient = User(
        name=payload.patient_name,
        email=payload.patient_email,
        hashed_password=get_password_hash(payload.password or "Demo@123"),
        role="patient",
        hospital_id=current_user.hospital_id,
        hospital_code=current_user.hospital_code,
        doctor_id=current_user.id,
        age=float(patient_age) if patient_age is not None and str(patient_age).strip() != "" else None,
        sex=float(patient_sex) if patient_sex is not None and str(patient_sex).strip() != "" else None,
        is_demographics_locked=bool(patient_age is not None and patient_sex is not None),
        phone_number=payload.phone_number,
        emergency_contact_name=payload.emergency_contact_name,
        emergency_contact_phone=payload.emergency_contact_phone,
        address=payload.address,
        is_active=True,
    )
    db.add(new_patient)
    db.commit()
    db.refresh(new_patient)

    # If draft had vitals, create official PatientAssessment
    if data.get("systolic_bp"):
        assessment = PatientAssessment(
            hospital_id=new_patient.hospital_id,
            patient_id=new_patient.id,
            doctor_id=current_user.id,
            age=new_patient.age,
            sex=new_patient.sex,
            systolic_bp=int(data["systolic_bp"]) if data.get("systolic_bp") else None,
            diastolic_bp=int(data["diastolic_bp"]) if data.get("diastolic_bp") else None,
            cholesterol=float(data["cholesterol"]) if data.get("cholesterol") else None,
            fasting_blood_sugar=float(data["fasting_blood_sugar"]) if data.get("fasting_blood_sugar") is not None else None,
            max_heart_rate=float(data["max_heart_rate"]) if data.get("max_heart_rate") else None,
            bmi=float(data["bmi"]) if data.get("bmi") else None,
            smoking=float(data["smoking"]) if data.get("smoking") is not None else None,
            chest_pain_type=float(data["chest_pain_type"]) if data.get("chest_pain_type") is not None else None,
            exercise_angina=float(data["exercise_angina"]) if data.get("exercise_angina") is not None else None,
            st_depression=float(data["st_depression"]) if data.get("st_depression") is not None else None,
            hypertension=1.0 if data.get("hypertension") else 0.0,
            diabetes=1.0 if data.get("diabetes") else 0.0,
            prior_medical_events=data.get("prior_medical_events"),
            risk_level=draft.risk_level or "Low Risk",
            risk_probability=draft.risk_probability or 0.2,
            triggered_rule_codes=None,  # Will be recalculated on full assessment
            clinical_recommendations=None,  # Will be recalculated on full assessment
        )
        db.add(assessment)
        db.commit()

    # Delete draft after conversion
    db.delete(draft)
    db.commit()

    return {
        "status": "success",
        "message": f"Draft converted to registered patient {new_patient.name} successfully.",
        "patient_id": new_patient.id,
        "doctor_id": current_user.id,
    }


# ---------------------------------------------------------------------------
# Doctor Diagnosis & Clinical Notes Endpoints
# ---------------------------------------------------------------------------

@app.post("/doctor/patients/{patient_id}/diagnosis", response_model=DoctorDiagnosisOut)
def record_patient_diagnosis(
    patient_id: int,
    payload: DoctorDiagnosisCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Allows doctors to record or update a clinical diagnosis and treatment plan."""
    if current_user.role not in ["doctor", "admin", "hospital_admin"]:
        raise HTTPException(status_code=403, detail="Doctor access required")

    # MULTI-TENANT: verify the doctor/admin is authorized for this patient + hospital.
    patient = verify_patient_access(patient_id, current_user, db, require_assigned=(current_user.role == "doctor"))

    diag = DoctorDiagnosis(
        hospital_id=patient.hospital_id,
        patient_id=patient.id,
        doctor_id=current_user.id,
        diagnosis_title=payload.diagnosis_title,
        clinical_notes=payload.clinical_notes,
        treatment_plan=payload.treatment_plan,
        prescriptions=payload.prescriptions,
        risk_summary=payload.risk_summary,
    )
    db.add(diag)
    db.commit()
    db.refresh(diag)

    # Write AuditLog
    audit = AuditLog(
        hospital_id=patient.hospital_id,
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        action="recorded_diagnosis",
        target_type="DoctorDiagnosis",
        target_id=diag.id,
        details=json.dumps({
            "patient_id": patient.id,
            "patient_name": patient.name,
            "doctor_id": current_user.id,
            "doctor_name": current_user.name,
            "diagnosis_title": diag.diagnosis_title,
        }),
    )
    db.add(audit)
    db.commit()

    return DoctorDiagnosisOut(
        id=diag.id,
        patient_id=diag.patient_id,
        doctor_id=diag.doctor_id,
        doctor_name=current_user.name,
        doctor_specialization=current_user.specialization,
        doctor_license=current_user.license_number,
        patient_name=patient.name,
        diagnosis_title=diag.diagnosis_title,
        clinical_notes=diag.clinical_notes,
        treatment_plan=diag.treatment_plan,
        prescriptions=diag.prescriptions,
        risk_summary=diag.risk_summary,
        created_at=diag.created_at,
        updated_at=diag.updated_at,
    )


@app.get("/doctor/patients/{patient_id}/diagnoses", response_model=List[DoctorDiagnosisOut])
def get_patient_diagnoses(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetches diagnosis records for a patient.

    SECURITY: Access restricted to assigned doctor or admin only.
    """
    if current_user.role not in ["doctor", "admin"]:
        raise HTTPException(status_code=403, detail="Doctor access required")

    # SECURITY: Verify authorization BEFORE accessing data
    patient = verify_patient_access(patient_id, current_user, db, require_assigned=True)

    diagnoses = (
        db.query(DoctorDiagnosis)
        .filter(DoctorDiagnosis.patient_id == patient_id)
        .order_by(DoctorDiagnosis.created_at.desc())
        .all()
    )

    out = []
    for d in diagnoses:
        doc = d.doctor
        out.append(
            DoctorDiagnosisOut(
                id=d.id,
                patient_id=d.patient_id,
                doctor_id=d.doctor_id,
                doctor_name=doc.name if doc else "Attending Physician",
                doctor_specialization=doc.specialization if doc else "Clinical Medicine",
                doctor_license=doc.license_number if doc else "DOC-REG",
                patient_name=patient.name,
                diagnosis_title=d.diagnosis_title,
                clinical_notes=d.clinical_notes,
                treatment_plan=d.treatment_plan,
                prescriptions=d.prescriptions,
                risk_summary=d.risk_summary,
                created_at=d.created_at,
                updated_at=d.updated_at,
            )
        )
    return out


# ---------------------------------------------------------------------------
# Patient Self-Registration Queue & Transfer Endpoints
# ---------------------------------------------------------------------------

@app.get("/doctor/patient-requests", response_model=List[PatientRegistrationRequestOut])
def get_doctor_patient_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lists pending self-registered patients waiting for doctor acceptance or assignment.
    Scoped to the current hospital tenant.
    """
    if current_user.role not in ["doctor", "admin", "hospital_admin"]:
        raise HTTPException(status_code=403, detail="Doctor access required")

    hid = tenant_scope(current_user)
    if current_user.role in ("admin", "hospital_admin"):
        req_q = db.query(PatientRegistrationRequest).filter(
            PatientRegistrationRequest.status.in_(["pending", "forwarded"])
        )
        if hid is not None:
            req_q = req_q.filter(PatientRegistrationRequest.hospital_id == hid)
        requests = req_q.order_by(PatientRegistrationRequest.created_at.desc()).all()
    else:
        req_q = db.query(PatientRegistrationRequest).filter(
            PatientRegistrationRequest.status.in_(["pending", "forwarded"])
        )
        if hid is not None:
            req_q = req_q.filter(PatientRegistrationRequest.hospital_id == hid)
        requests = req_q.filter(
            (PatientRegistrationRequest.preferred_doctor_id == current_user.id) | (PatientRegistrationRequest.preferred_doctor_id == None)
        ).order_by(PatientRegistrationRequest.created_at.desc()).all()

    out = []
    for r in requests:
        pat = r.patient
        doc = r.preferred_doctor
        out.append(
            PatientRegistrationRequestOut(
                id=r.id,
                patient_id=r.patient_id,
                patient_name=pat.name if pat else "Patient",
                patient_email=pat.email if pat else "patient@hospital.com",
                preferred_doctor_id=r.preferred_doctor_id,
                preferred_doctor_name=doc.name if doc else "General Department Queue",
                department_preference=r.department_preference,
                status=r.status,
                notes=r.notes,
                created_at=r.created_at,
            )
        )
    return out


@app.post("/doctor/patient-requests/{request_id}/accept")
def accept_patient_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Doctor accepts a self-registered patient request into their clinical roster.
    """
    if current_user.role not in ["doctor", "admin", "hospital_admin"]:
        raise HTTPException(status_code=403, detail="Doctor access required")

    req = db.query(PatientRegistrationRequest).filter(PatientRegistrationRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Registration request not found")
    # MULTI-TENANT: request and patient must be in the same hospital as the user.
    req_patient = req.patient
    require_hospital_access(req.hospital_id or (req_patient.hospital_id if req_patient else None), current_user)
    if not req_patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    if req.status not in ["pending", "forwarded"]:
        raise HTTPException(status_code=400, detail=f"Request is already {req.status}")

    if current_user.role == "doctor" and req.preferred_doctor_id and req.preferred_doctor_id != current_user.id and req.status == "forwarded":
        raise HTTPException(status_code=403, detail="This request has been forwarded to another doctor")

    patient = req_patient

    patient.reassign_doctor(current_user.id)
    patient.pending_assignment = False
    req.status = "accepted"
    req.preferred_doctor_id = current_user.id
    req.notes = f"Accepted into clinical care roster by Dr. {current_user.name}"

    audit = AuditLog(
        hospital_id=req.hospital_id or patient.hospital_id,
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        action="accepted_patient_request",
        target_type="User",
        target_id=patient.id,
        details=json.dumps({
            "request_id": req.id,
            "patient_id": patient.id,
            "patient_name": patient.name,
            "doctor_id": current_user.id,
            "doctor_name": current_user.name,
        }),
    )
    db.add(audit)
    db.commit()

    return {"status": "success", "message": f"Patient {patient.name} successfully added to your assigned roster.", "patient_id": patient.id}


@app.post("/doctor/patient-requests/{request_id}/forward")
def forward_patient_request(
    request_id: int,
    payload: ForwardPatientRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Doctor forwards / routes a self-registered patient request to a colleague doctor.
    """
    if current_user.role not in ["doctor", "admin", "hospital_admin"]:
        raise HTTPException(status_code=403, detail="Doctor access required")

    req = db.query(PatientRegistrationRequest).filter(PatientRegistrationRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Registration request not found")
    req_patient = req.patient
    require_hospital_access(req.hospital_id or (req_patient.hospital_id if req_patient else None), current_user)

    if req.status not in ["pending", "forwarded"]:
        raise HTTPException(status_code=400, detail=f"Request is already {req.status}")

    if current_user.role == "doctor" and req.preferred_doctor_id and req.preferred_doctor_id != current_user.id and req.status == "forwarded":
        raise HTTPException(status_code=403, detail="This request has been forwarded to another doctor")

    target_doc = db.query(User).filter(User.id == payload.new_doctor_id, User.role == "doctor", User.is_active == True).first()
    if not target_doc:
        raise HTTPException(status_code=404, detail="Target doctor not found")
    # MULTI-TENANT: only forward within the same hospital.
    require_hospital_access(target_doc.hospital_id, current_user)

    old_doc_name = current_user.name
    req.preferred_doctor_id = target_doc.id
    req.status = "forwarded"
    req.notes = f"Forwarded by Dr. {old_doc_name} to Dr. {target_doc.name}. Reason: {payload.notes or 'Departmental Routing'}"

    # If patient was assigned to this doctor, update pointer
    patient = req_patient
    if patient and patient.pending_assignment:
        patient.doctor_id = target_doc.id

    audit = AuditLog(
        hospital_id=req.hospital_id or (patient.hospital_id if patient else None),
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        action="forwarded_patient_request",
        target_type="PatientRegistrationRequest",
        target_id=req.id,
        details=json.dumps({
            "request_id": req.id,
            "from_doctor_id": current_user.id,
            "to_doctor_id": target_doc.id,
            "to_doctor_name": target_doc.name,
            "notes": payload.notes,
        }),
    )
    db.add(audit)
    db.commit()

    return {"status": "success", "message": f"Patient request forwarded to Dr. {target_doc.name}."}


@app.get("/admin/pending-patients")
def get_admin_pending_patients(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Admin view of all pending patient self-registration requests (tenant-scoped)."""
    require_admin(current_user)
    hid = tenant_scope(current_user)

    req_q = db.query(PatientRegistrationRequest)
    if hid is not None:
        req_q = req_q.filter(PatientRegistrationRequest.hospital_id == hid)
    requests = (
        req_q.filter(PatientRegistrationRequest.status.in_(["pending", "forwarded"]))
        .order_by(PatientRegistrationRequest.created_at.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "patient_id": r.patient_id,
            "patient_name": r.patient.name if r.patient else "Patient",
            "patient_email": r.patient.email if r.patient else "-",
            "preferred_doctor_id": r.preferred_doctor_id,
            "preferred_doctor_name": r.preferred_doctor.name if r.preferred_doctor else "Unassigned",
            "department_preference": r.department_preference,
            "status": r.status,
            "notes": r.notes,
            "created_at": r.created_at.strftime("%Y-%m-%d %H:%M"),
        }
        for r in requests
    ]


# ---------------------------------------------------------------------------
# Medicine Management & Procurement Endpoints
# ---------------------------------------------------------------------------

@app.post("/doctor/medicines/request", response_model=MedicineOut)
def request_medicine_procurement(
    payload: MedicineRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Doctor submits a medicine request to admin for hospital procurement."""
    if current_user.role not in ["doctor", "admin", "hospital_admin"]:
        raise HTTPException(status_code=403, detail="Doctor access required")

    med = Medicine(
        # MULTI-TENANT: medicine inventory is scoped to the requesting user's hospital.
        hospital_id=current_user.hospital_id,
        name=payload.name.strip(),
        generic_name=payload.generic_name.strip() if payload.generic_name else None,
        category=payload.category or "Cardiovascular & Internal Medicine",
        unit=payload.unit or "tablet",
        quantity=payload.quantity,
        requested_by_doctor_id=current_user.id,
        doctor_id=None,
        status="requested",
        notes=payload.notes,
        requested_at=datetime.now(timezone.utc),
    )
    db.add(med)
    db.commit()
    db.refresh(med)

    audit = AuditLog(
        hospital_id=current_user.hospital_id,
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        action="requested_medicine",
        target_type="Medicine",
        target_id=med.id,
        details=json.dumps({
            "medicine_id": med.id,
            "medicine_name": med.name,
            "quantity": med.quantity,
            "doctor_id": current_user.id,
            "doctor_name": current_user.name,
        }),
    )
    db.add(audit)
    db.commit()

    return MedicineOut(
        id=med.id,
        name=med.name,
        generic_name=med.generic_name,
        category=med.category,
        unit=med.unit,
        quantity=med.quantity,
        status=med.status,
        requested_by_doctor_id=med.requested_by_doctor_id,
        requested_by_name=current_user.name,
        doctor_id=med.doctor_id,
        notes=med.notes,
        requested_at=med.requested_at,
        procured_at=med.procured_at,
    )


@app.get("/doctor/medicines", response_model=List[MedicineOut])
def get_doctor_medicines(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists all medicines procured for this doctor and pending requests submitted by this doctor (tenant-scoped)."""
    if current_user.role not in ["doctor", "admin", "hospital_admin"]:
        raise HTTPException(status_code=403, detail="Doctor access required")

    hid = tenant_scope(current_user)
    if current_user.role in ("admin", "hospital_admin"):
        med_q = db.query(Medicine)
        if hid is not None:
            med_q = med_q.filter(Medicine.hospital_id == hid)
        meds = med_q.order_by(Medicine.requested_at.desc()).all()
    else:
        med_q = db.query(Medicine).filter(
            (Medicine.doctor_id == current_user.id) | (Medicine.requested_by_doctor_id == current_user.id)
        )
        if hid is not None:
            med_q = med_q.filter(Medicine.hospital_id == hid)
        meds = med_q.order_by(Medicine.status.asc(), Medicine.name.asc()).all()

    out = []
    for m in meds:
        out.append(
            MedicineOut(
                id=m.id,
                name=m.name,
                generic_name=m.generic_name,
                category=m.category,
                unit=m.unit,
                quantity=m.quantity,
                status=m.status,
                requested_by_doctor_id=m.requested_by_doctor_id,
                requested_by_name=m.requested_by.name if m.requested_by else "Doctor",
                doctor_id=m.doctor_id,
                notes=m.notes,
                requested_at=m.requested_at,
                procured_at=m.procured_at,
            )
        )
    return out


@app.get("/admin/medicine-requests", response_model=List[MedicineOut])
def get_admin_medicine_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Admin endpoint to list all unprocured medicine requests (tenant-scoped)."""
    require_admin(current_user)
    hid = tenant_scope(current_user)

    med_q = db.query(Medicine).filter(Medicine.status == "requested")
    if hid is not None:
        med_q = med_q.filter(Medicine.hospital_id == hid)
    meds = med_q.order_by(Medicine.requested_at.desc()).all()
    out = []
    for m in meds:
        out.append(
            MedicineOut(
                id=m.id,
                name=m.name,
                generic_name=m.generic_name,
                category=m.category,
                unit=m.unit,
                quantity=m.quantity,
                status=m.status,
                requested_by_doctor_id=m.requested_by_doctor_id,
                requested_by_name=m.requested_by.name if m.requested_by else "Doctor",
                doctor_id=m.doctor_id,
                notes=m.notes,
                requested_at=m.requested_at,
                procured_at=m.procured_at,
            )
        )
    return out


@app.post("/admin/medicine-requests/{medicine_id}/procure", response_model=MedicineOut)
def procure_medicine(
    medicine_id: int,
    payload: MedicineProcurePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Admin procures requested medicine and allocates it to the requesting doctor's inventory."""
    require_admin(current_user)

    med = db.query(Medicine).filter(Medicine.id == medicine_id).first()
    if not med:
        raise HTTPException(status_code=404, detail="Medicine request not found")
    # MULTI-TENANT: procurement is scoped to the admin's hospital.
    require_hospital_access(med.hospital_id, current_user)

    med.status = "procured"
    med.quantity = payload.quantity
    med.procured_at = datetime.now(timezone.utc)
    med.doctor_id = med.requested_by_doctor_id  # Link directly to requesting doctor's inventory

    target_doc = db.query(User).filter(User.id == med.doctor_id).first()
    doc_name = target_doc.name if target_doc else f"Doctor #{med.doctor_id}"

    audit = AuditLog(
        hospital_id=med.hospital_id,
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        action="procured_medicine",
        target_type="Medicine",
        target_id=med.id,
        details=json.dumps({
            "medicine_id": med.id,
            "medicine_name": med.name,
            "quantity_procured": med.quantity,
            "allocated_to_doctor_id": med.doctor_id,
            "allocated_to_doctor_name": doc_name,
        }),
    )
    db.add(audit)
    db.commit()
    db.refresh(med)

    return MedicineOut(
        id=med.id,
        name=med.name,
        generic_name=med.generic_name,
        category=med.category,
        unit=med.unit,
        quantity=med.quantity,
        status=med.status,
        requested_by_doctor_id=med.requested_by_doctor_id,
        requested_by_name=doc_name,
        doctor_id=med.doctor_id,
        notes=med.notes,
        requested_at=med.requested_at,
        procured_at=med.procured_at,
    )


@app.post("/doctor/patients/{patient_id}/prescribe")
def prescribe_patient_medicines(
    patient_id: int,
    payload: PrescriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Allows doctor to prescribe available medicines from their inventory to a patient."""
    if current_user.role not in ["doctor", "admin", "hospital_admin"]:
        raise HTTPException(status_code=403, detail="Doctor access required")

    # MULTI-TENANT: patient must be in the same hospital.
    patient = verify_patient_access(patient_id, current_user, db, require_assigned=(current_user.role == "doctor"))

    selected_meds = db.query(Medicine).filter(Medicine.id.in_(payload.medicine_ids)).all()
    if not selected_meds:
        raise HTTPException(status_code=400, detail="No valid medicines selected")
    # MULTI-TENANT: all prescribed medicines must belong to the patient's hospital.
    for m in selected_meds:
        require_hospital_access(m.hospital_id or patient.hospital_id, current_user)

    med_names = [f"{m.name} ({m.generic_name or m.category or 'Rx'})" for m in selected_meds]
    rx_summary = ", ".join(med_names)
    if payload.instructions:
        rx_summary += f" | Instructions: {payload.instructions}"

    return {
        "status": "success",
        "prescription_text": rx_summary,
        "medicines_count": len(selected_meds),
        "medicines": [{"id": m.id, "name": m.name, "category": m.category} for m in selected_meds],
    }


# ---------------------------------------------------------------------------
# Common / Collaborative Doctor Area Endpoints
# ---------------------------------------------------------------------------

@app.get("/doctor/shared-cases")
def get_shared_doctor_cases(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Common Doctor Area: Lists all patients across the network to facilitate
    cross-doctor collaboration, continuity of care, and shared diagnosis review.
    """
    if current_user.role not in ["doctor", "admin", "hospital_admin"]:
        raise HTTPException(status_code=403, detail="Doctor access required")

    # MULTI-TENANT: collaboration/cross-doctor sharing is scoped to the hospital.
    hid = tenant_scope(current_user)
    q = db.query(User).filter(User.role == "patient")
    if hid is not None:
        q = q.filter(User.hospital_id == hid)
    patients = q.order_by(User.name.asc()).all()

    out = []
    for p in patients:
        # Count transfer events in audit logs (scoped to the tenant)
        transfers_count = db.query(AuditLog).filter(
            AuditLog.target_id == p.id,
            AuditLog.action == "reassigned_patient",
        )
        if hid is not None:
            transfers_count = transfers_count.filter(AuditLog.hospital_id == hid)
        transfers_count = transfers_count.count()

        latest_assessment = (
            db.query(PatientAssessment)
            .filter(PatientAssessment.patient_id == p.id)
            .order_by(PatientAssessment.created_at.desc())
            .first()
        )

        latest_diagnosis = (
            db.query(DoctorDiagnosis)
            .filter(DoctorDiagnosis.patient_id == p.id)
            .order_by(DoctorDiagnosis.created_at.desc())
            .first()
        )

        out.append({
            "id": p.id,
            "name": p.name or p.email,
            "email": p.email,
            "age": p.age,
            "sex": p.sex,
            "is_demographics_locked": p.is_demographics_locked,
            "assigned_doctor_id": p.doctor_id,
            "assigned_doctor_name": p.doctor.name if p.doctor else "Unassigned",
            "assigned_doctor_specialty": p.doctor.specialization if p.doctor else None,
            "is_my_patient": p.doctor_id == current_user.id if current_user.role == "doctor" else False,
            "transfers_count": transfers_count,
            "has_shared_history": transfers_count > 0 or latest_diagnosis is not None,
            "latest_risk_level": latest_assessment.risk_level if latest_assessment else "Not Assessed",
            "latest_risk_probability": round(latest_assessment.risk_probability * 100, 1) if latest_assessment else None,
            "latest_diagnosis_title": latest_diagnosis.diagnosis_title if latest_diagnosis else "No formal diagnosis logged",
            "latest_diagnosis_by": latest_diagnosis.doctor.name if (latest_diagnosis and latest_diagnosis.doctor) else None,
        })

    return out


@app.get("/doctor/patients/{patient_id}/collaborative-file")
def get_patient_collaborative_file(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Common Doctor Area: Fetches the entire multi-doctor medical history,
    including transfer audit logs, all diagnoses from different doctors,
    assessments, and blood test results.
    """
    if current_user.role not in ["doctor", "admin", "hospital_admin"]:
        raise HTTPException(status_code=403, detail="Doctor access required")

    # MULTI-TENANT: shared history is scoped to the same hospital.
    patient = verify_patient_access(patient_id, current_user, db, require_assigned=(current_user.role == "doctor"))

    # 1. Fetch Transfer History from AuditLog
    transfer_logs = (
        db.query(AuditLog)
        .filter(AuditLog.target_id == patient.id, AuditLog.action == "reassigned_patient")
        .order_by(AuditLog.created_at.desc())
        .all()
    )
    transfers = []
    for log in transfer_logs:
        details = {}
        try:
            details = json.loads(log.details) if log.details else {}
        except Exception:
            pass
        transfers.append({
            "id": log.id,
            "date": log.created_at.strftime("%Y-%m-%d %H:%M"),
            "actor_role": log.actor_role,
            "actor_name": log.actor.name if log.actor else "System Admin",
            "from_doctor": details.get("old_doctor_name", "Previous Doctor"),
            "to_doctor": details.get("new_doctor_name", "Target Doctor"),
            "reason": details.get("reason", "Inter-departmental care transfer"),
        })

    # 2. Fetch All Diagnoses
    diagnoses_records = (
        db.query(DoctorDiagnosis)
        .filter(DoctorDiagnosis.patient_id == patient.id)
        .order_by(DoctorDiagnosis.created_at.desc())
        .all()
    )
    diagnoses = [
        {
            "id": d.id,
            "doctor_id": d.doctor_id,
            "doctor_name": d.doctor.name if d.doctor else "Attending Physician",
            "doctor_specialty": d.doctor.specialization if d.doctor else "Clinical Specialist",
            "diagnosis_title": d.diagnosis_title,
            "clinical_notes": d.clinical_notes,
            "treatment_plan": d.treatment_plan,
            "prescriptions": d.prescriptions,
            "risk_summary": d.risk_summary,
            "created_at": d.created_at.strftime("%Y-%m-%d %H:%M"),
        }
        for d in diagnoses_records
    ]

    # 3. Fetch All Assessments
    assessments_records = (
        db.query(PatientAssessment)
        .filter(PatientAssessment.patient_id == patient.id)
        .order_by(PatientAssessment.created_at.desc())
        .all()
    )
    assessments = [
        {
            "id": a.id,
            "doctor_id": a.doctor_id,
            "doctor_name": db.query(User.name).filter(User.id == a.doctor_id).scalar() or "Doctor",
            "risk_level": a.risk_level,
            "risk_probability": round(a.risk_probability * 100, 1),
            "age": a.age,
            "sex": a.sex,
            "systolic_bp": a.systolic_bp,
            "diastolic_bp": a.diastolic_bp,
            "cholesterol": a.cholesterol,
            "bmi": a.bmi,
            "st_depression": a.st_depression,
            "chest_pain_type": a.chest_pain_type,
            "top_features": a.triggered_rule_codes,
            "created_at": a.created_at.strftime("%Y-%m-%d %H:%M"),
        }
        for a in assessments_records
    ]

    # 4. Fetch All Blood Tests
    blood_tests_records = (
        db.query(BloodTestResult)
        .filter(BloodTestResult.patient_id == patient.id)
        .order_by(BloodTestResult.created_at.desc())
        .all()
    )
    blood_tests = [
        {
            "id": b.id,
            "fasting_glucose": b.fasting_glucose,
            "hba1c": b.hba1c,
            "hemoglobin": b.hemoglobin,
            "wbc_count": b.wbc_count,
            "platelet_count": b.platelet_count,
            "total_cholesterol": b.total_cholesterol,
            "hdl": b.hdl,
            "ldl": b.ldl,
            "creatinine": b.creatinine,
            "notes": b.notes,
            "created_at": b.created_at.strftime("%Y-%m-%d"),
        }
        for b in blood_tests_records
    ]

    return {
        "patient": {
            "id": patient.id,
            "name": patient.name,
            "email": patient.email,
            "age": patient.age,
            "sex": patient.sex,
            "is_demographics_locked": patient.is_demographics_locked,
            "phone_number": patient.phone_number,
            "emergency_contact_name": patient.emergency_contact_name,
            "emergency_contact_phone": patient.emergency_contact_phone,
            "address": patient.address,
            "assigned_doctor_id": patient.doctor_id,
            "assigned_doctor_name": patient.doctor.name if patient.doctor else "Unassigned",
            "assigned_doctor_specialty": patient.doctor.specialization if patient.doctor else None,
        },
        "transfers": transfers,
        "diagnoses": diagnoses,
        "assessments": assessments,
        "blood_tests": blood_tests,
    }


# ---------------------------------------------------------------------------
# PDF Download Endpoints (Admin, Doctor, and Patient)
# ---------------------------------------------------------------------------

@app.get("/reports/diagnosis/{diagnosis_id}/pdf")
def download_diagnosis_pdf(
    diagnosis_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generates and returns an official PDF medical diagnosis report.
    Accessible by Admin, any Doctor (care collaboration), or the Patient themself.
    """
    diagnosis = db.query(DoctorDiagnosis).filter(DoctorDiagnosis.id == diagnosis_id).first()
    if not diagnosis:
        raise HTTPException(status_code=404, detail="Diagnosis record not found")

    patient = diagnosis.patient
    doctor = diagnosis.doctor

    # MULTI-TENANT: enforce hospital isolation + patient ownership.
    require_hospital_access(diagnosis.hospital_id or (patient.hospital_id if patient else None), current_user)
    if current_user.role == "patient" and current_user.id != patient.id:
        raise HTTPException(status_code=403, detail="Access denied to other patients' reports")

    # Fetch latest clinical assessment for this patient
    latest_assessment = (
        db.query(PatientAssessment)
        .filter(PatientAssessment.patient_id == patient.id)
        .order_by(PatientAssessment.created_at.desc())
        .first()
    )
    assessment_dict = None
    if latest_assessment:
        assessment_dict = {
            "risk_level": latest_assessment.risk_level,
            "risk_probability": latest_assessment.risk_probability,
            "systolic_bp": latest_assessment.systolic_bp,
            "diastolic_bp": latest_assessment.diastolic_bp,
            "max_heart_rate": latest_assessment.max_heart_rate,
            "bmi": latest_assessment.bmi,
            "cholesterol": latest_assessment.cholesterol,
            "st_depression": latest_assessment.st_depression,
            "triggered_rule_codes": latest_assessment.triggered_rule_codes,
            "clinical_recommendations": latest_assessment.clinical_recommendations,
            "created_at": latest_assessment.created_at.strftime("%Y-%m-%d"),
        }

    # Fetch latest blood test
    latest_bt = (
        db.query(BloodTestResult)
        .filter(BloodTestResult.patient_id == patient.id)
        .order_by(BloodTestResult.created_at.desc())
        .first()
    )
    bt_dict = None
    if latest_bt:
        bt_dict = {
            "fasting_glucose": latest_bt.fasting_glucose,
            "hba1c": latest_bt.hba1c,
            "hemoglobin": latest_bt.hemoglobin,
            "total_cholesterol": latest_bt.total_cholesterol,
            "hdl": latest_bt.hdl,
            "ldl": latest_bt.ldl,
            "creatinine": latest_bt.creatinine,
            "notes": latest_bt.notes,
        }

    # Fetch transfer history
    tx_logs = (
        db.query(AuditLog)
        .filter(AuditLog.target_id == patient.id, AuditLog.action == "reassigned_patient")
        .order_by(AuditLog.created_at.asc())
        .all()
    )
    transfer_history = []
    for log in tx_logs:
        try:
            det = json.loads(log.details) if log.details else {}
            transfer_history.append({
                "date": log.created_at.strftime("%Y-%m-%d"),
                "from_doctor": det.get("old_doctor_name", "Previous Doctor"),
                "to_doctor": det.get("new_doctor_name", "Target Doctor"),
                "reason": det.get("reason", "Referral"),
            })
        except Exception:
            pass

    # Fetch latest 5 visit dates dynamically for this patient
    assessments_dates = (
        db.query(PatientAssessment.created_at)
        .filter(PatientAssessment.patient_id == patient.id)
        .order_by(PatientAssessment.created_at.desc())
        .limit(5)
        .all()
    )
    diagnoses_dates = (
        db.query(DoctorDiagnosis.created_at)
        .filter(DoctorDiagnosis.patient_id == patient.id)
        .order_by(DoctorDiagnosis.created_at.desc())
        .limit(5)
        .all()
    )
    all_dates = set([r[0] for r in assessments_dates if r[0]] + [r[0] for r in diagnoses_dates if r[0]])
    sorted_dates = sorted(list(all_dates), reverse=True)[:5]
    past_visits = [{"date": d, "label": "Visit"} for d in sorted_dates]

    patient_dict = {
        "id": patient.id,
        "name": patient.name,
        "email": patient.email,
        "age": patient.age,
        "sex": patient.sex,
        "phone_number": patient.phone_number,
        "emergency_contact_name": patient.emergency_contact_name,
        "emergency_contact_phone": patient.emergency_contact_phone,
    }

    doctor_dict = {
        "id": doctor.id if doctor else 0,
        "name": doctor.name if doctor else "Attending Physician",
        "specialization": doctor.specialization if doctor else "Cardiology & Internal Medicine",
        "license_number": doctor.license_number if doctor else "DOC-REG-2026",
        "email": doctor.email if doctor else "doctor@hospital.com",
    }

    diagnosis_dict = {
        "id": diagnosis.id,
        "diagnosis_title": diagnosis.diagnosis_title,
        "clinical_notes": diagnosis.clinical_notes,
        "treatment_plan": diagnosis.treatment_plan,
        "prescriptions": diagnosis.prescriptions,
        "created_at": diagnosis.created_at,
    }

    # Enhance assessment_dict with rule engine outputs for report
    if assessment_dict:
        # Try to parse triggered_rule_codes and clinical_recommendations from JSON
        try:
            if assessment_dict.get("triggered_rule_codes"):
                # Re-evaluate from the intentionally trimmed assessment data
                # so the report gets the actual per-rule point breakdown.
                report_risk = calculate_rule_based_risk(assessment_dict)
                assessment_dict["triggered_rules"] = report_risk["triggered_rules"]
            if assessment_dict.get("clinical_recommendations"):
                assessment_dict["clinical_recommendations"] = json.loads(assessment_dict["clinical_recommendations"])
        except Exception:
            pass  # Use existing structure if parsing fails

    pdf_bytes = generate_medical_diagnosis_pdf(
        patient_info=patient_dict,
        doctor_info=doctor_dict,
        diagnosis_info=diagnosis_dict,
        assessment_info=assessment_dict,
        blood_test_info=bt_dict,
        past_visits=past_visits,
    )

    filename = f"medical_report_patient_{patient.id}_diag_{diagnosis.id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=\"{filename}\""},
    )


@app.get("/reports/patient/{patient_id}/latest-pdf")
def download_patient_latest_pdf(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Quick download of the latest medical diagnosis report for a patient."""
    if current_user.role == "patient" and current_user.id != patient_id:
        raise HTTPException(status_code=403, detail="Access denied")

    patient = db.query(User).filter(User.id == patient_id, User.role == "patient").first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # MULTI-TENANT: enforce hospital isolation for tenant-scoped roles.
    require_hospital_access(patient.hospital_id, current_user)

    latest_diag = (
        db.query(DoctorDiagnosis)
        .filter(DoctorDiagnosis.patient_id == patient_id)
        .order_by(DoctorDiagnosis.created_at.desc())
        .first()
    )

    if latest_diag:
        return download_diagnosis_pdf(latest_diag.id, db, current_user)

    # If no formal diagnosis recorded yet, create a default summary diagnosis on the fly for export
    doc = patient.doctor or db.query(User).filter(User.role == "doctor").first()
    dummy_diag = {
        "id": 0,
        "diagnosis_title": "Comprehensive Clinical Health & Risk Evaluation",
        "clinical_notes": "Routine cardiovascular risk screening and clinical evaluation. No acute contraindications reported.",
        "treatment_plan": "Maintain balanced dietary regimen, engage in regular aerobic physical activity (150 min/wk), and monitor blood pressure periodically.",
        "prescriptions": "None prescribed at this visit.",
        "created_at": datetime.now(timezone.utc),
    }

    latest_assessment = (
        db.query(PatientAssessment)
        .filter(PatientAssessment.patient_id == patient.id)
        .order_by(PatientAssessment.created_at.desc())
        .first()
    )
    assessment_dict = None
    if latest_assessment:
        assessment_dict = {
            "risk_level": latest_assessment.risk_level,
            "risk_probability": latest_assessment.risk_probability,
            "systolic_bp": latest_assessment.systolic_bp,
            "diastolic_bp": latest_assessment.diastolic_bp,
            "max_heart_rate": latest_assessment.max_heart_rate,
            "bmi": latest_assessment.bmi,
            "cholesterol": latest_assessment.cholesterol,
            "st_depression": latest_assessment.st_depression,
            "triggered_rule_codes": latest_assessment.triggered_rule_codes,
            "clinical_recommendations": latest_assessment.clinical_recommendations,
            "created_at": latest_assessment.created_at.strftime("%Y-%m-%d"),
        }

    latest_bt = (
        db.query(BloodTestResult)
        .filter(BloodTestResult.patient_id == patient.id)
        .order_by(BloodTestResult.created_at.desc())
        .first()
    )
    bt_dict = None
    if latest_bt:
        bt_dict = {
            "fasting_glucose": latest_bt.fasting_glucose,
            "hba1c": latest_bt.hba1c,
            "hemoglobin": latest_bt.hemoglobin,
            "total_cholesterol": latest_bt.total_cholesterol,
            "hdl": latest_bt.hdl,
            "ldl": latest_bt.ldl,
            "creatinine": latest_bt.creatinine,
            "notes": latest_bt.notes,
        }

    # Dynamic latest 5 visits
    assessments_dates = (
        db.query(PatientAssessment.created_at)
        .filter(PatientAssessment.patient_id == patient.id)
        .order_by(PatientAssessment.created_at.desc())
        .limit(5)
        .all()
    )
    diagnoses_dates = (
        db.query(DoctorDiagnosis.created_at)
        .filter(DoctorDiagnosis.patient_id == patient.id)
        .order_by(DoctorDiagnosis.created_at.desc())
        .limit(5)
        .all()
    )
    all_dates = set([r[0] for r in assessments_dates if r[0]] + [r[0] for r in diagnoses_dates if r[0]])
    sorted_dates = sorted(list(all_dates), reverse=True)[:5]
    past_visits = [{"date": d, "label": "Visit"} for d in sorted_dates]

    # Enhance assessment_dict with rule engine outputs for report
    if assessment_dict:
        try:
            if assessment_dict.get("triggered_rule_codes"):
                report_risk = calculate_rule_based_risk(assessment_dict)
                assessment_dict["triggered_rules"] = report_risk["triggered_rules"]
            if assessment_dict.get("clinical_recommendations"):
                assessment_dict["clinical_recommendations"] = json.loads(assessment_dict["clinical_recommendations"])
        except Exception:
            pass

    pdf_bytes = generate_medical_diagnosis_pdf(
        patient_info={
            "id": patient.id,
            "name": patient.name,
            "email": patient.email,
            "age": patient.age,
            "sex": patient.sex,
            "phone_number": patient.phone_number,
            "emergency_contact_name": patient.emergency_contact_name,
            "emergency_contact_phone": patient.emergency_contact_phone,
        },
        doctor_info={
            "id": doc.id if doc else 0,
            "name": doc.name if doc else "Attending Physician",
            "specialization": doc.specialization if doc else "Cardiology",
            "license_number": doc.license_number if doc else "DOC-REG-2026",
            "email": doc.email if doc else "doctor@hospital.com",
        },
        diagnosis_info=dummy_diag,
        assessment_info=assessment_dict,
        blood_test_info=bt_dict,
        past_visits=past_visits,
    )

    filename = f"medical_report_patient_{patient.id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=\"{filename}\""},
    )


@app.post("/doctor/patients/{patient_id}/blood-test", response_model=BloodTestResultOut)
def record_blood_test(
    patient_id: int,
    payload: BloodTestResultCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ["doctor", "admin", "hospital_admin"]:
        raise HTTPException(status_code=403, detail="Doctor access required")

    # MULTI-TENANT: verify access (cross-hospital + assignment) before writing.
    patient = verify_patient_access(patient_id, current_user, db, require_assigned=(current_user.role == "doctor"))

    blood_test = BloodTestResult(
        hospital_id=patient.hospital_id,
        patient_id=patient.id,
        recorded_by_doctor_id=current_user.id,
        hemoglobin=payload.hemoglobin,
        wbc_count=payload.wbc_count,
        platelet_count=payload.platelet_count,
        fasting_glucose=payload.fasting_glucose,
        hba1c=payload.hba1c,
        total_cholesterol=payload.total_cholesterol,
        hdl=payload.hdl,
        ldl=payload.ldl,
        triglycerides=payload.triglycerides,
        creatinine=payload.creatinine,
        notes=payload.notes,
    )
    db.add(blood_test)
    db.commit()
    db.refresh(blood_test)

    # Write AuditLog
    audit = AuditLog(
        hospital_id=patient.hospital_id,
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        action="added_blood_test",
        target_type="BloodTestResult",
        target_id=blood_test.id,
        details=json.dumps({
            "patient_id": patient.id,
            "patient_name": patient.name,
            "blood_test_id": blood_test.id,
            "fasting_glucose": payload.fasting_glucose,
            "hba1c": payload.hba1c,
        }),
    )
    db.add(audit)
    db.commit()

    return blood_test


@app.get("/doctor/patients/{patient_id}/blood-tests", response_model=List[BloodTestResultOut])
def get_patient_blood_tests(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # SECURITY: Use authorization helper to verify access BEFORE data query
    patient = verify_patient_access(patient_id, current_user, db, require_assigned=True)

    tests = (
        db.query(BloodTestResult)
        .filter(BloodTestResult.patient_id == patient_id)
        .order_by(BloodTestResult.created_at.desc())
        .all()
    )
    return tests


# ---------------------------------------------------------------------------
# Patient Endpoints (role: patient)
# ---------------------------------------------------------------------------

@app.put("/patient/profile")
def update_profile(
    profile: PatientProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "patient":
        raise HTTPException(status_code=403, detail="Patient access required")

    if profile.phone_number is not None:
        current_user.phone_number = profile.phone_number
    if profile.emergency_contact_name is not None:
        current_user.emergency_contact_name = profile.emergency_contact_name
    if profile.emergency_contact_phone is not None:
        current_user.emergency_contact_phone = profile.emergency_contact_phone
    if profile.address is not None:
        current_user.address = profile.address

    db.commit()
    return {"status": "success", "message": "Profile updated successfully"}


@app.get("/patient/history")
def get_patient_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "patient":
        raise HTTPException(status_code=403, detail="Patient access required")

    assessments = (
        db.query(PatientAssessment)
        .filter(PatientAssessment.patient_id == current_user.id)
        .order_by(PatientAssessment.created_at.desc())
        .all()
    )
    return [
        {
            "id": a.id,
            "risk_level": a.risk_level,
            "risk_probability": round(a.risk_probability * 100, 1),
            "top_features": a.triggered_rule_codes,
            "age": a.age,
            "systolic_bp": a.systolic_bp,
            "diastolic_bp": a.diastolic_bp,
            "resting_bp": a.systolic_bp if a.systolic_bp is not None else getattr(a, "resting_bp", None),
            "bmi": a.bmi,
            "cholesterol": a.cholesterol,
            "created_at": a.created_at.strftime("%Y-%m-%d %H:%M"),
        }
        for a in assessments
    ]


@app.get("/patient/my-diagnoses")
def get_patient_my_diagnoses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Allows logged-in patients to view their doctor diagnoses and download reports."""
    if current_user.role != "patient":
        raise HTTPException(status_code=403, detail="Patient access required")

    diagnoses = (
        db.query(DoctorDiagnosis)
        .filter(DoctorDiagnosis.patient_id == current_user.id)
        .order_by(DoctorDiagnosis.created_at.desc())
        .all()
    )

    out = []
    for d in diagnoses:
        doc = d.doctor
        out.append({
            "id": d.id,
            "doctor_id": d.doctor_id,
            "doctor_name": doc.name if doc else "Attending Physician",
            "doctor_specialization": doc.specialization if doc else "Clinical Medicine",
            "diagnosis_title": d.diagnosis_title,
            "clinical_notes": d.clinical_notes,
            "treatment_plan": d.treatment_plan,
            "prescriptions": d.prescriptions,
            "risk_summary": d.risk_summary,
            "created_at": d.created_at.strftime("%Y-%m-%d %H:%M"),
        })
    return out


# ---------------------------------------------------------------------------
# Direct /predict Endpoint (with AuditLog integration)
# ---------------------------------------------------------------------------

@app.post("/predict", response_model=PredictionResponse)
def predict_risk(
    payload: PredictionRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    feat_dict = {k: v for k, v in payload.features.dict().items() if v is not None}
    if feat_dict.get("resting_bp") is None and feat_dict.get("systolic_bp") is not None:
        feat_dict["resting_bp"] = feat_dict["systolic_bp"]

    explanation = explain_prediction(feat_dict)
    risk_prob = float(explanation["risk_score"])
    risk_label = str(explanation["risk_label"])

    shap_items = [
        SHAPContribution(
            feature=c["feature"],
            value=c.get("value"),
            shap_value=c["shap_value"],
        )
        for c in explanation["top_contributions"]
    ]

    # Save to PredictionLog
    pred_log = PredictionLog(
        patient_id=payload.patient_id,
        risk_score=risk_prob,
        risk_label=risk_label,
        model_version="1.0.0",
    )
    db.add(pred_log)
    db.commit()
    db.refresh(pred_log)

    # Write AuditLog
    actor_id = current_user.id if current_user else None
    actor_role = current_user.role if current_user else "anonymous"
    audit = AuditLog(
        actor_user_id=actor_id,
        actor_role=actor_role,
        action="predict",
        target_type="PredictionLog",
        target_id=pred_log.id,
        details=json.dumps({
            "patient_id": payload.patient_id,
            "risk_score": risk_prob,
            "risk_label": risk_label,
        }),
    )
    db.add(audit)
    db.commit()

    return PredictionResponse(
        patient_id=payload.patient_id,
        risk_score=risk_prob,
        risk_label=risk_label,
        shap_contributions=shap_items,
        model_version="1.0.0",
        predicted_at=pred_log.predicted_at,
    )
