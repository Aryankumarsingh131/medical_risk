"""
api/schemas.py
--------------
Pydantic models for request validation and response serialisation.

Sections
--------
- Auth
- User management (admin)
- Patient profile & Doctor transfer
- Clinical record / assessment (doctor -> PatientRecord / PatientAssessment)
- Blood test panel (doctor -> BloodTestResult)
- Audit log (actor audit trail)
- Legacy prediction schemas
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class LoginPayload(BaseModel):
    email: str
    password: str
    # SECURITY/MULTI-TENANT: Hospital code scopes the login session
    hospital_code: Optional[str] = None


class HospitalRegisterPayload(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    address: str = Field(..., min_length=2, max_length=300)
    contact_number: str = Field(..., min_length=5, max_length=30)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    hospital_admin_name: str = Field(..., min_length=2, max_length=100)
    hospital_admin_email: str
    hospital_admin_password: str = Field(..., min_length=6)


class HospitalLoginPayload(BaseModel):
    hospital_code: str
    email: str
    password: str


class SuperAdminLoginPayload(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    name: str


class TokenData(BaseModel):
    user_id: Optional[int] = None
    role: Optional[str] = None


# ---------------------------------------------------------------------------
# User management (used by admin endpoints)
# ---------------------------------------------------------------------------

class DoctorCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: str
    password: str = Field(..., min_length=6)
    specialization: Optional[str] = None
    license_number: Optional[str] = None
    degree: Optional[str] = None
    years_of_experience: Optional[int] = None
    certifications: Optional[str] = None
    hospital_code: Optional[str] = None  # Required for hospital_admin registration


class DoctorProfileUpdate(BaseModel):
    name: Optional[str] = None
    specialization: Optional[str] = None
    license_number: Optional[str] = None
    degree: Optional[str] = None
    years_of_experience: Optional[int] = Field(None, ge=0, le=70)
    certifications: Optional[str] = None


class PatientCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: str
    password: str = Field(..., min_length=6)
    doctor_id: Optional[int] = None
    hospital_code: str  # Required for patient registration


class UserOut(BaseModel):
    id: int
    name: Optional[str]
    email: str
    role: str
    is_active: bool
    specialization: Optional[str] = None
    license_number: Optional[str] = None
    degree: Optional[str] = None
    years_of_experience: Optional[int] = None
    certifications: Optional[str] = None
    doctor_id: Optional[int] = None
    assigned_doctor: Optional[str] = None   # convenience: doctor name string
    hospital_id: Optional[int] = None
    hospital_code: Optional[str] = None
    hospital_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Patient profile & Doctor transfer
# ---------------------------------------------------------------------------

class DoctorTransferRequest(BaseModel):
    """Payload to transfer / reassign a patient to a new doctor."""
    new_doctor_id: int = Field(..., description="ID of the doctor to assign the patient to")
    reason: Optional[str] = Field(None, description="Clinical reason or notes for the transfer")


class DoctorTransferResponse(BaseModel):
    """Response returned after transferring / reassigning a patient to a doctor."""
    status: str = "success"
    message: str
    patient_id: int
    doctor_id: Optional[int] = None
    doctor_name: Optional[str] = None


class PatientProfile(BaseModel):
    """Patient profile representation with assigned doctor ID and locked demographics."""
    id: int
    name: Optional[str]
    email: str
    doctor_id: Optional[int] = None
    assigned_doctor: Optional[str] = None
    age: Optional[float] = None
    sex: Optional[float] = None
    is_demographics_locked: bool = False
    phone_number: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    address: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PatientProfileUpdate(BaseModel):
    """Fields allowed during patient self-profile update."""
    phone_number: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    address: Optional[str] = None
    doctor_id: Optional[int] = None


# ---------------------------------------------------------------------------
# Doctor Diagnosis & Clinical Notes
# ---------------------------------------------------------------------------

class DoctorDiagnosisCreate(BaseModel):
    """Payload to create or record a formal doctor diagnosis note."""
    diagnosis_title: str = Field(..., min_length=2, max_length=200)
    clinical_notes: str = Field(..., min_length=2)
    treatment_plan: Optional[str] = None
    prescriptions: Optional[str] = None
    risk_summary: Optional[str] = None


class DoctorDiagnosisOut(BaseModel):
    """Serialized doctor diagnosis response."""
    id: int
    patient_id: int
    doctor_id: int
    doctor_name: Optional[str] = None
    doctor_specialization: Optional[str] = None
    doctor_license: Optional[str] = None
    patient_name: Optional[str] = None
    diagnosis_title: str
    clinical_notes: str
    treatment_plan: Optional[str] = None
    prescriptions: Optional[str] = None
    risk_summary: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Clinical Record / Assessment (doctor -> PatientRecord / PatientAssessment)
# resting_bp replaced with systolic_bp and diastolic_bp (both integers)
# ---------------------------------------------------------------------------

class DoctorPatientCreate(BaseModel):
    """Payload used by doctors to register a new patient directly from the doctor dashboard."""
    name: str = Field(..., min_length=2, max_length=100)
    email: str
    password: Optional[str] = "Demo@123"
    age: Optional[float] = None
    sex: Optional[float] = None
    phone_number: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    address: Optional[str] = None


class PatientRecordCreate(BaseModel):
    """Inputs submitted by a doctor to create a patient clinical record."""
    age: Optional[float] = Field(None, ge=0, le=130)
    sex: Optional[float] = Field(None, description="1=Male, 0=Female")
    systolic_bp: Optional[int] = Field(None, ge=50, le=300, description="Systolic blood pressure (mmHg)")
    diastolic_bp: Optional[int] = Field(None, ge=30, le=200, description="Diastolic blood pressure (mmHg)")
    cholesterol: Optional[float] = Field(None, ge=0, le=800)
    fasting_blood_sugar: Optional[float] = Field(None, description="1 if >120 mg/dL else 0")
    max_heart_rate: Optional[float] = Field(None, ge=30, le=260)
    bmi: Optional[float] = Field(None, ge=10.0, le=90.0)
    smoking: Optional[float] = Field(None, description="1=smoker / former, 0=non-smoker")
    
    # Clinical Signs & Comorbidities
    chest_pain_type: Optional[float] = Field(None, description="0=typical, 1=atypical, 2=non-anginal, 3=asymptomatic")
    exercise_angina: Optional[float] = Field(None, description="1=yes, 0=no")
    st_depression: Optional[float] = Field(None, ge=0.0, le=10.0, description="ST depression (ECG) in mm")
    hypertension: Optional[float] = Field(None, description="1=yes, 0=no")
    diabetes: Optional[float] = Field(None, description="1=yes, 0=no")
    prior_medical_events: Optional[str] = None


# Aliases for AssessmentCreate and PatientRecordInput
AssessmentCreate = PatientRecordCreate
PatientRecordInput = PatientRecordCreate


class PatientRecordOut(BaseModel):
    """Serialized patient clinical record with systolic_bp and diastolic_bp."""
    id: int
    patient_id: int
    doctor_id: Optional[int] = None
    age: Optional[float] = None
    sex: Optional[float] = None
    systolic_bp: Optional[int] = None
    diastolic_bp: Optional[int] = None
    cholesterol: Optional[float] = None
    fasting_blood_sugar: Optional[float] = None
    max_heart_rate: Optional[float] = None
    bmi: Optional[float] = None
    smoking: Optional[float] = None
    chest_pain_type: Optional[float] = None
    exercise_angina: Optional[float] = None
    st_depression: Optional[float] = None
    hypertension: Optional[float] = None
    diabetes: Optional[float] = None
    prior_medical_events: Optional[str] = None
    risk_level: str
    risk_probability: float
    triggered_rule_codes: Optional[str] = None
    clinical_recommendations: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Aliases for AssessmentOut and PatientRecord
AssessmentOut = PatientRecordOut
PatientRecord = PatientRecordOut


class RiskReason(BaseModel):
    """A single human-readable reason for a risk contribution."""
    feature: str
    label: str
    value: Optional[float] = None
    shap_value: float
    impact: str
    direction: str
    reason: str


class RiskCategory(BaseModel):
    """Risk tier with visual color coding."""
    label: str           # 'High Risk' | 'Moderate Risk' | 'Low Risk'
    percentage: float    # 0-100
    tier: str            # 'high' | 'moderate' | 'low'
    color: str           # hex color


class AssessmentResult(BaseModel):
    """Returned immediately after an assessment / ML inference."""
    risk_level: str
    risk_probability: float
    risk_percentage: float
    risk_category: RiskCategory
    top_features: List[str]        # legacy string list
    reasons: List[RiskReason]      # structured clinical reasons
    recommendations: List[str]     # actionable advice
    assessed_at: datetime
    auto_diagnosis_suggestion: Optional[str] = None  # AI-generated diagnosis heading


# ---------------------------------------------------------------------------
# Blood Test Panel (doctor -> BloodTestResult, independent of PatientRecord)
# ---------------------------------------------------------------------------

class BloodTestResultCreate(BaseModel):
    """Lab panel data for complete blood count, metabolic, and renal panels."""
    # Complete Blood Count (CBC)
    hemoglobin: Optional[float] = Field(None, ge=0, le=25, description="Hemoglobin (g/dL)")
    wbc_count: Optional[float] = Field(None, ge=0, le=100, description="WBC count (10^3/uL)")
    platelet_count: Optional[float] = Field(None, ge=0, le=2000, description="Platelet count (10^3/uL)")

    # Metabolic panel
    fasting_glucose: Optional[float] = Field(None, ge=0, le=1000, description="Fasting glucose (mg/dL)")
    hba1c: Optional[float] = Field(None, ge=0, le=20, description="HbA1c (%)")
    total_cholesterol: Optional[float] = Field(None, ge=0, le=1000, description="Total cholesterol (mg/dL)")
    hdl: Optional[float] = Field(None, ge=0, le=200, description="HDL cholesterol (mg/dL)")
    ldl: Optional[float] = Field(None, ge=0, le=500, description="LDL cholesterol (mg/dL)")
    triglycerides: Optional[float] = Field(None, ge=0, le=2000, description="Triglycerides (mg/dL)")

    # Renal panel
    creatinine: Optional[float] = Field(None, ge=0, le=50, description="Serum creatinine (mg/dL)")

    notes: Optional[str] = None


# Alias for BloodTestCreate
BloodTestCreate = BloodTestResultCreate


class BloodTestResultOut(BaseModel):
    """Serialized BloodTestResult schema."""
    id: int
    patient_id: int
    recorded_by_doctor_id: Optional[int] = None
    hemoglobin: Optional[float] = None
    wbc_count: Optional[float] = None
    platelet_count: Optional[float] = None
    fasting_glucose: Optional[float] = None
    hba1c: Optional[float] = None
    total_cholesterol: Optional[float] = None
    hdl: Optional[float] = None
    ldl: Optional[float] = None
    triglycerides: Optional[float] = None
    creatinine: Optional[float] = None
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Aliases for BloodTestOut and BloodTestResult
BloodTestOut = BloodTestResultOut
BloodTestResult = BloodTestResultOut


# ---------------------------------------------------------------------------
# Audit Log (immutable event trail)
# ---------------------------------------------------------------------------

class AuditLogCreate(BaseModel):
    """Payload to create an audit log event."""
    actor_user_id: Optional[int] = None
    actor_role: str = Field(..., description="Role of the actor e.g. admin, doctor, patient")
    action: str = Field(..., description="Action e.g. created_patient, created_doctor, reassigned_patient, added_record, added_blood_test")
    target_type: Optional[str] = Field(None, description="Target entity type e.g. User, PatientRecord, BloodTestResult")
    target_id: Optional[int] = None
    details: Optional[Union[str, Dict[str, Any]]] = None


class AuditLogOut(BaseModel):
    """Serialized AuditLog representation."""
    id: int
    actor_user_id: Optional[int] = None
    actor_role: str
    action: str
    target_type: Optional[str] = None
    target_id: Optional[int] = None
    details: Optional[str] = None   # JSON string
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Clinical Drafts (Guest patient evaluations & saved drafts)
# ---------------------------------------------------------------------------

class ClinicalDraftCreate(BaseModel):
    draft_name: Optional[str] = "Guest Patient Draft"
    guest_identifier: Optional[str] = None
    data: Dict[str, Any]
    risk_level: Optional[str] = None
    risk_probability: Optional[float] = None


class ClinicalDraftOut(BaseModel):
    id: int
    doctor_id: int
    draft_name: str
    guest_identifier: Optional[str] = None
    raw_data_json: str
    risk_level: Optional[str] = None
    risk_probability: Optional[float] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DraftConvertRequest(BaseModel):
    patient_name: str = Field(..., min_length=2, max_length=100)
    patient_email: str
    password: Optional[str] = "Demo@123"
    phone_number: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    address: Optional[str] = None


# ---------------------------------------------------------------------------
# Medicine Schemas (doctor requests + admin procurement)
# ---------------------------------------------------------------------------

class MedicineRequest(BaseModel):
    """Doctor submits a request for medicine procurement."""
    name: str = Field(..., min_length=1, max_length=150)
    generic_name: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    quantity: int = Field(1, ge=1)
    notes: Optional[str] = None


class MedicineOut(BaseModel):
    """Serialized medicine inventory item."""
    id: int
    name: str
    generic_name: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    quantity: int
    status: str                             # requested | procured
    requested_by_doctor_id: Optional[int] = None
    requested_by_name: Optional[str] = None
    doctor_id: Optional[int] = None
    notes: Optional[str] = None
    requested_at: datetime
    procured_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MedicineProcurePayload(BaseModel):
    """Admin payload to procure a requested medicine."""
    quantity: int = Field(1, ge=1)


class PrescriptionCreate(BaseModel):
    """Doctor prescribes medicines to a patient (links medicine IDs)."""
    medicine_ids: List[int]
    instructions: Optional[str] = None


# ---------------------------------------------------------------------------
# Patient Self-Registration & Request Queue
# ---------------------------------------------------------------------------

class PatientSelfRegister(BaseModel):
    """New patient self-registers — doctor assignment happens via the request queue."""
    name: str = Field(..., min_length=2, max_length=100)
    email: str
    password: str = Field(..., min_length=6)
    preferred_doctor_id: Optional[int] = None
    department_preference: Optional[str] = None
    # MULTI-TENANT: Hospital code the patient belongs to. Defaults to CITY01.
    hospital_code: Optional[str] = Field("CITY01", min_length=4, max_length=10)


class PatientRegistrationRequestOut(BaseModel):
    """Serialized patient registration request for the doctor's request queue."""
    id: int
    patient_id: int
    patient_name: Optional[str] = None
    patient_email: Optional[str] = None
    preferred_doctor_id: Optional[int] = None
    preferred_doctor_name: Optional[str] = None
    department_preference: Optional[str] = None
    status: str
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ForwardPatientRequest(BaseModel):
    """Doctor forwards a patient request to a different doctor."""
    new_doctor_id: int
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Legacy prediction schemas (kept for backward compat)
# ---------------------------------------------------------------------------

