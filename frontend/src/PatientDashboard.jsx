import React, { useState, useEffect } from "react";
import { useAuth } from "./AuthContext";
import { apiRequest, downloadPdfReport } from "./api";
import { useToast } from "./ToastContext";
import { SkeletonCard } from "./Skeleton";
import EmptyState from "./EmptyState";
import CopyButton from "./CopyButton";

export default function PatientDashboard() {
  const [nearbyHospitals, setNearbyHospitals] = useState([]);
  const [emergencyLoading, setEmergencyLoading] = useState(false);
  const [userLocation, setUserLocation] = useState(null);
  const [assignedDoctorInfo, setAssignedDoctorInfo] = useState(null);
  const { auth } = useAuth();
  const toast = useToast();
  const [history, setHistory] = useState([]);
  const [diagnoses, setDiagnoses] = useState([]);
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [dataLoading, setDataLoading] = useState(true);
  const [pdfLoading, setPdfLoading] = useState(false);

  const [profile, setProfile] = useState({
    name: "",
    email: "",
    age: null,
    sex: null,
    phone_number: "",
    emergency_contact_name: "",
    emergency_contact_phone: "",
    address: "",
    assigned_doctor: "",
  });

  const loadNearbyHospitals = async (lat, lon) => {
    setEmergencyLoading(true);
    try {
      const data = await apiRequest(
        `/patient/hospitals/nearby?latitude=${lat}&longitude=${lon}&radius_km=100`,
        {},
        auth?.access_token
      ).catch(() => []);
      setNearbyHospitals(Array.isArray(data) ? data : []);
    } catch (err) {
      setNearbyHospitals([]);
    } finally {
      setEmergencyLoading(false);
    }
  };

  const handleEmergencyView = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const { latitude, longitude } = pos.coords;
          setUserLocation({ latitude, longitude });
          loadNearbyHospitals(latitude, longitude);
        },
        () => {
          loadNearbyHospitals(28.6139, 77.2090);
        }
      );
    } else {
      loadNearbyHospitals(28.6139, 77.2090);
    }
  };

  const loadData = async () => {
    try {
      const [hist, diags, me, allDocs] = await Promise.all([
        apiRequest("/patient/history", {}, auth?.access_token).catch(() => []),
        apiRequest("/patient/my-diagnoses", {}, auth?.access_token).catch(() => []),
        apiRequest("/auth/me", {}, auth?.access_token).catch(() => null),
        apiRequest("/doctor/all-doctors", {}, auth?.access_token).catch(() => []),
      ]);
      setHistory(hist);
      setDiagnoses(diags);
      if (me) {
        setProfile({
          name: me.name || "",
          email: me.email || "",
          age: me.age,
          sex: me.sex,
          phone_number: me.phone_number || "",
          emergency_contact_name: me.emergency_contact_name || "",
          emergency_contact_phone: me.emergency_contact_phone || "",
          address: me.address || "",
          assigned_doctor: me.assigned_doctor || "Hospital Medical Staff",
        });
        if (me.doctor_id && Array.isArray(allDocs)) {
          const doc = allDocs.find((d) => d.id === me.doctor_id);
          setAssignedDoctorInfo(doc || null);
        }
      }
    } catch (err) {
      setError(err.message);
      toast.error("We couldn't load your medical records. Please refresh and try again.");
    } finally {
      setDataLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleProfileSave = async (e) => {
    e.preventDefault();
    setMsg("");
    setError("");
    setLoading(true);
    try {
      await apiRequest(
        "/patient/profile",
        {
          method: "PUT",
          body: JSON.stringify({
            phone_number: profile.phone_number,
            emergency_contact_name: profile.emergency_contact_name,
            emergency_contact_phone: profile.emergency_contact_phone,
            address: profile.address,
          }),
        },
        auth?.access_token
      );
      setMsg("Contact details updated successfully.");
      toast.success("Contact details updated successfully.");
    } catch (err) {
      setError(err.message);
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadLatestPdf = async () => {
    setPdfLoading(true);
    try {
      await downloadPdfReport(
        `/reports/patient/${auth.id}/latest-pdf`,
        `medical_report_${(auth.name || "patient").toLowerCase().replace(/\s+/g, "_")}.pdf`,
        auth?.access_token
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setPdfLoading(false);
    }
  };

  const handleDownloadDiagnosisPdf = async (diagId) => {
    setPdfLoading(true);
    try {
      await downloadPdfReport(
        `/reports/diagnosis/${diagId}/pdf`,
        `diagnosis_report_${diagId}.pdf`,
        auth?.access_token
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setPdfLoading(false);
    }
  };

  return (
    <div className="container">
      {msg && <div className="alert alert-success">{msg}</div>}
      {error && <div className="alert alert-error">{error}</div>}

      {dataLoading ? (
        <>
          <SkeletonCard lines={2} />
          <SkeletonCard lines={3} />
          <SkeletonCard lines={4} />
        </>
      ) : (
      <>
      {/* Patient Profile Header */}
      <div
        className="card"
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          backgroundColor: "#f8fafc",
          border: "1px solid #cbd5e1",
          flexWrap: "wrap",
          gap: 8,
        }}
      >
        <div>
          <h2 style={{ margin: "0 0 4px" }}>Welcome, {auth.name}</h2>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", fontSize: "0.85rem", color: "#475569" }}>
            <span>Patient ID: <strong>{auth.id}</strong></span>
            <CopyButton text={String(auth.id)} label="" />
            <span style={{ margin: "0 4px" }}>|</span>
            <span>Age: {profile.age ? `${profile.age} years` : "Recorded in evaluation"}</span>
            <span style={{ margin: "0 4px" }}>|</span>
            <span>Sex: {profile.sex !== null && profile.sex !== undefined ? (profile.sex === 1 ? "Male" : "Female") : "Recorded"}</span>
            <span className="badge badge-neutral">Demographics Verified</span>
          </div>
        </div>

        <button
          type="button"
          onClick={handleDownloadLatestPdf}
          disabled={pdfLoading}
          style={{ backgroundColor: "#15803d", borderColor: "#15803d" }}
        >
          {pdfLoading ? "Generating..." : "Download Medical Report (PDF)"}
        </button>
      </div>

      {/* Assigned Doctor Qualifications Card */}
      {assignedDoctorInfo && (
        <div className="card" style={{ borderLeft: "4px solid #0284c7", backgroundColor: "#f0f9ff" }}>
          <div style={{ display: "flex", alignItems: "flex-start", gap: 16 }}>
            <div style={{ width: 48, height: 48, borderRadius: "50%", backgroundColor: "#0284c7", display: "flex", alignItems: "center", justifyContent: "center", color: "white", fontWeight: 700, fontSize: "1.2rem", flexShrink: 0 }}>
              {(assignedDoctorInfo.name || "D").charAt(0)}
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                <strong style={{ fontSize: "1rem", color: "#0c4a6e" }}>Dr. {assignedDoctorInfo.name}</strong>
                <span className="badge badge-neutral">{assignedDoctorInfo.specialization || "Physician"}</span>
              </div>
              {assignedDoctorInfo.degree && (
                <div style={{ fontSize: "0.82rem", color: "#334155", marginBottom: 2 }}>
                  🎓 <strong>Qualifications:</strong> {assignedDoctorInfo.degree}
                </div>
              )}
              {assignedDoctorInfo.years_of_experience && (
                <div style={{ fontSize: "0.82rem", color: "#334155", marginBottom: 2 }}>
                  ⏱️ <strong>Experience:</strong> {assignedDoctorInfo.years_of_experience} years
                </div>
              )}
              {assignedDoctorInfo.certifications && (
                <div style={{ fontSize: "0.82rem", color: "#475569" }}>
                  🏅 <strong>Certifications:</strong> {assignedDoctorInfo.certifications}
                </div>
              )}
              {assignedDoctorInfo.license_number && (
                <div style={{ fontSize: "0.75rem", color: "#64748b", marginTop: 4 }}>License: {assignedDoctorInfo.license_number}</div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Emergency: Nearby Hospital Directory */}
      <div className="card" style={{ borderColor: "#dc2626", backgroundColor: "#fef2f2" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <h3 style={{ margin: 0, color: "#991b1b" }}>Emergency: Nearby Hospitals</h3>
          <button
            type="button"
            onClick={handleEmergencyView}
            disabled={emergencyLoading}
            style={{ backgroundColor: "#dc2626", borderColor: "#dc2626", color: "white", fontSize: "0.8rem", padding: "6px 12px" }}
          >
            {emergencyLoading ? "Locating..." : "Find Nearby Hospitals"}
          </button>
        </div>

        {nearbyHospitals.length > 0 ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {nearbyHospitals.map((h) => (
              <div key={h.id} style={{ padding: 12, backgroundColor: "white", border: "1px solid #fecaca", borderRadius: 4 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div>
                    <strong style={{ fontSize: "1rem", color: "#991b1b" }}>{h.name}</strong>
                    <div style={{ fontSize: "0.85rem", color: "#475569" }}>{h.address}</div>
                    <div style={{ fontSize: "0.85rem", color: "#0369a1", marginTop: 2 }}>📞 {h.contact_number}</div>
                  </div>
                  {h.distance_km && (
                    <span className="badge badge-high">{h.distance_km} km</span>
                  )}
                </div>
                <div style={{ display: "flex", gap: 12, marginTop: 8, flexWrap: "wrap", fontSize: "0.8rem" }}>
                  <span style={{ color: h.available_beds > 0 ? "#16a34a" : "#dc2626" }}>🛏️ Beds: {h.available_beds}</span>
                  <span style={{ color: h.icu_beds_available > 0 ? "#16a34a" : "#dc2626" }}>ICU: {h.icu_beds_available}</span>
                  <span style={{ color: h.ventilators_available > 0 ? "#16a34a" : "#dc2626" }}>💨 Ventilators: {h.ventilators_available}</span>
                  <span style={{ color: h.blood_bank_available ? "#16a34a" : "#dc2626" }}>🩸 Blood Bank: {h.blood_bank_available ? "Available" : "Unavailable"}</span>
                  <span style={{ color: h.emergency_services_available ? "#16a34a" : "#dc2626" }}>🚑 Emergency: {h.emergency_services_available ? "Open" : "Closed"}</span>
                </div>
                {h.doctor_availability && h.doctor_availability.length > 0 && (
                  <div style={{ marginTop: 8, fontSize: "0.8rem", color: "#475569" }}>
                    <strong>Available Specialists:</strong>
                    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 4 }}>
                      {h.doctor_availability.map((a) => (
                        <span key={a.id} className="badge badge-med">{a.specialization}: {a.available_doctors} doctors</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p style={{ fontSize: "0.85rem", color: "#64748b" }}>Click "Find Nearby Hospitals" to locate emergency services.</p>
        )}
      </div>

      {/* Doctor Diagnoses Section */}
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <h3 style={{ margin: 0 }}>Doctor Diagnoses & Prescriptions</h3>
          <span style={{ fontSize: "0.8rem", color: "#64748b" }}>{diagnoses.length} recorded</span>
        </div>

        {diagnoses.length === 0 ? (
          <EmptyState
            icon="\u{1F48A}"
            title="No diagnoses yet"
            description="Your attending doctor's diagnoses and prescriptions will appear here."
          />
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {diagnoses.map((diag) => (
              <div
                key={diag.id}
                style={{
                  padding: 12,
                  backgroundColor: "#ffffff",
                  border: "1px solid #e2e8f0",
                  borderRadius: 3,
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 6 }}>
                  <div>
                    <h4 style={{ margin: "0 0 2px", fontSize: "0.95rem" }}>{diag.diagnosis_title}</h4>
                    <span style={{ fontSize: "0.75rem", color: "#64748b" }}>
                      Attending: Dr. {diag.doctor_name} ({diag.doctor_specialization || "Physician"}) - {diag.created_at}
                    </span>
                  </div>
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => handleDownloadDiagnosisPdf(diag.id)}
                    disabled={pdfLoading}
                    style={{ fontSize: "0.75rem", padding: "3px 8px" }}
                  >
                    Export PDF
                  </button>
                </div>

                <div style={{ fontSize: "0.85rem", color: "#334155", marginBottom: 4 }}>
                  <strong>Notes:</strong> {diag.clinical_notes}
                </div>

                {diag.treatment_plan && (
                  <div style={{ fontSize: "0.8rem", color: "#475569", marginTop: 2 }}>
                    <strong>Plan:</strong> {diag.treatment_plan}
                  </div>
                )}

                {diag.prescriptions && (
                  <div style={{ fontSize: "0.8rem", color: "#0369a1", marginTop: 2 }}>
                    <strong>Rx:</strong> {diag.prescriptions}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Patient Contact & Profile Form */}
      <div className="card">
        <h3>Contact & Emergency Details</h3>
        <form className="form" onSubmit={handleProfileSave}>
          <div className="form-grid">
            <div className="form-group">
              <label>Phone Number</label>
              <input
                type="text"
                value={profile.phone_number}
                onChange={(e) => setProfile({ ...profile, phone_number: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label>Emergency Contact Name</label>
              <input
                type="text"
                value={profile.emergency_contact_name}
                onChange={(e) => setProfile({ ...profile, emergency_contact_name: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label>Emergency Contact Phone</label>
              <input
                type="text"
                value={profile.emergency_contact_phone}
                onChange={(e) => setProfile({ ...profile, emergency_contact_phone: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label>Address</label>
              <input
                type="text"
                value={profile.address}
                onChange={(e) => setProfile({ ...profile, address: e.target.value })}
              />
            </div>
          </div>
          <button type="submit" disabled={loading} style={{ alignSelf: "flex-start" }}>
            {loading ? "Saving..." : "Save Details"}
          </button>
        </form>
      </div>

      {/* Assessment History Table */}
      <div className="card">
        <h3>Cardiovascular Risk History</h3>
        {history.length === 0 ? (
          <EmptyState
            icon="\u{1F4CA}"
            title="No assessments yet"
            description="Your cardiovascular risk assessments will appear here once recorded."
          />
        ) : (
          <div className="table-wrapper">
            <table className="table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Risk Level</th>
                  <th>Probability</th>
                  <th>Age</th>
                  <th>Blood Pressure</th>
                  <th>BMI</th>
                  <th>Top Contributing Factors</th>
                </tr>
              </thead>
              <tbody>
                {history.map((h) => (
                  <tr key={h.id}>
                    <td>{h.created_at}</td>
                    <td>
                      <span
                        className={`badge ${
                          h.risk_level === "High Risk"
                            ? "badge-high"
                            : h.risk_level === "Moderate Risk"
                            ? "badge-med"
                            : "badge-low"
                        }`}
                      >
                        {h.risk_level}
                      </span>
                    </td>
                    <td>{h.risk_probability}%</td>
                    <td>{h.age ?? "-"}</td>
                    <td>{h.systolic_bp && h.diastolic_bp ? `${h.systolic_bp}/${h.diastolic_bp}` : (h.resting_bp ?? "-")}</td>
                    <td>{h.bmi ?? "-"}</td>
                    <td style={{ fontSize: "0.8rem", color: "#475569" }}>{h.top_features || "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      </>
      )}
    </div>
  );
}
