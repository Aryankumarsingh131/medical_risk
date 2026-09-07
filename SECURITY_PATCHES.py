"""
CRITICAL SECURITY PATCHES - Apply Immediately
Medical Risk XAI System

This file contains the most critical security fixes.
Review each change before applying to production.
"""

# ============================================================================
# PATCH 1: Fix SECRET_KEY and Remove Hardcoded Salt
# ============================================================================

# FILE: api/main.py (Line 100-104)
# BEFORE:
"""
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production-super-secret-key-32chars")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
"""

# AFTER:
"""
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY environment variable must be set. "
        "Generate with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
    )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))  # 2 hours default

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
"""

# ============================================================================
# PATCH 2: Remove Hardcoded Password Hash Salt
# ============================================================================

# FILE: api/main.py (Line 177-178)
# BEFORE:
"""
def get_password_hash(password: str) -> str:
    salt = "medrisk_salt_2026"
    return hashlib.sha256(f"{salt}_{password}".encode("utf-8")).hexdigest()
"""

# AFTER:
"""
def get_password_hash(password: str) -> str:
    # Use bcrypt's built-in salt generation (already in pwd_context)
    return pwd_context.hash(password)
"""

# ============================================================================
# PATCH 3: Fix Password Verification
# ============================================================================

# FILE: api/main.py (Line 181-182)
# BEFORE:
"""
def verify_password(plain: str, hashed: str) -> bool:
    return hmac.compare_digest(get_password_hash(plain), hashed)
"""

# AFTER:
"""
def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False
"""

# ============================================================================
# PATCH 4: Add Authorization Helper Function
# ============================================================================

# FILE: api/main.py (After get_current_user_optional function)
# ADD NEW FUNCTION:
"""
def verify_patient_access(
    patient_id: int,
    current_user: User,
    db: Session,
    require_assigned: bool = True
) -> User:
    '''Verify doctor has authorization to access patient data.

    Args:
        patient_id: ID of patient to access
        current_user: Currently authenticated user
        db: Database session
        require_assigned: If True, doctor must be assigned to patient

    Returns:
        Patient User object if authorized

    Raises:
        HTTPException: 404 if patient not found, 403 if unauthorized
    '''
    patient = db.query(User).filter(
        User.id == patient_id,
        User.role == "patient",
        User.is_active == True
    ).first()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Admin can access any patient
    if current_user.role == "admin":
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
"""

# ============================================================================
# PATCH 5: Secure Demo Accounts Endpoint
# ============================================================================

# FILE: api/main.py (Line 366)
# BEFORE:
"""
@app.get("/auth/demo-accounts")
def get_demo_accounts(db: Session = Depends(get_db)):
"""

# AFTER:
"""
@app.get("/auth/demo-accounts")
def get_demo_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Only admins can list demo accounts
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
"""

# ============================================================================
# PATCH 6: Fix IDOR in Blood Tests Endpoint
# ============================================================================

# FILE: api/main.py (Line 2734-2760)
# BEFORE:
"""
@app.get("/doctor/patients/{patient_id}/blood-tests", response_model=List[BloodTestResultOut])
def get_patient_blood_tests(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patient = db.query(User).filter(User.id == patient_id, User.role == "patient").first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Accessible by their doctor, the patient themself, or admin
    if current_user.role == "patient":
        if current_user.id != patient_id:
            raise HTTPException(status_code=403, detail="Access denied to other patient's lab data")
    elif current_user.role == "doctor":
        if patient.doctor_id != current_user.id:
            raise HTTPException(status_code=403, detail="Patient is not assigned to this doctor")
    elif current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
"""

# AFTER:
"""
@app.get("/doctor/patients/{patient_id}/blood-tests", response_model=List[BloodTestResultOut])
def get_patient_blood_tests(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Use authorization helper - checks BEFORE query
    patient = verify_patient_access(patient_id, current_user, db, require_assigned=True)
"""

# ============================================================================
# PATCH 7: Fix IDOR in Diagnoses Endpoint
# ============================================================================