class PatientFeatures(BaseModel):
    """Canonical patient clinical features for direct /predict usage."""
    age: Optional[float] = Field(None, ge=0, le=130)
    sex: Optional[float] = None
    systolic_bp: Optional[int] = Field(None, ge=50, le=300)
    diastolic_bp: Optional[int] = Field(None, ge=30, le=200)
    resting_bp: Optional[float] = Field(None, ge=0, le=350)
    temperature: Optional[float] = Field(None, ge=30.0, le=45.0)
    max_heart_rate: Optional[float] = Field(None, ge=30, le=260)
    bmi: Optional[float] = Field(None, ge=10.0, le=90.0)
    cholesterol: Optional[float] = Field(None, ge=0, le=800)
    fasting_blood_sugar: Optional[float] = None
    st_depression: Optional[float] = None
    smoking: Optional[float] = None
    alcohol: Optional[float] = None
    drug: Optional[float] = None
    speech: Optional[float] = None
    movement: Optional[float] = None
    active_diagnosis: Optional[float] = None
    prior_medical_events: Optional[float] = None
    current_medication_list: Optional[float] = None
    chest_pain_type: Optional[float] = None
    exercise_angina: Optional[float] = None
    hypertension: Optional[float] = None
    diabetes: Optional[float] = None

    class Config:
        extra = "allow"


