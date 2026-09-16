import React, { useState, useEffect } from "react";
import "./LandingPage.css";
import doctorPortrait from "./assets/doctor_portrait.jpg";
import medicalTeam from "./assets/medical_team.jpg";
import doctorPatient from "./assets/doctor_patient.jpg";
import { ContainerScroll } from "./components/ui/container-scroll-animation";
import CommunityOrbit from "./components/ui/builders-community-hero";
import { InfiniteFloatingTestimonials } from "./components/ui/floating-testimonials";
import { AppleHelloEnglishEffect } from "./components/ui/apple-hello-effect";
import { 
  Activity, 
  HeartPulse, 
  Cpu, 
  Stethoscope, 
  FileCheck2, 
  ShieldAlert, 
  Sparkles,
  Award
} from "lucide-react";

// ── SVG Icons ─────────────────────────────────────────────────────────────
const LogoIcon = () => (
  <svg width="36" height="36" viewBox="0 0 36 36" fill="none">
    <rect width="36" height="36" rx="8" fill="#1AAB9B"/>
    <path d="M18 8v20M8 18h20" stroke="#fff" strokeWidth="3.5" strokeLinecap="round"/>
    <path d="M12 9c0-2 1.5-3 3-2" stroke="#C6F135" strokeWidth="1.5" strokeLinecap="round"/>
  </svg>
);

const SearchIcon = () => (
  <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
    <circle cx="7.5" cy="7.5" r="5.5" stroke="#6B7280" strokeWidth="1.5"/>
    <path d="M12 12l3.5 3.5" stroke="#6B7280" strokeWidth="1.5" strokeLinecap="round"/>
  </svg>
);

const ChatBubbleIcon = () => (
  <div className="lp-chat-icon" aria-hidden="true">
    <svg width="44" height="44" viewBox="0 0 44 44" fill="none">
      <rect width="44" height="44" rx="12" fill="#E6F9F7"/>
      <path d="M12 15a2 2 0 012-2h16a2 2 0 012 2v9a2 2 0 01-2 2h-5l-5 4v-4h-6a2 2 0 01-2-2v-9z" stroke="#1AAB9B" strokeWidth="1.5" strokeLinejoin="round"/>
      <path d="M16 18h12M16 22h7" stroke="#1AAB9B" strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  </div>
);