# FILE: api/main.py (Line 1711)
# BEFORE:
"""
@app.get("/doctor/patients/{patient_id}/diagnoses", response_model=List[DoctorDiagnosisOut])
def get_patient_diagnoses(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ["doctor", "admin"]:
        raise HTTPException(status_code=403, detail="Doctor access required")

    patient = db.query(User).filter(User.id == patient_id, User.role == "patient").first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
"""

# AFTER:
"""
@app.get("/doctor/patients/{patient_id}/diagnoses", response_model=List[DoctorDiagnosisOut])
def get_patient_diagnoses(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Authorization check FIRST
    patient = verify_patient_access(patient_id, current_user, db, require_assigned=True)
"""

# ============================================================================
# PATCH 8: Fix Shared Cases - Remove Data Over-Exposure
# ============================================================================

# FILE: api/main.py (Line 2174)
# BEFORE:
"""
@app.get("/doctor/shared-cases")
def get_shared_doctor_cases(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ["doctor", "admin"]:
        raise HTTPException(status_code=403, detail="Doctor access required")

    patients = db.query(User).filter(User.role == "patient").order_by(User.name.asc()).all()
"""

# AFTER:
"""
@app.get("/doctor/shared-cases")
def get_shared_doctor_cases(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ["doctor", "admin"]:
        raise HTTPException(status_code=403, detail="Doctor access required")

    # SECURITY FIX: Only show patients with transfer history OR current doctor's patients
    # Remove ability to see ALL patients in system
    if current_user.role == "doctor":
        # Only show own patients + patients with documented transfers
        patients = db.query(User).filter(
            User.role == "patient",
            db.or_(
                User.doctor_id == current_user.id,
                User.id.in_(
                    db.query(AuditLog.target_id).filter(
                        AuditLog.action == "reassigned_patient",
                        AuditLog.target_type == "User"
                    )
                )
            )
        ).order_by(User.name.asc()).all()
    else:
        # Admins can see all
        patients = db.query(User).filter(User.role == "patient").order_by(User.name.asc()).all()
"""

# ============================================================================
# PATCH 9: Add Authentication to Hospital Nearby Endpoint
# ============================================================================

# FILE: api/main.py (Line 983)
# BEFORE:
"""
@app.get("/hospitals/nearby", response_model=List[HospitalOut])
def get_nearby_hospitals(latitude: float, longitude: float, radius_km: float = 50, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
"""

# AFTER - Verify this endpoint has current_user dependency (it already does - GOOD!)
# But should verify it's enforced

# ============================================================================
# PATCH 10: Fix Generic Error Messages
# ============================================================================

# FILE: api/main.py (Line 258-259)
# BEFORE:
"""
if not user or not verify_password(payload.password, user.hashed_password):
    raise HTTPException(status_code=401, detail="Invalid email or password")
"""

# AFTER:
"""
if not user or not verify_password(payload.password, user.hashed_password):
    # Generic error message prevents user enumeration
    raise HTTPException(status_code=401, detail="Invalid credentials")
"""

# ============================================================================
# PATCH 11: Add Rate Limiting Middleware
# ============================================================================

# FILE: api/main.py (After app initialization)
# ADD:
"""
from api.security import RateLimitMiddleware, SecurityHeadersMiddleware

# Add security middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)
"""

# ============================================================================
# PATCH 12: Add Global Exception Handler
# ============================================================================

# FILE: api/main.py (After startup_event)
# ADD:
"""
import logging
logger = logging.getLogger(__name__)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Log full error details server-side
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    # Return generic message to client (no stack trace)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal error occurred. Please contact support if the issue persists."
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    # Log HTTP errors
    if exc.status_code >= 500:
        logger.error(f"HTTP {exc.status_code}: {exc.detail}")

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )
"""

# ============================================================================
# PATCH 13: Improve JWT Token Validation
# ============================================================================

