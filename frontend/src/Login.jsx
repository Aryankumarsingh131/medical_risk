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
    hospital_code: "CITY01",
    preferred_doctor_id: "",
    department_preference: "Cardiology",
  });
  const [availableDoctors, setAvailableDoctors] = useState([]);

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

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
      await register({
        name: regForm.name,
        email: regForm.email,
        password: regForm.password,
        hospital_code: regForm.hospital_code,
        preferred_doctor_id: regForm.preferred_doctor_id ? parseInt(regForm.preferred_doctor_id, 10) : null,
        department_preference: regForm.department_preference || "Cardiology",
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


  return (
    <div className="container" style={{ maxWidth: 460, marginTop: 40 }}>
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
            <p style={{ fontSize: "0.85rem", color: "#64748b", marginBottom: 12 }}>
              Self-register as a new patient. Your profile will be routed to your chosen department or physician queue.
            </p>
            <form className="form" onSubmit={handleRegisterSubmit}>
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
                  placeholder="Create a password"
                  required
                  minLength={6}
                />
              </div>
              <div className="form-group">
                <label>Department / Specialty Preference</label>
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
                  <option value="">-- Route to Department Queue --</option>
                  {availableDoctors.map((doc) => (
                    <option key={doc.id} value={doc.id}>
                      Dr. {doc.name} ({doc.specialization || "Physician"})
                    </option>
                  ))}
                </select>
              </div>
              <button type="submit" disabled={loading} style={{ width: "100%", marginTop: 6 }}>
                {loading ? "Registering..." : "Create Account & Enter Portal"}
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}