const ArrowRight = () => (
  <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
    <path d="M2.5 7.5h10M8.5 3.5l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);

// Medical outline icons matching reference style
const ShieldIcon = () => (
  <svg width="54" height="54" viewBox="0 0 54 54" fill="none">
    <path d="M27 6l18 8v14c0 10-8 18-18 22C9 46 1 38 1 28V14l18-8z" stroke="#1A1A1A" strokeWidth="1.5" fill="none" strokeLinejoin="round"/>
    <path d="M20 27l5 5 9-9" stroke="#1A1A1A" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    <circle cx="41" cy="11" r="6" stroke="#1A1A1A" strokeWidth="1.5" fill="none"/>
    <path d="M39 11h4M41 9v4" stroke="#1A1A1A" strokeWidth="1.5" strokeLinecap="round"/>
  </svg>
);

const BrainAIIcon = () => (
  <svg width="54" height="54" viewBox="0 0 54 54" fill="none">
    <ellipse cx="27" cy="27" rx="14" ry="12" stroke="#1A1A1A" strokeWidth="1.5" fill="none"/>
    <path d="M13 27H7M41 27h6M27 13v-6M27 41v6" stroke="#1A1A1A" strokeWidth="1.5" strokeLinecap="round"/>
    <circle cx="27" cy="27" r="4" stroke="#1A1A1A" strokeWidth="1.3" fill="none"/>
    <path d="M27 8l2 4-2 4-2-4 2-4z" stroke="#1A1A1A" strokeWidth="1.2" strokeLinejoin="round" fill="none"/>
  </svg>
);

const DataChartIcon = () => (
  <svg width="54" height="54" viewBox="0 0 54 54" fill="none">
    <rect x="7" y="11" width="40" height="28" rx="3" stroke="#1A1A1A" strokeWidth="1.5" fill="none"/>
    <path d="M19 39v7M35 39v7M13 46h28" stroke="#1A1A1A" strokeWidth="1.5" strokeLinecap="round"/>
    <path d="M14 32l7-8 7 5 7-10 7 6" stroke="#1A1A1A" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
    <circle cx="40" cy="9" r="6" stroke="#1A1A1A" strokeWidth="1.5" fill="none"/>
    <path d="M38 9h4M40 7v4" stroke="#1A1A1A" strokeWidth="1.5" strokeLinecap="round"/>
  </svg>
);

const GreenIcon1 = () => (
  <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
    <path d="M4 18V9l7-6 7 6v9" stroke="#1A1A1A" strokeWidth="1.4" strokeLinejoin="round"/>
    <rect x="8.5" y="12" width="5" height="6" rx="1" stroke="#1A1A1A" strokeWidth="1.3" fill="none"/>
  </svg>
);
const GreenIcon2 = () => (
  <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
    <circle cx="11" cy="8" r="4" stroke="#1A1A1A" strokeWidth="1.4"/>
    <path d="M3 20c0-4.5 3.5-7 8-7s8 2.5 8 7" stroke="#1A1A1A" strokeWidth="1.4" strokeLinecap="round"/>
  </svg>
);
const GreenIcon3 = () => (
  <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
    <rect x="2" y="4" width="18" height="14" rx="2" stroke="#1A1A1A" strokeWidth="1.4" fill="none"/>
    <path d="M6 10h10M6 14h6" stroke="#1A1A1A" strokeWidth="1.4" strokeLinecap="round"/>
    <circle cx="16" cy="14" r="2" stroke="#1A1A1A" strokeWidth="1.2" fill="none"/>
    <path d="M17 15l2 2" stroke="#1A1A1A" strokeWidth="1.2" strokeLinecap="round"/>
  </svg>
);

const FBIcon  = () => <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor"><path d="M8 4.5V2.5a.75.75 0 01.75-.75H10V.25H8.25A2.25 2.25 0 006 2.5v2H4.5v2H6v6.5h2V6.5h1.75L10.25 4.5H8z"/></svg>;
const LIIcon  = () => <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor"><path d="M2 5h2v7H2V5zm1-1.5A1.25 1.25 0 113 1a1.25 1.25 0 010 2.5zm3 1.5h1.8v1h.03C8.2 5.7 9 5.2 10 5.2c2.1 0 2.5 1.4 2.5 3.2V12h-2V8.8c0-.9-.02-2.1-1.3-2.1-1.3 0-1.5 1-1.5 2V12H6V5z"/></svg>;
const IGIcon  = () => <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.2"><rect x="1.5" y="1.5" width="11" height="11" rx="3.2"/><circle cx="7" cy="7" r="2.7"/><circle cx="10.2" cy="3.8" r=".6" fill="currentColor" stroke="none"/></svg>;
const XIcon   = () => <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor"><path d="M1 1l5.2 6L1 13h1.4l4.5-5.1L11 13h2L7.6 6.8 12.6 1h-1.4L6.7 5.7 3 1H1z"/></svg>;

const MapPinSvg = () => (
  <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
    <path d="M7 1a4 4 0 014 4c0 3.2-4 8-4 8S3 8.2 3 5a4 4 0 014-4z" stroke="rgba(255,255,255,.5)" strokeWidth="1.2" fill="none"/>
    <circle cx="7" cy="5" r="1.4" stroke="rgba(255,255,255,.5)" strokeWidth="1.2" fill="none"/>
  </svg>
);
const PhoneSvg = () => (
  <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
    <path d="M2 2.5C2 2 2.5 1 4 1c.5 0 1 .5 1.5 1.5L6 4c0 .5-.5 1-1 1.5C4.8 5.7 5.3 6.8 6.5 8s2.3 1.7 2.5 1.5C9.5 9 10 8.5 10.5 8.5l1.5.5c1 .5 1.5 1 1.5 1.5 0 1.5-1 2-2 2C7 13 1 7 1 3.5 1 2.5 1.5 2 2 2.5z" stroke="rgba(255,255,255,.5)" strokeWidth="1.2" fill="none"/>
  </svg>
);
const MailSvg = () => (
  <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
    <rect x="1" y="3" width="12" height="8" rx="1.5" stroke="rgba(255,255,255,.5)" strokeWidth="1.2" fill="none"/>
    <path d="M1 4.5l6 3.5 6-3.5" stroke="rgba(255,255,255,.5)" strokeWidth="1.2"/>
  </svg>
);

// ── Main Component ──────────────────────────────────────────────────────────
export default function LandingPage({ onGetStarted }) {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 30);
    window.addEventListener("scroll", handler);
    return () => window.removeEventListener("scroll", handler);
  }, []);

  return (
    <div className="lp">

      {/* ── HEADER ─────────────────────────────────────────────────────── */}
      <header className={`lp-header${scrolled ? " lp-header--shadow" : ""}`}>
        <div className="lp-wrap lp-header__row">
          {/* Logo – real system name */}
          <a href="#" className="lp-logo">
            <LogoIcon />
            <span>Medical Risk XAI</span>
          </a>

          {/* Nav */}
          <nav className="lp-nav">
            <a href="#home"     className="lp-nav__a">Home     <span className="lp-nav__v">▾</span></a>
            <a href="#features" className="lp-nav__a">Features <span className="lp-nav__v">▾</span></a>
            <a href="#how"      className="lp-nav__a">How It Works</a>
            <a href="#about"    className="lp-nav__a">About    <span className="lp-nav__v">▾</span></a>
            <a href="#contact"  className="lp-nav__a">Contact</a>
          </nav>

          {/* Right actions */}
          <div className="lp-header__right">
            <button className="lp-search-btn" aria-label="Search">
              <SearchIcon />
            </button>
            <ChatBubbleIcon />
            <button className="lp-signin-btn" onClick={onGetStarted}>
              Sign In →
            </button>
          </div>
        </div>
      </header>

      {/* ── HERO / ABOUT ────────────────────────────────────────────────── */}
      <section className="lp-hero" id="home">
        <div className="lp-wrap lp-hero__row">
          {/* Left content */}
          <div className="lp-hero__left">
            <div style={{ marginBottom: "0.75rem", display: "inline-block", color: "#1AAB9B" }}>
              <AppleHelloEnglishEffect speed={1.1} style={{ height: "46px" }} />
            </div>
            <span className="lp-badge">About Our Platform</span>
            <h1 className="lp-hero__h1">
              Predict Risk with<br />
              <span className="lp-hl">Transparent</span>,<br />Explainable AI
            </h1>
            <p className="lp-hero__sub">
              A cardiovascular risk platform that combines cutting-edge machine learning with full
              clinical transparency. Every score is explainable, every prediction auditable, and
              every hospital's data stays fully isolated.
            </p>

            <div className="lp-feature-list">
              <div className="lp-feature">
                <span className="lp-feature__num">01</span>
                <div>
                  <h4 className="lp-feature__title">Clinically Validated Risk Scoring</h4>
                  <p className="lp-feature__body">
                    Powered by <span className="lp-teal-link">XGBoost, Random Forest</span> and{" "}
                    <span className="lp-teal-link">Logistic Regression</span> — benchmarked by ROC-AUC
                    across 15+ curated medical datasets with <span className="lp-teal-link">21 clinical features</span>.
                  </p>
                </div>
              </div>
              <div className="lp-feature">
                <span className="lp-feature__num">02</span>
                <div>
                  <h4 className="lp-feature__title">Multi-Tenant Hospital Isolation</h4>
                  <p className="lp-feature__body">
                    Each hospital operates as a fully <span className="lp-teal-link">isolated tenant</span>. Patient data,
                    doctors, and records are strictly scoped to the owning{" "}
                    <span className="lp-teal-link">hospital</span> — no cross-contamination.
                  </p>
                </div>
              </div>
            </div>

            <div className="lp-hero__cta-row">
              <button className="lp-btn-primary" onClick={onGetStarted}>
                Get Started — Sign In
              </button>
              <a href="#features" className="lp-btn-outline">See Features</a>
            </div>
          </div>

          {/* Right – doctor image with decorative elements */}
          <div className="lp-hero__right">
            <div className="lp-hero__circle"></div>
            <img src={doctorPortrait} alt="Medical professional" className="lp-hero__photo" />
            <div className="lp-deco lp-deco--lime"></div>
            <div className="lp-deco lp-deco--teal"></div>
          </div>
        </div>
      </section>

      {/* ── INTERACTIVE 3D SCROLL SHOWCASE ─────────────────────────────── */}
      <section style={{ backgroundColor: "#060D17", width: "100%", padding: "2rem 0" }}>
        <ContainerScroll
          titleComponent={
            <div style={{ marginBottom: "1.5rem" }}>
              <span
                style={{
                  display: "inline-block",
                  padding: "6px 16px",
                  borderRadius: "9999px",
                  fontSize: "12px",
                  fontWeight: 700,
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                  color: "#C6F135",
                  backgroundColor: "rgba(198, 241, 53, 0.12)",
                  border: "1px solid rgba(198, 241, 53, 0.25)",
                  marginBottom: "1rem",
                }}
              >
                Interactive Platform View
              </span>
              <h2
                style={{
                  fontSize: "clamp(2rem, 4vw, 3.2rem)",
                  fontWeight: 800,
                  color: "#FFFFFF",
                  letterSpacing: "-0.02em",
                  lineHeight: 1.15,
                  margin: 0,
                }}
              >
                Experience Real-Time <br />
                <span
                  style={{
                    background: "linear-gradient(90deg, #1AAB9B, #C6F135)",
                    WebkitBackgroundClip: "text",
                    WebkitTextFillColor: "transparent",
                  }}
                >
                  Risk Assessment & XAI Analytics
                </span>
              </h2>
            </div>
          }
        >
          <div
            style={{
              position: "relative",
              width: "100%",
              height: "100%",
              borderRadius: "16px",
              overflow: "hidden",
            }}
          >
            <img
              src={medicalTeam}
              alt="Medical Risk XAI Platform Interface"
              style={{
                width: "100%",
                height: "100%",
                objectFit: "cover",
                objectPosition: "center",
                filter: "brightness(0.9)",
              }}
            />
            {/* Overlay Glass UI Mockup Badge */}
            <div
              style={{
                position: "absolute",
                bottom: "20px",
                left: "20px",
                right: "20px",
                backgroundColor: "rgba(10, 18, 30, 0.88)",
                backdropFilter: "blur(12px)",
                border: "1px solid rgba(255,255,255,0.15)",
                borderRadius: "16px",
                padding: "16px 24px",
                display: "flex",
                flexWrap: "wrap",
                alignItems: "center",
                justifyContent: "space-between",
                gap: "12px",
              }}
            >
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <span
                    style={{
                      display: "inline-block",
                      width: "10px",
                      height: "10px",
                      borderRadius: "50%",
                      backgroundColor: "#3FB950",
                    }}
                  />
                  <span style={{ color: "#E6EDF3", fontSize: "14px", fontWeight: 700 }}>
                    XGBoost & SHAP Pipeline Active
                  </span>
                </div>
                <div style={{ color: "rgba(255,255,255,0.6)", fontSize: "12px", marginTop: "4px" }}>
                  ROC-AUC Score: 0.894 • 21 Clinical Parameters Analyzed • Zero Data Leakage
                </div>
              </div>
              <button
                onClick={onGetStarted}
                style={{
                  backgroundColor: "#1AAB9B",
                  color: "#FFFFFF",
                  border: "none",
                  padding: "8px 20px",
                  borderRadius: "9999px",
                  fontWeight: 600,
                  fontSize: "13px",
                  cursor: "pointer",
                }}
              >
                Launch Live Demo →
              </button>
            </div>
          </div>
        </ContainerScroll>
      </section>

      {/* ── STATS STRIP ─────────────────────────────────────────────────── */}
      <div className="lp-stats-strip">
        <div className="lp-wrap lp-stats-strip__inner">
          {[
            { num:"15+",   label:"Curated Datasets"      },
            { num:"21",    label:"Clinical Features"     },
            { num:"3",     label:"Benchmarked Models"    },
            { num:"100%",  label:"Explainable Outputs"   },
          ].map((s,i) => (
            <div key={i} className="lp-stat">
              <div className="lp-stat__num">{s.num}</div>
              <div className="lp-stat__label">{s.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ── INFO CARDS (3-col) ──────────────────────────────────────────── */}
      <section className="lp-info-section" id="features">
        <div className="lp-wrap lp-info-grid">
          <div className="lp-info-card">
            <ShieldIcon />
            <h3 className="lp-info-card__h3">SHAP-powered risk explanations<br />patients & doctors can trust</h3>
            <a href="#" className="lp-rm lp-rm--dark" onClick={onGetStarted}>Explore Platform <ArrowRight/></a>
          </div>
          <div className="lp-info-card">
            <BrainAIIcon />
            <h3 className="lp-info-card__h3">Best model auto-selected<br />by ROC-AUC benchmarking</h3>
            <a href="#" className="lp-rm lp-rm--dark" onClick={onGetStarted}>Explore Platform <ArrowRight/></a>
          </div>
          <div className="lp-info-card">
            <DataChartIcon />
            <h3 className="lp-info-card__h3">Real-time emergency directory<br />with live hospital availability</h3>
            <a href="#" className="lp-rm lp-rm--dark" onClick={onGetStarted}>Explore Platform <ArrowRight/></a>
          </div>
        </div>
      </section>

      {/* ── FEATURES SPLIT SECTION ──────────────────────────────────────── */}
      <section className="lp-svc" id="how">
        <div className="lp-wrap lp-svc__row">
          {/* Left */}
          <div className="lp-svc__left">
            <h2 className="lp-svc__h2">
              Precision Care,<br/>
              <span className="lp-svc__line2">
                Powered by <span className="lp-svc__ul">Explainable</span> AI
              </span>
            </h2>

            {[
              {
                icon: <GreenIcon1/>,
                title:"Multi-Role Dashboard Access",
                bullets:["Hospital Admin, Doctor, Patient portals", "Role-based data access controls"],
                active: true
              },
              {
                icon: <GreenIcon2/>,
                title:"Cardiovascular Risk Assessment",
                bullets:["Instant risk score with clinical explanation", "SHAP feature attribution breakdown"],
                active: false
              },
              {
                icon: <GreenIcon3/>,
                title:"Clinical Workflow & Case Management",
                bullets:["Diagnoses, prescriptions, blood tests", "Collaborative case drafts & history"],
                active: false
              },
            ].map((s, i) => (
              <div key={i} className={`lp-svc-item${s.active ? " lp-svc-item--active" : ""}`}>
                <div className="lp-svc-item__icon">{s.icon}</div>
                <div className="lp-svc-item__body">
                  <h4 className="lp-svc-item__title">{s.title}</h4>
                  <ul className="lp-svc-item__bullets">
                    {s.bullets.map((b,j) => <li key={j}>{b}</li>)}
                  </ul>
                </div>
                <button
                  className={`lp-rm-pill ${s.active ? "lp-rm-pill--dark" : "lp-rm-pill--outline"}`}
                  onClick={onGetStarted}
                >
                  Sign In <ArrowRight/>
                </button>
              </div>
            ))}
          </div>

          {/* Right – doctor + patient image */}
          <div className="lp-svc__right">
            <div className="lp-svc__img-frame">
              <img src={doctorPatient} alt="Doctor with patient" className="lp-svc__img"/>
            </div>
          </div>
        </div>
      </section>

      {/* ── BUILDERS COMMUNITY ORBIT SECTION ────────────────────────────── */}
      <section style={{ backgroundColor: "#0B111A", width: "100%", paddingTop: "4rem" }}>
        <CommunityOrbit
          items={[
            { kind: "status", ring: "outer", angle: 132, label: "SHAP Model Verified" },
            { kind: "card", ring: "outer", angle: 112, emoji: "🩺", badge: "Live" },
            {
              kind: "pill",
              ring: "outer",
              angle: 90,
              icon: <HeartPulse size={15} color="#FF6B6B" />,
              label: "Cardio Risk Analyzed",
            },
            {
              kind: "pill",
              ring: "outer",
              angle: 68,
              icon: <Activity size={15} color="#57AB5A" />,
              label: "99.4% Uptime",
            },
            {
              kind: "avatar",
              ring: "outer",
              angle: 50,
              src: "https://images.unsplash.com/photo-1612349317150-e413f6a5b16d?auto=format&fit=crop&q=80&w=200",
              alt: "Cardiologist",
              color: "#1E3A5F",
            },
            {
              kind: "pill",
              ring: "outer",
              angle: 35,
              icon: <Cpu size={14} color="#79B8FF" />,
              label: "XGBoost Engine",
            },
            {
              kind: "avatar",
              ring: "inner",
              angle: 137,
              src: "https://images.unsplash.com/photo-1537368910025-700350fe46c7?auto=format&fit=crop&q=80&w=200",
              alt: "Medical Specialist",
              color: "#2E5A44",
            },
            {
              kind: "pill",
              ring: "inner",
              angle: 116,
              icon: <Sparkles size={14} color="#F59E0B" />,
              label: "21 Clinical Indicators",
            },
            {
              kind: "avatar",
              ring: "inner",
              angle: 90,
              src: "https://images.unsplash.com/photo-1594824813576-92896350e9eb?auto=format&fit=crop&q=80&w=200",
              alt: "Senior Clinician",
              color: "#1AAB9B",
              size: 52,
            },
            { kind: "card", ring: "inner", angle: 63, emoji: "📊" },
            { kind: "check", ring: "inner", angle: 42 },
          ]}
          stats={[
            { value: "600+", label: "Hospitals Connected" },
            { value: "240K+", label: "Risk Assessments Run" },
            { value: "98.7%", label: "Clinician Satisfaction" },
          ]}
          headline={
            <>
              Trusted by Top Indian Hospital Networks & <br />
              Cardiology Institutes Nationwide
            </>
          }
          tags={[
            { icon: <Cpu strokeWidth={2} />, label: "SHAP Explainability", onClick: onGetStarted },
            { icon: <Stethoscope strokeWidth={2} />, label: "Clinician Workflows", onClick: onGetStarted },
            { icon: <FileCheck2 strokeWidth={2} />, label: "ABDM & Data Privacy", onClick: onGetStarted },
            { icon: <ShieldAlert strokeWidth={2} />, label: "Multi-Hospital Isolation", onClick: onGetStarted },
          ]}
        />
      </section>

      {/* ── BANNER – team photo ─────────────────────────────────────────── */}
      <section className="lp-banner">
        <img src={medicalTeam} alt="Medical team collaborating" className="lp-banner__img"/>
      </section>

      {/* ── FLOATING LOOPING TESTIMONIALS SECTION ──────────────────────── */}
      <section style={{ backgroundColor: "#090E17", padding: "4rem 0 3rem" }}>
        <div className="lp-wrap" style={{ textAlign: "center", marginBottom: "2rem" }}>
          <span
            style={{
              display: "inline-block",
              padding: "5px 14px",
              borderRadius: "9999px",
              fontSize: "12px",
              fontWeight: 700,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              color: "#1AAB9B",
              backgroundColor: "rgba(26, 171, 155, 0.12)",
              border: "1px solid rgba(26, 171, 155, 0.25)",
              marginBottom: "0.8rem",
            }}
          >
            Clinical Feedback
          </span>
          <h2
            style={{
              fontSize: "clamp(1.8rem, 3.5vw, 2.6rem)",
              fontWeight: 700,
              color: "#FFFFFF",
              letterSpacing: "-0.01em",
              margin: "0 0 0.5rem 0",
            }}
          >
            What Indian Healthcare Leaders Are Saying
          </h2>
          <p style={{ color: "rgba(255,255,255,0.6)", fontSize: "15px", maxWidth: "600px", margin: "0 auto" }}>
            Real reviews floating from cardiologists, medical superintendents, and clinicians across premier healthcare institutes in India.
          </p>
        </div>

        {/* Floating infinite loop row 1 (left) */}
        <InfiniteFloatingTestimonials
          direction="left"
          speed={32}
          testimonials={[
            {
              quote: "The SHAP feature attribution breakdown gives our cardiology team transparent reasoning to share with patients and their families.",
              name: "Dr. Ananya Sen",
              role: "Head of Cardiology",
              hospital: "Apollo Multispeciality Hospitals, Kolkata",
              rating: 5,
              avatar: "https://images.unsplash.com/photo-1594824813576-92896350e9eb?auto=format&fit=crop&q=80&w=150",
            },
            {
              quote: "Multi-tenant hospital isolation guarantees that our patient data stays strictly segregated and compliant with Indian healthcare data norms.",
              name: "Dr. Rajeshwar Nair",
              role: "Medical Superintendent",
              hospital: "Amrita Institute of Medical Sciences, Kochi",
              rating: 5,
              avatar: "https://images.unsplash.com/photo-1622253692010-333f2da6031d?auto=format&fit=crop&q=80&w=150",
            },
            {
              quote: "Automated ROC-AUC benchmarking between XGBoost and Random Forest has proved invaluable during our clinical risk audits.",
              name: "Dr. Sunita Kulkarni",
              role: "Senior Consultant Cardiologist",
              hospital: "Fortis Escorts Heart Institute, New Delhi",
              rating: 5,
              avatar: "https://images.unsplash.com/photo-1559839734-2b71ea197ec2?auto=format&fit=crop&q=80&w=150",
            },
            {
              quote: "Rapid risk stratification with clinical feature importance has significantly improved triage efficiency in our emergency wing.",
              name: "Dr. Vikramaditya Sharma",
              role: "Chief of Emergency Medicine",
              hospital: "Max Super Speciality Hospital, Gurugram",
              rating: 5,
              avatar: "https://images.unsplash.com/photo-1537368910025-700350fe46c7?auto=format&fit=crop&q=80&w=150",
            },
          ]}
        />

        {/* Floating infinite loop row 2 (right) */}
        <InfiniteFloatingTestimonials
          direction="right"
          speed={36}
          testimonials={[
            {
              quote: "Our patients appreciate viewing personalized lifestyle metrics and cholesterol risk factors with absolute clarity on their portal.",
              name: "Dr. Priya Deshmukh",
              role: "Preventative Cardiology Specialist",
              hospital: "Lilavati Hospital & Research Centre, Mumbai",
              rating: 5,
              avatar: "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?auto=format&fit=crop&q=80&w=150",
            },
            {
              quote: "Eliminating opaque AI predictions allows our clinical review board to trust risk scores for early cardiovascular intervention.",
              name: "Dr. Arvind Chawla",
              role: "Director of Clinical Quality",
              hospital: "Medanta - The Medicity, Gurugram",
              rating: 5,
              avatar: "https://images.unsplash.com/photo-1612349317150-e413f6a5b16d?auto=format&fit=crop&q=80&w=150",
            },
            {
              quote: "The role-based interfaces for Doctors, Hospital Admins, and Patients made hospital-wide adoption seamless across our units.",
              name: "Sister Mary Varghese",
              role: "Chief Nursing Officer",
              hospital: "Manipal Hospital, Bengaluru",
              rating: 5,
              avatar: "https://images.unsplash.com/photo-1582750433449-648ed127bb54?auto=format&fit=crop&q=80&w=150",
            },
          ]}
        />
      </section>

      {/* ── BOTTOM INFO CARDS ────────────────────────────────────────────── */}
      <section className="lp-info-section lp-info-section--bottom" id="about">
        <div className="lp-wrap lp-info-grid">
          <div className="lp-info-card">
            <ShieldIcon />
            <h3 className="lp-info-card__h3">Clinically validated across<br />15+ research datasets</h3>
            <a href="#" className="lp-rm lp-rm--teal" onClick={onGetStarted}>Get Started <ArrowRight/></a>
          </div>
          <div className="lp-info-card">
            <BrainAIIcon />
            <h3 className="lp-info-card__h3">Automated model training<br />& live inference API</h3>
            <a href="#" className="lp-rm lp-rm--dark" onClick={onGetStarted}>Get Started <ArrowRight/></a>
          </div>
          <div className="lp-info-card">
            <DataChartIcon />
            <h3 className="lp-info-card__h3">Full audit trail for every<br />risk prediction made</h3>
            <a href="#" className="lp-rm lp-rm--dark" onClick={onGetStarted}>Get Started <ArrowRight/></a>
          </div>
        </div>
      </section>

      {/* ── NEWSLETTER / CTA ─────────────────────────────────────────────── */}
      <section className="lp-nl" id="contact">
        <svg className="lp-nl__hb" viewBox="0 0 1440 80" preserveAspectRatio="none" fill="none">
          <path d="M0 40h350l45-30 30 60 30-60 30 60 30-60 45 30h880" stroke="rgba(255,255,255,0.1)" strokeWidth="1.8"/>
        </svg>
        <div className="lp-wrap lp-nl__inner">
          <h2 className="lp-nl__h2">
            Ready to Transform Patient Care?<br/>
            Start with Medical Risk XAI Today
          </h2>
          <div className="lp-nl__underline"></div>
          <p className="lp-nl__sub">
            Join healthcare providers already using explainable AI to deliver better patient outcomes.
          </p>
          <button className="lp-nl__btn lp-nl__btn--large" onClick={onGetStarted}>
            Sign In to the Platform <ArrowRight/>
          </button>
        </div>
      </section>


      {/* ── FOOTER ──────────────────────────────────────────────────────── */}
      <section className="lp-footer-wrap">
        <div className="lp-wrap">
          <div className="lp-footer-card">
            {/* Brand */}
            <div className="lp-fc-brand">
              <div className="lp-fc-logo">
                <LogoIcon/>
                <span>Medical Risk XAI</span>
              </div>
              <p className="lp-fc-desc">
                An explainable AI platform for cardiovascular risk prediction — built for hospitals,
                trusted by clinicians.
              </p>
              <div className="lp-fc-socials">
                {[<FBIcon/>, <LIIcon/>, <IGIcon/>, <XIcon/>].map((ic,i) => (
                  <a key={i} href="#" className="lp-fc-social">{ic}</a>
                ))}
              </div>
            </div>

            {/* Page */}
            <div className="lp-fc-col">
              <h5 className="lp-fc-col__h">Platform</h5>
              <ul className="lp-fc-list">
                {[
                  { label:"About", href: "#about" },
                  { label:"Features", href: "#features" },
                  { label:"How It Works", href: "#how" },
                  { label:"Sign In", action: onGetStarted },
                ].map(item => (
                  <li key={item.label}>
                    {item.action ? (
                      <a href="#" onClick={(e)=>{e.preventDefault(); item.action();}}>{item.label}</a>
                    ) : (
                      <a href={item.href}>{item.label}</a>
                    )}
                  </li>
                ))}
              </ul>
            </div>

            {/* Link */}
            <div className="lp-fc-col">
              <h5 className="lp-fc-col__h">Legal</h5>
              <ul className="lp-fc-list">
                {["Terms & Conditions","Privacy Policy","HIPAA Compliance","Security"].map(t => (
                  <li key={t}><a href="#">{t}</a></li>
                ))}
              </ul>
            </div>

            {/* Contact */}
            <div className="lp-fc-col">
              <h5 className="lp-fc-col__h">Contact</h5>
              <ul className="lp-fc-contact">
                <li>
                  <MapPinSvg/>
                  <div>
                    <span>Address</span>
                    <strong>123 Medical Drive, Health City</strong>
                  </div>
                </li>
                <li>
                  <PhoneSvg/>
                  <div>
                    <span>Phone Number</span>
                    <strong>(603) 555-0123</strong>
                  </div>
                </li>
                <li>
                  <MailSvg/>
                  <div>
                    <span>Email</span>
                    <strong>info@medicalriskai.com</strong>
                  </div>
                </li>
              </ul>
            </div>
          </div>

          <p className="lp-footer-copy">© 2026 Medical Risk XAI. All rights reserved.</p>
        </div>
      </section>

    </div>
  );
}