class PredictionRequest(BaseModel):
    patient_id: Optional[str] = None
    features: PatientFeatures


class SHAPContribution(BaseModel):
    feature: str
    value: Optional[float] = None
    shap_value: float


class PredictionResponse(BaseModel):
    patient_id: Optional[str]
    risk_score: float = Field(..., ge=0.0, le=1.0)
    risk_label: str
    shap_contributions: List[SHAPContribution]
    model_version: str
    predicted_at: datetime


class PredictionRecord(BaseModel):
    id: int
    patient_id: Optional[str]
    risk_score: float
    risk_label: str
    model_version: str
    predicted_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Hospital Directory & Emergency Availability
# ---------------------------------------------------------------------------

class HospitalDoctorAvailabilityOut(BaseModel):
    id: int
    hospital_id: int
    specialization: str
    available_doctors: int

    class Config:
        from_attributes = True


class HospitalOut(BaseModel):
    id: int
    name: str
    hospital_code: str
    address: str
    contact_number: str
    latitude: float
    longitude: float
    available_beds: int
    icu_beds_available: int
    ventilators_available: int
    blood_bank_available: bool
    emergency_services_available: bool
    is_active: bool
    subscription_tier: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    doctor_availability: List[HospitalDoctorAvailabilityOut] = []
    distance_km: Optional[float] = None

    class Config:
        from_attributes = True


class HospitalCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    address: str = Field(..., min_length=2, max_length=300)
    contact_number: str = Field(..., min_length=5, max_length=30)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    available_beds: int = Field(default=0, ge=0)
    icu_beds_available: int = Field(default=0, ge=0)
    ventilators_available: int = Field(default=0, ge=0)
    blood_bank_available: bool = False
    emergency_services_available: bool = True
    # hospital_code will be auto-generated


class HospitalUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=200)
    address: Optional[str] = Field(default=None, min_length=2, max_length=300)
    contact_number: Optional[str] = Field(default=None, min_length=5, max_length=30)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    available_beds: Optional[int] = Field(default=None, ge=0)
    icu_beds_available: Optional[int] = Field(default=None, ge=0)
    ventilators_available: Optional[int] = Field(default=None, ge=0)
    blood_bank_available: Optional[bool] = None
    emergency_services_available: Optional[bool] = None


class HospitalDoctorAvailabilityCreate(BaseModel):
    specialization: str = Field(..., min_length=2, max_length=100)
    available_doctors: int = Field(default=0, ge=0)