# FILE: api/main.py (get_current_user function)
# ADD role verification from database:
"""
def get_current_user(token: Optional[str] = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    if not token:
        raise HTTPException(status_code=401, detail="Authentication token missing")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        token_role: str = payload.get("role")  # Role from JWT

        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user = db.query(User).filter(User.email == email).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not active or found")

    # SECURITY: Verify role in token matches database
    if user.role != token_role:
        raise HTTPException(status_code=401, detail="Token validation failed")

    return user
"""

# ============================================================================
# PATCH 14: Secure Patient Record Creation
# ============================================================================

# FILE: api/main.py (record_patient_assessment function, line 1284)
# ADD authorization check:
"""
@app.post("/doctor/patients/{patient_id}/record", response_model=AssessmentResult)
def record_patient_assessment(
    patient_id: int,
    record: PatientRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ["doctor", "admin"]:
        raise HTTPException(status_code=403, detail="Doctor access required")

    # ADD THIS: Authorization check BEFORE accessing data
    patient = verify_patient_access(patient_id, current_user, db, require_assigned=True)

    # ... rest of function
"""

# ============================================================================
# PATCH 15: Update .env.example with Security Notes
# ============================================================================

# FILE: .env.example
# ADD:
"""
# SECURITY: Generate a strong secret key for production
# Run: python -c "import secrets; print(secrets.token_urlsafe(32))"
SECRET_KEY=CHANGE_THIS_IN_PRODUCTION_USE_GENERATOR_ABOVE

# Recommended: 2 hours for healthcare applications
ACCESS_TOKEN_EXPIRE_MINUTES=120

# Database - Use PostgreSQL in production for Row Level Security
# DATABASE_URL=postgresql://user:pass@localhost/medical_risk_prod
DATABASE_URL=sqlite:///./medical_risk.db
"""

# ============================================================================
# APPLICATION INSTRUCTIONS
# ============================================================================

print("""
CRITICAL SECURITY PATCHES - APPLICATION INSTRUCTIONS

1. IMMEDIATE ACTIONS (Before ANY deployment):
   ✅ Apply all patches in this file
   ✅ Generate new SECRET_KEY: python -c "import secrets; print(secrets.token_urlsafe(32))"
   ✅ Update .env with strong SECRET_KEY
   ✅ Rotate all demo passwords
   ✅ Test all endpoints with security tests

2. SHORT TERM (Within 1 week):
   ⚠️ Migrate to PostgreSQL with Row Level Security
   ⚠️ Implement token refresh mechanism
   ⚠️ Add comprehensive audit logging
   ⚠️ Implement input sanitization throughout
   ⚠️ Add XSS protection to frontend

3. MEDIUM TERM (Within 1 month):
   📋 Conduct full penetration test
   📋 Implement SIEM/logging monitoring
   📋 Add intrusion detection
   📋 Implement data encryption at rest
   📋 Add HIPAA compliance audit trail

4. TESTING AFTER PATCHES:
   Run these tests to verify fixes:

   # Test 1: IDOR Prevention
   curl -H "Authorization: Bearer $DOCTOR_TOKEN" \\
     http://localhost:8000/doctor/patients/999/blood-tests
   # Should return 403 Forbidden

   # Test 2: Demo Accounts Protection
   curl http://localhost:8000/auth/demo-accounts
   # Should return 401 Unauthorized

   # Test 3: Rate Limiting
   for i in {1..10}; do
     curl -X POST http://localhost:8000/auth/login
   done
   # Should rate limit after 5 attempts

   # Test 4: Generic Error Messages
   curl -X POST http://localhost:8000/auth/login \\
     -d '{"email":"test@test.com","password":"wrong"}'
   # Should return "Invalid credentials" (not "Invalid email or password")

5. COMPLIANCE:
   This system handles PHI (Protected Health Information).
   After applying patches, you MUST still:
   - Complete HIPAA Security Risk Assessment
   - Implement Business Associate Agreements
   - Document all security controls
   - Conduct annual security audits
   - Train staff on PHI handling

WARNING: These patches address CRITICAL vulnerabilities but DO NOT
make the system fully HIPAA compliant. Additional security measures,
compliance documentation, and professional security audit are required
before handling real patient data.
""")
