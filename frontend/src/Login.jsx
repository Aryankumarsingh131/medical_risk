import React, { useState, useEffect } from "react";
import { useAuth } from "./AuthContext";
import { apiRequest } from "./api";

const DEMO_USERS = [
  { id: 1, label: "Admin ID 1: Admin - System Administrator", email: "admin@hospital.com", role: "admin" },
  // Doctors
  { id: 2, label: "Dr. Sharma (Doctor ID 2)", email: "dr.sharma@hospital.com", role: "doctor" },
  { id: 3, label: "Dr. Mehta (Doctor ID 3)", email: "dr.mehta@hospital.com", role: "doctor" },
  { id: 4, label: "Dr. Khan (Doctor ID 4)", email: "dr.khan@hospital.com", role: "doctor" },
  { id: 5, label: "Dr. Rao (Doctor ID 5)", email: "dr.rao@hospital.com", role: "doctor" },
  { id: 6, label: "Dr. Iyer (Doctor ID 6)", email: "dr.iyer@hospital.com", role: "doctor" },
  // Patients
  { id: 7, label: "Arjun (Patient ID 7)", email: "patient.arjun@hospital.com", role: "patient" },
  { id: 8, label: "Riya (Patient ID 8)", email: "patient.riya@hospital.com", role: "patient" },
  { id: 9, label: "Rohan (Patient ID 9)", email: "patient.rohan@hospital.com", role: "patient" },
  { id: 10, label: "Ananya (Patient ID 10)", email: "patient.ananya@hospital.com", role: "patient" },
  { id: 11, label: "Vikram (Patient ID 11)", email: "patient.vikram@hospital.com", role: "patient" },
  { id: 12, label: "Pooja (Patient ID 12)", email: "patient.pooja@hospital.com", role: "patient" },
  { id: 13, label: "Siddharth (Patient ID 13)", email: "patient.siddharth@hospital.com", role: "patient" },
  { id: 14, label: "Neha (Patient ID 14)", email: "patient.neha@hospital.com", role: "patient" },
  { id: 15, label: "Aditya (Patient ID 15)", email: "patient.aditya@hospital.com", role: "patient" },
  { id: 16, label: "Kavya (Patient ID 16)", email: "patient.kavya@hospital.com", role: "patient" },
];

const formatDemoUserLabel = (user) => {
  if (user?.label) return user.label;
  const name = user?.name || user?.email || "User";
  const roleText = user?.role === "admin" ? "Admin" : user?.role === "doctor" ? "Doctor" : "Patient";
  const idText = user?.id ? ` ID ${user.id}` : "";
  return `${roleText}${idText}: ${name}`;
};

export default function Login() {
  const { login, register } = useAuth();
  const [activeMode, setActiveMode] = useState("login"); // 'login' | 'register'
  const [demoUsers, setDemoUsers] = useState(DEMO_USERS);
  
  // Login form state
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  
  // Self registration state
  const [regForm, setRegForm] = useState({
    name: "",
    email: "",
    password: "",
    preferred_doctor_id: "",
    department_preference: "Cardiology",
  });
  const [availableDoctors, setAvailableDoctors] = useState([]);
  
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Load available doctors for self-registration routing
    apiRequest("/doctor/all-doctors")
      .then((docs) => setAvailableDoctors(docs || []))
      .catch(() => {});

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
      });
  }, []);

  const handleDemoSelect = (e) => {
    const selectedEmail = e.target.value;
    if (!selectedEmail) return;
    setEmail(selectedEmail);
    setPassword("Demo@123");
    setError("");
  };

  const handleLoginSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
    } catch (err) {
      setError(err.message || "Invalid credentials");
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
        preferred_doctor_id: regForm.preferred_doctor_id ? parseInt(regForm.preferred_doctor_id, 10) : null,
        department_preference: regForm.department_preference || "Cardiology",
      });
    } catch (err) {
      setError(err.message || "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  const adminUser = demoUsers.find((u) => u.role === "admin");
  const doctors = demoUsers.filter((u) => u.role === "doctor");
  const patients = demoUsers.filter((u) => u.role === "patient");

  return (
    <div className="container" style={{ maxWidth: 460, marginTop: 40 }}>
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
          <h2 style={{ margin: 0 }}>Medical Risk XAI Platform</h2>
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
              <select id="demo-login-select" onChange={handleDemoSelect} defaultValue="">
                <option value="">-- Choose a demo account --</option>
                {adminUser && (
                  <option value={adminUser.email}>Admin: {adminUser.label}</option>
                )}
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
            </div>

            <form className="form" onSubmit={handleLoginSubmit}>
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
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
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
                <label>Password * (min 6 chars)</label>
                <input
                  type="password"
                  placeholder="Create a password"
                  value={regForm.password}
                  onChange={(e) => setRegForm({ ...regForm, password: e.target.value })}
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
