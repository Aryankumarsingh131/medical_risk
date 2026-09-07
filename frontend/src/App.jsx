import React from "react";
import { useAuth } from "./AuthContext";
import Login from "./Login";
import AdminDashboard from "./AdminDashboard";
import DoctorDashboard from "./DoctorDashboard";
import PatientDashboard from "./PatientDashboard";
import "./styles.css";

export default function App() {
  const { auth, logout } = useAuth();

  if (!auth) {
    return <Login />;
  }

  return (
    <div>
      {/* Minimal Top Nav */}
      <header className="nav">
        <div className="nav-brand">Medical Risk XAI Platform</div>
        <div className="nav-user">
          <span style={{ fontSize: "0.9rem" }}>
            <strong>{auth.name}</strong> (
            <span style={{ textTransform: "capitalize", color: "#0284c7" }}>
              {auth.role}
            </span>
            )
          </span>
          <button className="btn-secondary" onClick={logout}>
            Log Out
          </button>
        </div>
      </header>

      {/* Role-Based Dashboard View */}
      <main>
        {auth.role === "admin" && <AdminDashboard />}
        {auth.role === "doctor" && <DoctorDashboard />}
        {auth.role === "patient" && <PatientDashboard />}
      </main>
    </div>
  );
}
