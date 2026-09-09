import React, { useState, useEffect } from "react";
import { useAuth } from "./AuthContext";
import { apiRequest } from "./api";
import { useToast } from "./ToastContext";
import PasswordToggle from "./PasswordToggle";
import { SkeletonList } from "./Skeleton";

const DEMO_USERS = [
  { id: 1, label: "Super Admin (Platform)", email: "superadmin@medrisk.com", role: "super_admin", hospital_code: "" },
  // City Care (CITY01)
  { id: 2, label: "City Care Admin", email: "admin.city01@hospital.com", role: "hospital_admin", hospital_code: "CITY01" },
  { id: 3, label: "Dr. Sharma (Cardiology)", email: "dr.sharma.city01@hospital.com", role: "doctor", hospital_code: "CITY01" },
  { id: 4, label: "Dr. Mehta (Internal Med)", email: "dr.mehta.city01@hospital.com", role: "doctor", hospital_code: "CITY01" },
  { id: 5, label: "Dr. Khan (Endocrinology)", email: "dr.khan.city01@hospital.com", role: "doctor", hospital_code: "CITY01" },
  { id: 8, label: "Arjun (Patient)", email: "patient.arjun.city01@hospital.com", role: "patient", hospital_code: "CITY01" },
  { id: 10, label: "Rohan (Patient)", email: "patient.rohan.city01@hospital.com", role: "patient", hospital_code: "CITY01" },
  // Apollo Heart & Emergency (APOLO2)
  { id: 7, label: "Apollo Admin", email: "admin.apolo2@hospital.com", role: "hospital_admin", hospital_code: "APOLO2" },
  { id: 6, label: "Dr. Rao (Cardiology)", email: "dr.rao.apolo2@hospital.com", role: "doctor", hospital_code: "APOLO2" },
  { id: 11, label: "Dr. Iyer (Internal Med)", email: "dr.iyer.apolo2@hospital.com", role: "doctor", hospital_code: "APOLO2" },
  { id: 12, label: "Dr. Menon (Endocrinology)", email: "dr.menon.apolo2@hospital.com", role: "doctor", hospital_code: "APOLO2" },
  { id: 13, label: "Pooja (Patient)", email: "patient.pooja.apolo2@hospital.com", role: "patient", hospital_code: "APOLO2" },
  { id: 14, label: "Siddharth (Patient)", email: "patient.siddharth.apolo2@hospital.com", role: "patient", hospital_code: "APOLO2" },
];

const formatDemoUserLabel = (user) => {
  if (user?.label) return user.label;
  const name = user?.name || user?.email || "User";
  const roleText = user?.role === "doctor" ? "Doctor" : user?.role === "patient" ? "Patient" : user?.role === "hospital_admin" ? "Hospital Admin" : user?.role === "super_admin" ? "Super Admin" : "Admin";
  const idText = user?.id ? ` ID ${user.id}` : "";
  return `${roleText}${idText}: ${name}`;
};

