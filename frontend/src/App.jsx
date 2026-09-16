import React, { useState, useEffect, useCallback } from "react";
import { useAuth } from "./AuthContext";
import Login from "./Login";
import LandingPage from "./LandingPage";
import AdminDashboard from "./AdminDashboard";
import DoctorDashboard from "./DoctorDashboard";
import PatientDashboard from "./PatientDashboard";
import { ToastProvider } from "./ToastContext";
import ShortcutsModal from "./ShortcutsModal";
import "./styles.css";

function DashboardShell() {
  const { auth, logout } = useAuth();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [showShortcuts, setShowShortcuts] = useState(false);
  const [notifAsked, setNotifAsked] = useState(false);

  // Request browser notification permission after a short delay (not immediately)
  useEffect(() => {
    if (notifAsked) return;
    if (!("Notification" in window)) return;
    if (Notification.permission !== "default") return;
    const timer = setTimeout(() => {
      Notification.requestPermission().catch(() => {});
      setNotifAsked(true);
    }, 8000);
    return () => clearTimeout(timer);
  }, [notifAsked]);

  // Global keyboard shortcuts
  useEffect(() => {
    const handleKey = (e) => {
      const tag = (e.target.tagName || "").toLowerCase();
      const inInput = tag === "input" || tag === "textarea" || tag === "select" || e.target.isContentEditable;

      // "?" to open shortcuts (shift + /)
      if (e.key === "?" && !inInput) {
        e.preventDefault();
        setShowShortcuts((v) => !v);
        return;
      }

      // "/" to focus first search input
      if (e.key === "/" && !inInput) {
        e.preventDefault();
        const searchInput = document.querySelector('input[aria-label*="search"], input[placeholder*="Search"], input[placeholder*="search"]');
        if (searchInput) searchInput.focus();
        return;
      }

      // Escape to close modals
      if (e.key === "Escape") {
        setMobileNavOpen(false);
        setShowShortcuts(false);
      }
    };

    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, []);

  const closeMobileNav = useCallback(() => setMobileNavOpen(false), []);
  const [showLanding, setShowLanding] = useState(true);

  const handleLogout = () => {
    setShowLanding(true);
    logout();
  };

  // Landing page shown first for unauthenticated / new users.
  if (!auth) {
    if (showLanding) {
      return <LandingPage onGetStarted={() => setShowLanding(false)} />;
    }
    return <Login onBackToLanding={() => setShowLanding(true)} />;
  }


  const userLabel = auth.name || "User";
  const roleLabel = auth.role === "super_admin" ? "Platform Admin"
    : auth.role === "hospital_admin" ? "Hospital Admin"
    : auth.role === "doctor" ? "Doctor"
    : auth.role === "patient" ? "Patient"
    : auth.role;

  return (
    <div>
      {/* Sticky Top Nav */}
      <header className="nav">
        <div className="nav-brand">
          <span>Medical Risk XAI Platform</span>
          <button
            type="button"
            className="shortcut-help-btn"
            onClick={() => setShowShortcuts(true)}
            title="Keyboard shortcuts (?)"
            aria-label="Keyboard shortcuts"
          >
            ?
          </button>
        </div>

        <button
          type="button"
          className="mobile-menu-toggle"
          onClick={() => setMobileNavOpen((v) => !v)}
          aria-label="Toggle navigation menu"
        >
          {mobileNavOpen ? "✕" : "☰"}
        </button>

        <div className={`nav-user ${mobileNavOpen ? "nav-user-open" : ""}`}>
          <span style={{ fontSize: "0.9rem" }}>
            <strong>{userLabel}</strong> (
            <span style={{ textTransform: "capitalize", color: "#0284c7" }}>
              {roleLabel}
            </span>
            )
            {auth.hospital_code && (
              <span style={{ color: "#64748b", marginLeft: 6 }}>&middot; {auth.hospital_code}</span>
            )}
          </span>
          <button className="btn-secondary" onClick={handleLogout}>
            Log Out
          </button>
        </div>
      </header>

      {mobileNavOpen && <div className="nav-overlay" onClick={closeMobileNav} />}

      {/* Role-Based Dashboard View */}
      <main>
        {["admin", "hospital_admin", "super_admin"].includes(auth.role) && <AdminDashboard />}
        {auth.role === "doctor" && <DoctorDashboard />}
        {auth.role === "patient" && <PatientDashboard />}
      </main>

      <ShortcutsModal isOpen={showShortcuts} onClose={() => setShowShortcuts(false)} />
    </div>
  );
}

export default function App() {
  return (
    <ToastProvider>
      <DashboardShell />
    </ToastProvider>
  );
}
