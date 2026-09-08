import React from "react";
import "./LandingPage.css";

const FEATURES = [
  {
    icon: "",
    title: "Explainable AI Risk Scoring",
    description:
      "Every prediction is backed by SHAP explanations and a deterministic clinical point engine — so clinicians always know why a patient was flagged high or low risk.",
    accent: "#0284c7",
  },
  {
    icon: "",
    title: "Multi-Tenant Hospital Isolation",
    description:
      "Each hospital operates as an isolated tenant. Patient data, doctors, records, and assessments are strictly scoped to the owning hospital.",
    accent: "#16a34a",
  },
  {
    icon: "",
    title: "Multi-Model Benchmarking",
    description:
      "Logistic regression, random forest, and XGBoost are trained and compared by ROC-AUC. The best model is deployed automatically for live inference.",
    accent: "#dc2626",
  },
  {
    icon: "",
    title: "21 Clinical Features",
    description:
      "Reprocessing insights across demographic, vital, lab, lifestyle, neurological, and comorbidity signals from 15+ curated medical datasets.",
    accent: "#7c3aed",
  },
  {
    icon: "",
    title: "Real-Time Emergency Directory",
    description:
      "Patients can locate nearby hospitals with live bed, ICU, ventilator, and blood-bank availability in an emergency.",
    accent: "#ea580c",
  },
  {
    icon: "",
    title: "Clinical Workflow Tools",
    description:
      "Doctors manage patient assessments, diagnoses, prescriptions, blood tests, and collaborative case drafts in one place.",
    accent: "#0f766e",
  },
];

export default function LandingPage({ onGetStarted }) {
  return (
    <div className="landing">
      {/* Top navigation */}
      <header className="landing-nav">
        <div className="landing-nav-inner">
          <span className="landing-logo">
            <span className="landing-logo-mark">＋</span>
            Medical Risk XAI
          </span>
          <div className="landing-nav-links">
            <a href="#features">Features</a>
            <a href="#how-it-works">How it works</a>
            <a href="#role">For your role</a>
          </div>
          <button type="button" className="landing-nav-cta" onClick={onGetStarted}>
            Sign In
          </button>
        </div>
      </header>

      {/* Hero */}
      <section className="landing-hero">
        <div className="landing-hero-inner">
          <span className="landing-eyebrow">Explainable AI · Multi-Tenant Medical SaaS</span>
          <h1 className="landing-title">
            Predict medical risk with{" "}
            <span style={{ color: "#0284c7" }}>transparent, explainable AI</span>.
          </h1>
          <p className="landing-subtitle">
            A cardiovascular risk platform that combines cutting-edge machine
            learning with clinical transparency. Every score comes with an
            audit trail, every prediction is explainable, and every hospital's
            data stays fully isolated.
          </p>
          <div className="landing-hero-actions">
            <button type="button" className="landing-btn landing-btn-primary" onClick={onGetStarted}>
              Get Started — Sign In
            </button>
            <a href="#features" className="landing-btn landing-btn-ghost">
              Explore the platform
            </a>
          </div>
          <div className="landing-stats">
            <div className="landing-stat">
              <strong>15+</strong>
              <span>Curated datasets</span>
            </div>
            <div className="landing-stat">
              <strong>21</strong>
              <span>Clinical features</span>
            </div>
            <div className="landing-stat">
              <strong>3</strong>
              <span>Model benchmark</span>
            </div>
            <div className="landing-stat">
              <strong>100%</strong>
              <span>Explainable</span>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="landing-section" id="features">
        <div className="landing-container">
          <h2 className="landing-h2">Built for clinical trust</h2>
          <p className="landing-lead">
            From research-grade datasets to a production-ready multi-tenant hospital platform.
          </p>
          <div className="landing-grid">
            {FEATURES.map((f) => (
              <div className="landing-feature" key={f.title}>
                <div className="landing-feature-dot" style={{ backgroundColor: f.accent }}>
                  {f.icon || "✓"}
                </div>
                <h3>{f.title}</h3>
                <p>{f.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="landing-section" id="how-it-works">
        <div className="landing-container">
          <h2 className="landing-h2">How it works</h2>
          <div className="landing-steps">
            <div className="landing-step">
              <span className="landing-step-num">01</span>
              <h3>Data harmonised</h3>
              <p>15+ datasets are mapped, cleaned, imputed, and outlier-filtered into a single canonical schema.</p>
            </div>
            <div className="landing-step">
              <span className="landing-step-num">02</span>
              <h3>Best model selected</h3>
              <p>XGBoost, random forest, and logistic regression are trained and ranked by ROC-AUC on stratified splits.</p>
            </div>
            <div className="landing-step">
              <span className="landing-step-num">03</span>
              <h3>Explainable inference</h3>
              <p>The API returns a deterministic risk band immediately and SHAP attributions in the background for auditability.</p>
            </div>
            <div className="landing-step">
              <span className="landing-step-num">04</span>
              <h3>Secure multi-tenant delivery</h3>
              <p>Every role sees only their own hospital's data — protected by tenant-scoped queries and role-based access.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Roles */}
      <section className="landing-section landing-section-tint" id="role">
        <div className="landing-container">
          <h2 className="landing-h2">Designed for every role</h2>
          <div className="landing-roles">
            <div className="landing-role">
              <h3>Platform Admin</h3>
              <p>Oversee all hospitals, users, and activity from a single control plane.</p>
            </div>
            <div className="landing-role">
              <h3>Hospital Admin</h3>
              <p>Manage your hospital's doctors, patients, medicines, and availability.</p>
            </div>
            <div className="landing-role">
              <h3>Doctors</h3>
              <p>Assess risk, record diagnoses, write prescriptions, and manage a patient queue.</p>
            </div>
            <div className="landing-role">
              <h3>Patients</h3>
              <p>Track your risk history, view reports, and find emergency care nearby.</p>
            </div>
          </div>

          <div className="landing-cta-band">
            <h2>Ready to see it in action?</h2>
            <p>Log in with a platform, hospital, doctor, or patient demo account.</p>
            <button type="button" className="landing-btn landing-btn-primary landing-btn-lg" onClick={onGetStarted}>
              Enter the Platform
            </button>
          </div>
        </div>
      </section>

      <footer className="landing-footer">
        <p>Medical Risk XAI · Explainable multi-tenant medical risk prediction</p>
      </footer>
    </div>
  );
}