export default function Login({ onBackToLanding } = {}) {
  const { login, register } = useAuth();
  const toast = useToast();
  const [activeMode, setActiveMode] = useState("login"); // 'login' | 'register'
  const [demoUsers, setDemoUsers] = useState(DEMO_USERS);
  const [demoLoading, setDemoLoading] = useState(true);

  // Login form state
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [hospitalCode, setHospitalCode] = useState("CITY01");

  // Self registration state
  const [regForm, setRegForm] = useState({
    name: "",
    email: "",
    password: "",
    date_of_birth: "",
    sex: "1",
    phone_number: "",
    emergency_contact_name: "",
    emergency_contact_phone: "",
    address: "",
    hospital_code: "CITY01",
    preferred_doctor_id: "",
    department_preference: "Cardiology",
    showVitals: false,
    systolic_bp: "",
    diastolic_bp: "",
    cholesterol: "",
    bmi: "",
    fasting_blood_sugar: "0",
    max_heart_rate: "",
    smoking: "0",
    hypertension: "0",
    diabetes: "0",
  });
  const [availableDoctors, setAvailableDoctors] = useState([]);

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const calculateAge = (dobString) => {
    if (!dobString) return null;
    const dob = new Date(dobString);
    if (isNaN(dob.getTime())) return null;
    const today = new Date();
    let age = today.getFullYear() - dob.getFullYear();
    const m = today.getMonth() - dob.getMonth();
    if (m < 0 || (m === 0 && today.getDate() < dob.getDate())) {
      age--;
    }
    return age >= 0 ? age : 0;
  };

  // Load available doctors scoped to the hospital code being registered into.
  useEffect(() => {
    const code = regForm.hospital_code;
    const qs = code ? `?hospital_code=${encodeURIComponent(code.trim().toUpperCase())}` : "";
    apiRequest(`/doctor/all-doctors${qs}`)
      .then((docs) => setAvailableDoctors(docs || []))
      .catch(() => {});
  }, [regForm.hospital_code]);

  useEffect(() => {
    setDemoLoading(true);
    apiRequest("/auth/demo-accounts")
      .then((users) => {
        if (Array.isArray(users) && users.length > 0) {
          const normalized = users.map((user) => ({
            ...user,
            label: formatDemoUserLabel(user),
          }));
          setDemoUsers(normalized);
        }
      })
      .catch(() => {
        setDemoUsers(DEMO_USERS);
      })
      .finally(() => setDemoLoading(false));
  }, []);

  const handleDemoSelect = (e) => {
    const selectedEmail = e.target.value;
    if (!selectedEmail) return;
    const selected = demoUsers.find((u) => u.email === selectedEmail);
    setEmail(selectedEmail);
    setPassword("Demo@123");
    if (selected?.role === "super_admin") {
      setHospitalCode("");
    } else {
      setHospitalCode(selected?.hospital_code || "");
    }
    setError("");
  };

  const handleLoginSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password, hospitalCode);
      toast.success("Signed in successfully!");
    } catch (err) {
      setError(err.message || "Invalid credentials. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleRegisterSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const computedAge = calculateAge(regForm.date_of_birth);
      await register({
        name: regForm.name,
        email: regForm.email,
        password: regForm.password,
        hospital_code: regForm.hospital_code,
        date_of_birth: regForm.date_of_birth || null,
        age: computedAge,
        sex: regForm.sex !== "" ? parseFloat(regForm.sex) : 1.0,
        phone_number: regForm.phone_number || null,
        emergency_contact_name: regForm.emergency_contact_name || null,
        emergency_contact_phone: regForm.emergency_contact_phone || null,
        address: regForm.address || null,
        preferred_doctor_id: regForm.preferred_doctor_id ? parseInt(regForm.preferred_doctor_id, 10) : null,
        department_preference: regForm.department_preference || "Cardiology",
        systolic_bp: regForm.systolic_bp ? parseInt(regForm.systolic_bp, 10) : null,
        diastolic_bp: regForm.diastolic_bp ? parseInt(regForm.diastolic_bp, 10) : null,
        cholesterol: regForm.cholesterol ? parseFloat(regForm.cholesterol) : null,
        bmi: regForm.bmi ? parseFloat(regForm.bmi) : null,
        fasting_blood_sugar: regForm.fasting_blood_sugar !== "" ? parseFloat(regForm.fasting_blood_sugar) : null,
        max_heart_rate: regForm.max_heart_rate ? parseFloat(regForm.max_heart_rate) : null,
        smoking: regForm.smoking !== "" ? parseFloat(regForm.smoking) : null,
        hypertension: regForm.hypertension !== "" ? parseFloat(regForm.hypertension) : null,
        diabetes: regForm.diabetes !== "" ? parseFloat(regForm.diabetes) : null,
      });
      toast.success("Registration successful! Welcome to the platform.");
    } catch (err) {
      setError(err.message || "Registration failed. Please check your details and try again.");
    } finally {
      setLoading(false);
    }
  };

  const superAdmins = demoUsers.filter((u) => u.role === "super_admin");
  const hospitalAdmins = demoUsers.filter((u) => u.role === "hospital_admin");
  const doctors = demoUsers.filter((u) => u.role === "doctor");
  const patients = demoUsers.filter((u) => u.role === "patient");

  const calculatedUserAge = calculateAge(regForm.date_of_birth);

  return (
    <div className="container" style={{ maxWidth: activeMode === "register" ? 560 : 460, marginTop: 24, transition: "max-width 0.3s ease" }}>
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
          <h2 style={{ margin: 0 }}>Medical Risk XAI Platform</h2>
          {onBackToLanding && (
            <button
              type="button"
              className="btn-secondary"
              onClick={onBackToLanding}
              style={{ fontSize: "0.8rem", padding: "4px 10px" }}
            >
              ← Back to Home
            </button>
          )}
        </div>

        {/* Mode Switcher */}
        <div style={{ display: "flex", gap: 6, marginBottom: 16 }}>
          <button
            type="button"
            className={activeMode === "login" ? "" : "btn-secondary"}
            onClick={() => {
              setActiveMode("login");
              setError("");
            }}
            style={{ flex: 1 }}
          >
            Sign In
          </button>
          <button
            type="button"
            className={activeMode === "register" ? "" : "btn-secondary"}
            onClick={() => {
              setActiveMode("register");
              setError("");
            }}
            style={{ flex: 1 }}
          >
            Patient Registration
          </button>
        </div>

        {error && <div className="alert alert-error">{error}</div>}

        {activeMode === "login" ? (
          <div>
            {/* Quick demo login selector */}
            <div className="form-group" style={{ marginBottom: 16 }}>
              <label htmlFor="demo-login-select">Quick Demo Login</label>
              {demoLoading ? (
                <SkeletonList items={3} />
              ) : (
                <select id="demo-login-select" onChange={handleDemoSelect} defaultValue="">
                  <option value="">-- Choose a demo account --</option>
                  {superAdmins.map((a) => (
                    <option key={a.id} value={a.email}>
                      Super: {a.label}
                    </option>
                  ))}
                  {hospitalAdmins.map((a) => (
                    <option key={a.id} value={a.email}>
                      Hospital: {a.label}
                    </option>
                  ))}
                  <optgroup label="Doctors">
                    {doctors.map((d) => (
                      <option key={d.email} value={d.email}>
                        {d.label}
                      </option>
                    ))}
                  </optgroup>
                  <optgroup label="Patients">
                    {patients.map((p) => (
                      <option key={p.email} value={p.email}>
                        {p.label}
                      </option>
                    ))}
                  </optgroup>
                </select>
              )}
            </div>

            <form className="form" onSubmit={handleLoginSubmit}>
              <div className="form-group">
                <label>Hospital Code (leave blank for Super Admin)</label>
                <input
                  type="text"
                  value={hospitalCode}
                  onChange={(e) => setHospitalCode(e.target.value.toUpperCase())}
                  placeholder="e.g. CITY01"
                />
              </div>
              <div className="form-group">
                <label>Email Address</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="e.g. dr.sharma@hospital.com"
                  required
                />
              </div>
              <div className="form-group">
                <label>Password</label>
                <PasswordToggle
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  required
                />
              </div>
              <button type="submit" disabled={loading} style={{ width: "100%" }}>
                {loading ? "Signing in..." : "Sign In"}
              </button>
            </form>

            <div style={{ marginTop: 16, fontSize: "0.82rem", color: "#64748b" }}>
              <p>Demo Password: <code>Demo@123</code> for seeded accounts</p>
            </div>
          </div>
        ) : (
          <div>
            <p style={{ fontSize: "0.85rem", color: "#64748b", marginBottom: 14 }}>
              Register as a new patient. Fill in your details including Date of Birth so our ML risk engine can perform your baseline evaluation immediately.
            </p>
            <form className="form" onSubmit={handleRegisterSubmit}>
              {/* Basic Credentials */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                <div className="form-group">
                  <label>Full Name *</label>
                  <input
                    type="text"
                    placeholder="Your Full Name"
                    value={regForm.name}
                    onChange={(e) => setRegForm({ ...regForm, name: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Email Address *</label>
                  <input
                    type="email"
                    placeholder="you@email.com"
                    value={regForm.email}
                    onChange={(e) => setRegForm({ ...regForm, email: e.target.value })}
                    required
                  />
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                <div className="form-group">
                  <label>Hospital Code *</label>
                  <input
                    type="text"
                    placeholder="e.g. CITY01"
                    value={regForm.hospital_code}
                    onChange={(e) => setRegForm({ ...regForm, hospital_code: e.target.value.toUpperCase() })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Password * (min 6 chars)</label>
                  <PasswordToggle
                    value={regForm.password}
                    onChange={(e) => setRegForm({ ...regForm, password: e.target.value })}
                    placeholder="Create password"
                    required
                    minLength={6}
                  />
                </div>
              </div>

              {/* Demographics: Date of Birth & Sex */}
              <div style={{ padding: "12px", borderRadius: "8px", backgroundColor: "#f8fafc", border: "1px solid #e2e8f0", marginBottom: 12 }}>
                <div style={{ fontWeight: 600, fontSize: "0.9rem", marginBottom: 10, color: "#1e293b" }}>
                  🎂 Demographics & Age Calculation
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                  <div className="form-group" style={{ margin: 0 }}>
                    <label style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span>Date of Birth *</span>
                      {calculatedUserAge !== null && (
                        <span className="badge badge-neutral" style={{ fontSize: "0.75rem", backgroundColor: "#e0f2fe", color: "#0369a1" }}>
                          Age: {calculatedUserAge} yrs
                        </span>
                      )}
                    </label>
                    <input
                      type="date"
                      value={regForm.date_of_birth}
                      onChange={(e) => setRegForm({ ...regForm, date_of_birth: e.target.value })}
                      required
                    />
                  </div>
                  <div className="form-group" style={{ margin: 0 }}>
                    <label>Biological Sex *</label>
                    <select
                      value={regForm.sex}
                      onChange={(e) => setRegForm({ ...regForm, sex: e.target.value })}
                      required
                    >
                      <option value="1">Male</option>
                      <option value="0">Female</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* Contact Details */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                <div className="form-group">
                  <label>Phone Number</label>
                  <input
                    type="tel"
                    placeholder="+91 9876543210"
                    value={regForm.phone_number}
                    onChange={(e) => setRegForm({ ...regForm, phone_number: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label>Address / Location</label>
                  <input
                    type="text"
                    placeholder="City / Area"
                    value={regForm.address}
                    onChange={(e) => setRegForm({ ...regForm, address: e.target.value })}
                  />
                </div>
              </div>

              {/* Emergency Contact */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                <div className="form-group">
                  <label>Emergency Contact Name</label>
                  <input
                    type="text"
                    placeholder="Contact Person"
                    value={regForm.emergency_contact_name}
                    onChange={(e) => setRegForm({ ...regForm, emergency_contact_name: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label>Emergency Contact Phone</label>
                  <input
                    type="tel"
                    placeholder="Emergency Phone"
                    value={regForm.emergency_contact_phone}
                    onChange={(e) => setRegForm({ ...regForm, emergency_contact_phone: e.target.value })}
                  />
                </div>
              </div>

              {/* Routing Choices */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                <div className="form-group">
                  <label>Department Preference</label>
                  <select
                    value={regForm.department_preference}
                    onChange={(e) => setRegForm({ ...regForm, department_preference: e.target.value })}
                  >
                    <option value="Cardiology">Cardiology</option>
                    <option value="Internal Medicine">Internal Medicine</option>
                    <option value="Endocrinology & Metabolic Care">Endocrinology & Metabolic Care</option>
                    <option value="Pulmonology">Pulmonology</option>
                    <option value="Nephrology & Renal Health">Nephrology & Renal Health</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Preferred Physician (Optional)</label>
                  <select
                    value={regForm.preferred_doctor_id}
                    onChange={(e) => setRegForm({ ...regForm, preferred_doctor_id: e.target.value })}
                  >
                    <option value="">-- Route to Dept Queue --</option>
                    {availableDoctors.map((doc) => (
                      <option key={doc.id} value={doc.id}>
                        Dr. {doc.name} ({doc.specialization || "Physician"})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Optional Baseline Clinical Vitals for accurate initial ML Prediction */}
              <div style={{ border: "1px solid #cbd5e1", borderRadius: 8, overflow: "hidden", marginBottom: 14 }}>
                <button
                  type="button"
                  onClick={() => setRegForm({ ...regForm, showVitals: !regForm.showVitals })}
                  style={{
                    width: "100%",
                    display: "flex",
                    justify: "space-between",
                    alignItems: "center",
                    backgroundColor: "#f1f5f9",
                    color: "#334155",
                    border: "none",
                    padding: "8px 12px",
                    fontWeight: 600,
                    fontSize: "0.85rem",
                    cursor: "pointer",
                  }}
                >
                  <span>🩺 Initial Clinical Baseline & Vitals (Optional)</span>
                  <span>{regForm.showVitals ? "▲ Hide" : "▼ Expand to enter vitals"}</span>
                </button>

                {regForm.showVitals && (
                  <div style={{ padding: 12, backgroundColor: "#ffffff" }}>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                      <div className="form-group">
                        <label>Systolic BP (mmHg)</label>
                        <input
                          type="number"
                          placeholder="e.g. 120"
                          value={regForm.systolic_bp}
                          onChange={(e) => setRegForm({ ...regForm, systolic_bp: e.target.value })}
                        />
                      </div>
                      <div className="form-group">
                        <label>Diastolic BP (mmHg)</label>
                        <input
                          type="number"
                          placeholder="e.g. 80"
                          value={regForm.diastolic_bp}
                          onChange={(e) => setRegForm({ ...regForm, diastolic_bp: e.target.value })}
                        />
                      </div>
                    </div>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
                      <div className="form-group">
                        <label>Cholesterol (mg/dL)</label>
                        <input
                          type="number"
                          placeholder="e.g. 190"
                          value={regForm.cholesterol}
                          onChange={(e) => setRegForm({ ...regForm, cholesterol: e.target.value })}
                        />
                      </div>
                      <div className="form-group">
                        <label>BMI (kg/m²)</label>
                        <input
                          type="number"
                          step="0.1"
                          placeholder="e.g. 24.5"
                          value={regForm.bmi}
                          onChange={(e) => setRegForm({ ...regForm, bmi: e.target.value })}
                        />
                      </div>
                      <div className="form-group">
                        <label>Max Heart Rate</label>
                        <input
                          type="number"
                          placeholder="e.g. 150"
                          value={regForm.max_heart_rate}
                          onChange={(e) => setRegForm({ ...regForm, max_heart_rate: e.target.value })}
                        />
                      </div>
                    </div>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
                      <div className="form-group">
                        <label>Smoking Status</label>
                        <select
                          value={regForm.smoking}
                          onChange={(e) => setRegForm({ ...regForm, smoking: e.target.value })}
                        >
                          <option value="0">Non-Smoker</option>
                          <option value="1">Smoker / Former</option>
                        </select>
                      </div>
                      <div className="form-group">
                        <label>Hypertension</label>
                        <select
                          value={regForm.hypertension}
                          onChange={(e) => setRegForm({ ...regForm, hypertension: e.target.value })}
                        >
                          <option value="0">No</option>
                          <option value="1">Yes</option>
                        </select>
                      </div>
                      <div className="form-group">
                        <label>Diabetes</label>
                        <select
                          value={regForm.diabetes}
                          onChange={(e) => setRegForm({ ...regForm, diabetes: e.target.value })}
                        >
                          <option value="0">No</option>
                          <option value="1">Yes</option>
                        </select>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              <button type="submit" disabled={loading} style={{ width: "100%", marginTop: 4 }}>
                {loading ? "Registering & Predicting ML Risk..." : "Create Account & Evaluate ML Risk"}
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}
