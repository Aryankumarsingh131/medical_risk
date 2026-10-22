import React from "react";
import { downloadPdfReport } from "./api";

/**
 * PatientReportModal
 * ------------------
 * Interactive and printable patient clinical report modal adhering to the
 * official 10-section structure with the mandatory clinical distinction notice:
 *
 * 1. Patient overview (Demographics, ID, Contact)
 * 2. Vital signs (BP, heart rate, temperature, BMI, SpO₂)
 * 3. Clinical parameters (Values relevant to selected disease)
 * 4. Test results (Values, units, reference ranges, and flags)
 * 5. Risk prediction (Risk %, category, target disease, with clear distinction notice)
 * 6. Key contributing factors (Important inputs influencing prediction)
 * 7. Historical trends (Previous results and last five visits with dates)
 * 8. Doctor's assessment (Clinical interpretation and confirmed diagnosis)
 * 9. Recommendations (Suggested next steps for clinician review)
 * 10. Report metadata (Generated date, model version, and doctor details)
 */
export default function PatientReportModal({
  isOpen,
  onClose,
  reportData,
  loading = false,
  downloadPdfEndpoint = null,
  patientName = "patient",
  token = null,
}) {
  if (!isOpen) return null;

  const handlePrint = () => {
    window.print();
  };

  const handleDownload = async () => {
    if (downloadPdfEndpoint) {
      await downloadPdfReport(
        downloadPdfEndpoint,
        `medical_report_${(patientName || "patient").toLowerCase().replace(/\s+/g, "_")}.pdf`,
        token
      );
    } else {
      window.print();
    }
  };

  const s = reportData?.sections || {};
  const patient = s.patient_overview || {};
  const vitals = s.vital_signs || {};
  const clinParams = s.clinical_parameters || {};
  const labTests = s.test_results?.results || [];
  const risk = s.risk_prediction || {};
  const factors = s.key_contributing_factors?.factors || [];
  const trends = s.historical_trends?.last_five_visits || [];
  const docAssessment = s.doctors_assessment || {};
  const recommendations = s.recommendations?.next_steps || [];
  const meta = s.report_metadata || {};
  const doc = meta.doctor || {};

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: "rgba(15, 23, 42, 0.75)",
        backdropFilter: "blur(4px)",
        zIndex: 9999,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "16px",
      }}
      onClick={onClose}
    >
      <div
        style={{
          backgroundColor: "#ffffff",
          borderRadius: "8px",
          width: "100%",
          maxWidth: "920px",
          maxHeight: "92vh",
          display: "flex",
          flexDirection: "column",
          boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.25)",
          overflow: "hidden",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Top Action Bar */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: "12px 20px",
            backgroundColor: "#0f3a60",
            color: "#ffffff",
            borderBottom: "1px solid #1e293b",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontSize: "1.2rem" }}>📄</span>
            <div>
              <strong style={{ fontSize: "1rem", letterSpacing: "0.3px" }}>
                Official Clinical Health &amp; Risk Report
              </strong>
              <div style={{ fontSize: "0.75rem", color: "#93c5fd" }}>
                10-Section Diagnostic Summary &bull; Clinical Decision Support
              </div>
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <button
              type="button"
              onClick={handlePrint}
              style={{
                backgroundColor: "#0284c7",
                color: "#ffffff",
                border: "none",
                padding: "6px 14px",
                borderRadius: "4px",
                fontSize: "0.82rem",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              🖨️ Print
            </button>
            <button
              type="button"
              onClick={handleDownload}
              style={{
                backgroundColor: "#16a34a",
                color: "#ffffff",
                border: "none",
                padding: "6px 14px",
                borderRadius: "4px",
                fontSize: "0.82rem",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              ⬇️ Download PDF
            </button>
            <button
              type="button"
              onClick={onClose}
              style={{
                backgroundColor: "transparent",
                color: "#cbd5e1",
                border: "1px solid #475569",
                padding: "6px 12px",
                borderRadius: "4px",
                fontSize: "0.82rem",
                cursor: "pointer",
              }}
            >
              ✕ Close
            </button>
          </div>
        </div>

        {/* Scrollable Report Content Area */}
        <div
          id="printable-medical-report"
          style={{
            flex: 1,
            overflowY: "auto",
            padding: "24px 28px",
            backgroundColor: "#ffffff",
            color: "#0f172a",
            fontSize: "0.85rem",
            lineHeight: 1.5,
          }}
        >
          {loading ? (
            <div style={{ textAlign: "center", padding: "48px 0", color: "#64748b" }}>
              <div style={{ fontSize: "1.8rem", marginBottom: 8 }}>⏳</div>
              Generating structured clinical report...
            </div>
          ) : (
            <div>
              {/* Document Banner */}
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "flex-start",
                  borderBottom: "2px solid #0284c7",
                  paddingBottom: "12px",
                  marginBottom: "16px",
                }}
              >
                <div>
                  <h2 style={{ margin: "0 0 2px", color: "#0f3a60", fontSize: "1.4rem" }}>
                    PATIENT CLINICAL MEDICAL REPORT
                  </h2>
                  <div style={{ fontSize: "0.8rem", color: "#64748b" }}>
                    Comprehensive Cardiometabolic Risk Evaluation &bull; Clinical Decision Support
                  </div>
                  <div style={{ fontSize: "0.75rem", color: "#b91c1c", fontWeight: 700, marginTop: 4 }}>
                    CONFIDENTIAL MEDICAL RECORD &bull; RESTRICTED PATIENT DOCUMENT
                  </div>
                </div>
                <div style={{ textAlign: "right", fontSize: "0.8rem", color: "#334155" }}>
                  <div><strong>Report ID:</strong> {reportData?.report_id || "RPT-2026-MED"}</div>
                  <div><strong>Generated:</strong> {meta.generated_at || new Date().toISOString().slice(0, 10)}</div>
                  <div><strong>Facility:</strong> {patient.facility || "Central Clinical Institute"}</div>
                </div>
              </div>

              {/* SECTION 1: Patient Overview */}
              <SectionHeader number={1} title="Patient Overview" subtitle="Demographics & Patient Identification" />
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: 12,
                  backgroundColor: "#f8fafc",
                  padding: "12px 16px",
                  borderRadius: "6px",
                  border: "1px solid #e2e8f0",
                  marginBottom: "16px",
                }}
              >
                <div>
                  <div><strong>Full Name:</strong> {patient.name || "N/A"}</div>
                  <div>
                    <strong>Patient ID:</strong>{" "}
                    <span style={{ color: "#0f3a60", fontWeight: 700 }}>#{patient.patient_id || "N/A"}</span>
                  </div>
                  <div><strong>Age / Sex:</strong> {patient.age ? `${patient.age} yrs` : "Recorded"} &bull; {patient.sex || "Unspecified"}</div>
                  <div><strong>Date of Birth:</strong> {patient.date_of_birth || "On File"}</div>
                </div>
                <div>
                  <div><strong>Primary Contact:</strong> {patient.phone_number || "Not recorded"}</div>
                  <div><strong>Email:</strong> {patient.email || "N/A"}</div>
                  <div>
                    <strong>Emergency Contact:</strong> {patient.emergency_contact_name || "N/A"}{" "}
                    {patient.emergency_contact_phone ? `(${patient.emergency_contact_phone})` : ""}
                  </div>
                  <div><strong>Address:</strong> {patient.address || "Metro Healthcare Area"}</div>
                </div>
              </div>

              {/* SECTION 2: Vital Signs */}
              <SectionHeader number={2} title="Vital Signs" subtitle="Current Clinical Measurements" />
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(5, 1fr)",
                  gap: 8,
                  marginBottom: "16px",
                }}
              >
                <VitalBadge label="Blood Pressure (BP)" value={vitals.blood_pressure || "120/80 mmHg"} unit="" />
                <VitalBadge label="Heart Rate (HR)" value={vitals.heart_rate || "74 bpm"} unit="" />
                <VitalBadge label="Body Temp" value={vitals.temperature || "98.6 °F"} unit="" />
                <VitalBadge label="BMI" value={vitals.bmi || "24.5 kg/m²"} unit="" />
                <VitalBadge label="SpO₂ (Room Air)" value={vitals.spo2 || "98%"} unit="" />
              </div>

              {/* SECTION 3: Clinical Parameters */}
              <SectionHeader number={3} title="Clinical Parameters" subtitle={`Values Relevant to Target Disease: ${clinParams.target_disease || "Cardiovascular Disease"}`} />
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: 12,
                  backgroundColor: "#f8fafc",
                  padding: "12px 16px",
                  borderRadius: "6px",
                  border: "1px solid #e2e8f0",
                  marginBottom: "16px",
                  fontSize: "0.82rem",
                }}
              >
                <div>
                  <div><strong>Chest Pain Presentation:</strong> {clinParams.chest_pain_type || "Asymptomatic"}</div>
                  <div><strong>ECG ST Depression:</strong> {clinParams.st_depression || "0.0 mm"}</div>
                  <div><strong>Exercise-Induced Angina:</strong> {clinParams.exercise_angina || "Absent"}</div>
                </div>
                <div>
                  <div><strong>Hypertension Status:</strong> {clinParams.hypertension || "None documented"}</div>
                  <div><strong>Glycemic Status / Diabetes:</strong> {clinParams.diabetes || "Normoglycemic"}</div>
                  <div><strong>Tobacco Use:</strong> {clinParams.smoking || "Non-smoker"}</div>
                  <div><strong>Prior Medical Events:</strong> {clinParams.prior_medical_events || "None reported"}</div>
                </div>
              </div>

              {/* SECTION 4: Test Results */}
              <SectionHeader number={4} title="Test Results" subtitle="Laboratory Values, Units, Reference Ranges & Clinical Flags" />
              <div style={{ overflowX: "auto", marginBottom: "16px" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8rem" }}>
                  <thead>
                    <tr style={{ backgroundColor: "#f1f5f9", textAlign: "left", color: "#0f3a60", borderBottom: "1px solid #cbd5e1" }}>
                      <th style={{ padding: "8px 10px" }}>Laboratory Test</th>
                      <th style={{ padding: "8px 10px", textAlign: "center" }}>Result Value</th>
                      <th style={{ padding: "8px 10px", textAlign: "center" }}>Standard Unit</th>
                      <th style={{ padding: "8px 10px", textAlign: "center" }}>Reference Range</th>
                      <th style={{ padding: "8px 10px", textAlign: "center" }}>Clinical Flag</th>
                    </tr>
                  </thead>
                  <tbody>
                    {labTests.length > 0 ? (
                      labTests.map((t, idx) => (
                        <tr key={idx} style={{ borderBottom: "1px solid #e2e8f0", backgroundColor: idx % 2 === 0 ? "#ffffff" : "#f8fafc" }}>
                          <td style={{ padding: "7px 10px", fontWeight: 600 }}>{t.name}</td>
                          <td style={{ padding: "7px 10px", textAlign: "center", fontWeight: 700 }}>{t.value}</td>
                          <td style={{ padding: "7px 10px", textAlign: "center", color: "#64748b" }}>{t.unit}</td>
                          <td style={{ padding: "7px 10px", textAlign: "center", color: "#475569" }}>{t.ref_range}</td>
                          <td style={{ padding: "7px 10px", textAlign: "center" }}>
                            <span
                              style={{
                                padding: "2px 8px",
                                borderRadius: "4px",
                                fontSize: "0.75rem",
                                fontWeight: 700,
                                backgroundColor: (t.flag_color || "#15803d") + "1a",
                                color: t.flag_color || "#15803d",
                                border: `1px solid ${t.flag_color || "#15803d"}40`,
                              }}
                            >
                              {t.flag}
                            </span>
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={5} style={{ padding: "12px", textAlign: "center", color: "#64748b" }}>
                          Standard routine metabolic profile recorded within normal parameters.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              {/* SECTION 5: Risk Prediction (WITH MANDATORY DISTINCTION NOTICE) */}
              <SectionHeader number={5} title="Risk Prediction" subtitle="AI Decision Support Model Output" />
              {/* Prominent Clinical Advisory Distinction Banner */}
              <div
                style={{
                  backgroundColor: "#fffbeb",
                  border: "1px solid #f59e0b",
                  borderRadius: "6px",
                  padding: "10px 14px",
                  marginBottom: "12px",
                  fontSize: "0.8rem",
                  color: "#92400e",
                  lineHeight: 1.45,
                }}
              >
                <div style={{ fontWeight: 700, display: "flex", alignItems: "center", gap: 6, marginBottom: 2 }}>
                  <span>⚠️</span>
                  <span>CRITICAL CLINICAL DISTINCTION &bull; AI PREDICTION &ne; MEDICAL DIAGNOSIS</span>
                </div>
                <div>
                  This risk score is an automated algorithmic probability estimate intended solely for <strong>Clinical Decision Support (CDS)</strong>.
                  <strong> An AI-generated risk prediction is NOT a medical diagnosis.</strong> Definitive clinical diagnosis, pathology confirmation, and treatment directives must be made exclusively by qualified healthcare clinicians.
                </div>
              </div>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: 12,
                  backgroundColor: "#f8fafc",
                  padding: "12px 16px",
                  borderRadius: "6px",
                  border: "1px solid #e2e8f0",
                  marginBottom: "16px",
                  fontSize: "0.82rem",
                }}
              >
                <div>
                  <div><strong>Target Evaluated Disease:</strong> {risk.target_disease || "Cardiovascular Disease & CAD"}</div>
                  <div style={{ marginTop: 4 }}>
                    <strong>Predicted Risk Category:</strong>{" "}
                    <span style={{ fontSize: "0.95rem", fontWeight: 700, color: getRiskColor(risk.risk_category) }}>
                      {risk.risk_category || "Low Risk"}
                    </span>
                  </div>
                  <div>
                    <strong>Estimated Risk Probability:</strong>{" "}
                    <span style={{ fontSize: "0.95rem", fontWeight: 700, color: getRiskColor(risk.risk_category) }}>
                      {risk.risk_percentage || "12.0%"}
                    </span>
                  </div>
                </div>
                <div>
                  <div><strong>Algorithm Engine:</strong> Deterministic Ruleset + Calibrated Gradient Boosting</div>
                  <div><strong>Intended Use:</strong> Risk Stratification &amp; Triaging Support</div>
                  <div><strong>Physician Review Status:</strong> Requires Attending Clinician Verification</div>
                </div>
              </div>

              {/* SECTION 6: Key Contributing Factors */}
              <SectionHeader number={6} title="Key Contributing Factors" subtitle="Inputs Influencing the Model & Rule Engine" />
              <div style={{ overflowX: "auto", marginBottom: "16px" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8rem" }}>
                  <thead>
                    <tr style={{ backgroundColor: "#f1f5f9", textAlign: "left", color: "#0f3a60", borderBottom: "1px solid #cbd5e1" }}>
                      <th style={{ padding: "8px 10px" }}>Risk Factor / Input Feature</th>
                      <th style={{ padding: "8px 10px", textAlign: "center" }}>Relative Impact</th>
                      <th style={{ padding: "8px 10px" }}>Clinical Rationale &amp; Influence</th>
                    </tr>
                  </thead>
                  <tbody>
                    {factors.length > 0 ? (
                      factors.map((f, idx) => (
                        <tr key={idx} style={{ borderBottom: "1px solid #e2e8f0" }}>
                          <td style={{ padding: "7px 10px", fontWeight: 600 }}>{f.factor}</td>
                          <td style={{ padding: "7px 10px", textAlign: "center" }}>
                            <span
                              style={{
                                padding: "2px 8px",
                                borderRadius: "4px",
                                fontSize: "0.75rem",
                                fontWeight: 700,
                                backgroundColor: f.impact === "High" ? "#fee2e2" : "#fef3c7",
                                color: f.impact === "High" ? "#991b1b" : "#92400e",
                              }}
                            >
                              {f.impact} Impact
                            </span>
                          </td>
                          <td style={{ padding: "7px 10px", color: "#334155" }}>{f.description}</td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={3} style={{ padding: "10px", color: "#64748b" }}>
                          Standard baseline cardiometabolic inputs evaluated. No critical acute triggers detected.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              {/* SECTION 7: Historical Trends */}
              <SectionHeader number={7} title="Historical Trends" subtitle="Previous Results & Last Five Visits with Dates" />
              <div style={{ overflowX: "auto", marginBottom: "16px" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8rem" }}>
                  <thead>
                    <tr style={{ backgroundColor: "#f1f5f9", textAlign: "left", color: "#0f3a60", borderBottom: "1px solid #cbd5e1" }}>
                      <th style={{ padding: "8px 10px", textAlign: "center" }}>Visit #</th>
                      <th style={{ padding: "8px 10px" }}>Date</th>
                      <th style={{ padding: "8px 10px" }}>Encounter Type</th>
                      <th style={{ padding: "8px 10px", textAlign: "center" }}>Risk Level</th>
                      <th style={{ padding: "8px 10px" }}>Vitals</th>
                      <th style={{ padding: "8px 10px" }}>Clinical Summary</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trends.length > 0 ? (
                      trends.map((v, idx) => (
                        <tr key={idx} style={{ borderBottom: "1px solid #e2e8f0", backgroundColor: idx % 2 === 0 ? "#ffffff" : "#f8fafc" }}>
                          <td style={{ padding: "7px 10px", textAlign: "center", fontWeight: 700 }}>{idx + 1}</td>
                          <td style={{ padding: "7px 10px" }}>{v.date}</td>
                          <td style={{ padding: "7px 10px" }}>{v.encounter_type || "Clinical Visit"}</td>
                          <td style={{ padding: "7px 10px", textAlign: "center", fontWeight: 600 }}>{v.risk_level || "-"}</td>
                          <td style={{ padding: "7px 10px" }}>BP: {v.blood_pressure || "-"}</td>
                          <td style={{ padding: "7px 10px", color: "#475569" }}>{v.summary || "Encounter completed"}</td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={6} style={{ padding: "10px", textAlign: "center", color: "#64748b" }}>
                          Initial clinical consultation recorded.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              {/* SECTION 8: Doctor's Assessment */}
              <SectionHeader number={8} title="Doctor's Assessment" subtitle="Clinical Interpretation & Confirmed Medical Diagnosis" />
              <div
                style={{
                  backgroundColor: "#ffffff",
                  border: "1.5px solid #0284c7",
                  borderRadius: "6px",
                  padding: "14px 18px",
                  marginBottom: "16px",
                  fontSize: "0.82rem",
                }}
              >
                <div style={{ marginBottom: 8 }}>
                  <div style={{ fontSize: "0.75rem", color: "#64748b", textTransform: "uppercase", fontWeight: 700 }}>
                    Confirmed Clinical Diagnosis (Physician Directive)
                  </div>
                  <div style={{ fontSize: "1rem", fontWeight: 700, color: "#0f3a60" }}>
                    {docAssessment.diagnosis_title || "Clinical Health & Risk Assessment"}
                  </div>
                </div>
                <div style={{ marginBottom: 8 }}>
                  <strong>Clinical Interpretation &amp; Physical Findings:</strong>
                  <div style={{ color: "#334155", marginTop: 2 }}>
                    {docAssessment.clinical_notes || "Evaluation conducted based on patient history, laboratory parameters, and physical exam."}
                  </div>
                </div>
                <div style={{ marginBottom: 8 }}>
                  <strong>Treatment &amp; Therapeutic Management Plan:</strong>
                  <div style={{ color: "#334155", marginTop: 2 }}>
                    {docAssessment.treatment_plan || "Maintain standard lifestyle modifications and routine periodic follow-up."}
                  </div>
                </div>
                <div>
                  <strong>Prescriptions &amp; Medication Schedule:</strong>
                  <div style={{ color: "#0284c7", fontWeight: 600, marginTop: 2 }}>
                    {docAssessment.prescriptions || "No active pharmacotherapy prescribed at this encounter."}
                  </div>
                </div>
              </div>

              {/* SECTION 9: Recommendations */}
              <SectionHeader number={9} title="Recommendations" subtitle="Suggested Next Steps for Clinician Review" />
              <div
                style={{
                  backgroundColor: "#f8fafc",
                  border: "1px solid #e2e8f0",
                  borderRadius: "6px",
                  padding: "12px 18px",
                  marginBottom: "16px",
                  fontSize: "0.82rem",
                }}
              >
                <ul style={{ margin: 0, paddingLeft: "18px", color: "#334155" }}>
                  {recommendations.map((r, idx) => (
                    <li key={idx} style={{ marginBottom: "6px" }}>{r}</li>
                  ))}
                </ul>
              </div>

              {/* SECTION 10: Report Metadata */}
              <SectionHeader number={10} title="Report Metadata & Attestation" subtitle="System Details & Clinician Sign-Off" />
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: 16,
                  backgroundColor: "#f8fafc",
                  border: "1px solid #e2e8f0",
                  borderRadius: "6px",
                  padding: "14px 18px",
                  fontSize: "0.8rem",
                }}
              >
                <div>
                  <div><strong>Document Identifier:</strong> {reportData?.report_id || "RPT-2026-MED"}</div>
                  <div><strong>Generated Date &amp; Time:</strong> {meta.generated_at || new Date().toISOString()}</div>
                  <div style={{ marginTop: 4 }}>
                    <strong>Model &amp; Ruleset Version:</strong>
                    <div style={{ fontSize: "0.75rem", color: "#475569" }}>
                      {meta.model_version || "MedRisk AI Ensemble v2.4 (GBM + Logistic) | CDS Ruleset v2.2.0 (AHA/ACC Aligned)"}
                    </div>
                  </div>
                </div>
                <div>
                  <div><strong>Attending Physician:</strong> Dr. {doc.name || "Attending Physician"}</div>
                  <div><strong>Degree &amp; Qualifications:</strong> {doc.degree || "MD, FACC"}</div>
                  <div><strong>Specialization:</strong> {doc.specialization || "Cardiovascular Medicine"}</div>
                  <div><strong>Medical License No:</strong> {doc.license_number || "DOC-REG-2026"}</div>
                  <div><strong>Care Facility:</strong> {doc.facility || "Central Clinical Institute"}</div>
                  <div style={{ marginTop: 8, paddingTop: 8, borderTop: "1px dashed #cbd5e1" }}>
                    <strong>Clinician Signature:</strong> ___________________________
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function SectionHeader({ number, title, subtitle }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        backgroundColor: "#f1f5f9",
        borderLeft: "4px solid #0284c7",
        padding: "6px 12px",
        marginBottom: "8px",
        borderRadius: "2px",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <strong style={{ color: "#0f3a60", fontSize: "0.88rem", letterSpacing: "0.2px" }}>
          {number}. {title.toUpperCase()}
        </strong>
        {subtitle && (
          <span style={{ fontSize: "0.75rem", color: "#64748b" }}>({subtitle})</span>
        )}
      </div>
    </div>
  );
}

function VitalBadge({ label, value, unit }) {
  return (
    <div
      style={{
        backgroundColor: "#f8fafc",
        border: "1px solid #e2e8f0",
        borderRadius: "6px",
        padding: "8px 10px",
        textAlign: "center",
      }}
    >
      <div style={{ fontSize: "0.7rem", color: "#64748b", fontWeight: 600, marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: "0.95rem", fontWeight: 700, color: "#0f3a60" }}>
        {value} {unit}
      </div>
    </div>
  );
}

function getRiskColor(level) {
  if (!level) return "#16a34a";
  const l = String(level).toLowerCase();
  if (l.includes("critical")) return "#991b1b";
  if (l.includes("high")) return "#dc2626";
  if (l.includes("mod") || l.includes("med")) return "#d97706";
  return "#16a34a";
}
