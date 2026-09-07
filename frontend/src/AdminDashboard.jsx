import React, { useState, useEffect } from "react";
import { useAuth } from "./AuthContext";
import { apiRequest, downloadPdfReport } from "./api";

export default function AdminDashboard() {
  const { auth } = useAuth();
  const [users, setUsers] = useState([]);
  const [overview, setOverview] = useState(null);
  const [activities, setActivities] = useState([]);
  const [medicineRequests, setMedicineRequests] = useState([]);
  const [pendingPatients, setPendingPatients] = useState([]);
  const [hospitals, setHospitals] = useState([]);
  const [procureQuantities, setProcureQuantities] = useState({});
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  const [reassignSelections, setReassignSelections] = useState({});
  const [pdfLoading, setPdfLoading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [showHospitalModal, setShowHospitalModal] = useState(false);
  const [editingHospital, setEditingHospital] = useState(null);

  const [docForm, setDocForm] = useState({
    name: "",
    email: "",
    password: "",
    specialization: "",
    license_number: "",
  });

  const [patForm, setPatForm] = useState({
    name: "",
    email: "",
    password: "",
    doctor_id: "",
  });

  const [hospitalForm, setHospitalForm] = useState({
    name: "",
    address: "",
    contact_number: "",
    latitude: "",
    longitude: "",
    available_beds: 0,
    icu_beds_available: 0,
    ventilators_available: 0,
    blood_bank_available: false,
    emergency_services_available: true,
  });

  const loadData = async () => {
    try {
      const [usersData, overviewData, activityData, medRequests, pendPats, hospitalsData] = await Promise.all([
        apiRequest("/admin/users", {}, auth?.access_token),
        apiRequest("/admin/overview", {}, auth?.access_token),
        apiRequest("/admin/activity", {}, auth?.access_token),
        apiRequest("/admin/medicine-requests", {}, auth?.access_token).catch(() => []),
        apiRequest("/admin/pending-patients", {}, auth?.access_token).catch(() => []),
        apiRequest("/admin/hospitals", {}, auth?.access_token).catch(() => []),
      ]);
      setUsers(usersData);
      setOverview(overviewData);
      setActivities(activityData);
      setMedicineRequests(medRequests);
      setPendingPatients(pendPats);
      setHospitals(hospitalsData);
    } catch (err) {
      setError(err.message);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleAddDoctor = async (e) => {
    e.preventDefault();
    setError("");
    setMsg("");
    try {
      await apiRequest(
        "/admin/doctors",
        {
          method: "POST",
          body: JSON.stringify(docForm),
        },
        auth?.access_token
      );
      setMsg(`Doctor ${docForm.name} registered successfully.`);
      setDocForm({ name: "", email: "", password: "", specialization: "", license_number: "" });
      loadData();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleAddPatient = async (e) => {
    e.preventDefault();
    setError("");
    setMsg("");
    try {
      await apiRequest(
        "/admin/patients",
        {
          method: "POST",
          body: JSON.stringify({
            ...patForm,
            doctor_id: patForm.doctor_id ? parseInt(patForm.doctor_id, 10) : null,
          }),
        },
        auth?.access_token
      );
      setMsg(`Patient ${patForm.name} registered successfully.`);
      setPatForm({ name: "", email: "", password: "", doctor_id: "" });
      loadData();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleReassignDoctor = async (patientId) => {
    const newDocId = reassignSelections[patientId];
    if (!newDocId) {
      setError("Please select a target doctor from the dropdown before transferring.");
      return;
    }
    setError("");
    setMsg("");
    try {
      const res = await apiRequest(
        `/admin/patients/${patientId}/reassign-doctor`,
        {
          method: "PUT",
          body: JSON.stringify({ new_doctor_id: parseInt(newDocId, 10) }),
        },
        auth?.access_token
      );
      setMsg(res.message || "Patient transferred to doctor successfully.");
      setReassignSelections((prev) => ({ ...prev, [patientId]: "" }));
      loadData();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleProcureMedicine = async (medId) => {
    const qty = parseInt(procureQuantities[medId] || "100", 10);
    if (!qty || qty <= 0) {
      setError("Please enter a valid procurement quantity.");
      return;
    }
    setError("");
    setMsg("");
    setLoading(true);
    try {
      const res = await apiRequest(
        `/admin/medicine-requests/${medId}/procure`,
        {
          method: "POST",
          body: JSON.stringify({ quantity: qty }),
        },
        auth?.access_token
      );
      setMsg(`Medicine '${res.name}' (${res.quantity} ${res.unit || "units"}) procured and allocated to Dr. ${res.requested_by_name || "Physician"}.`);
      loadData();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const toggleStatus = async (id) => {
    try {
      await apiRequest(`/admin/users/${id}/deactivate`, { method: "PUT" }, auth?.access_token);
      loadData();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleHospitalSave = async (e) => {
    e.preventDefault();
    setError("");
    setMsg("");
    setLoading(true);
    try {
      const payload = {
        ...hospitalForm,
        latitude: parseFloat(hospitalForm.latitude),
        longitude: parseFloat(hospitalForm.longitude),
        available_beds: parseInt(hospitalForm.available_beds, 10),
        icu_beds_available: parseInt(hospitalForm.icu_beds_available, 10),
        ventilators_available: parseInt(hospitalForm.ventilators_available, 10),
      };

      if (editingHospital) {
        await apiRequest(
          `/admin/hospitals/${editingHospital.id}`,
          {
            method: "PUT",
            body: JSON.stringify(payload),
          },
          auth?.access_token
        );
        setMsg(`Hospital '${hospitalForm.name}' updated successfully.`);
      } else {
        await apiRequest(
          "/admin/hospitals",
          {
            method: "POST",
            body: JSON.stringify(payload),
          },
          auth?.access_token
        );
        setMsg(`Hospital '${hospitalForm.name}' added successfully.`);
      }
      setShowHospitalModal(false);
      setEditingHospital(null);
      setHospitalForm({
        name: "",
        address: "",
        contact_number: "",
        latitude: "",
        longitude: "",
        available_beds: 0,
        icu_beds_available: 0,
        ventilators_available: 0,
        blood_bank_available: false,
        emergency_services_available: true,
      });
      loadData();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleEditHospital = (hospital) => {
    setEditingHospital(hospital);
    setHospitalForm({
      name: hospital.name,
      address: hospital.address,
      contact_number: hospital.contact_number,
      latitude: hospital.latitude.toString(),
      longitude: hospital.longitude.toString(),
      available_beds: hospital.available_beds,
      icu_beds_available: hospital.icu_beds_available,
      ventilators_available: hospital.ventilators_available,
      blood_bank_available: hospital.blood_bank_available,
      emergency_services_available: hospital.emergency_services_available,
    });
    setShowHospitalModal(true);
  };

  const handleDeleteHospital = async (hospitalId, hospitalName) => {
    if (!window.confirm(`Are you sure you want to delete '${hospitalName}'? This action cannot be undone.`)) {
      return;
    }
    setError("");
    setMsg("");
    try {
      await apiRequest(`/admin/hospitals/${hospitalId}`, { method: "DELETE" }, auth?.access_token);
      setMsg(`Hospital '${hospitalName}' deleted successfully.`);
      loadData();
    } catch (err) {
      setError(err.message);
    }
  };

  const openNewHospitalModal = () => {
    setEditingHospital(null);
    setHospitalForm({
      name: "",
      address: "",
      contact_number: "",
      latitude: "",
      longitude: "",
      available_beds: 0,
      icu_beds_available: 0,
      ventilators_available: 0,
      blood_bank_available: false,
      emergency_services_available: true,
    });
    setShowHospitalModal(true);
  };

  const handleDownloadPatientPdf = async (patientId, patientName) => {
    setPdfLoading(true);
    try {
      await downloadPdfReport(
        `/reports/patient/${patientId}/latest-pdf`,
        `medical_report_${(patientName || "patient").toLowerCase().replace(/\s+/g, "_")}.pdf`,
        auth?.access_token
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setPdfLoading(false);
    }
  };

  const doctorsList = users.filter((u) => u.role === "doctor" && u.is_active);

  const riskDist = overview?.risk_distribution || { Low: 0, Medium: 0, High: 0 };
  const totalRiskCount = (riskDist.Low || 0) + (riskDist.Medium || 0) + (riskDist.High || 0) || 1;

  const lowPct = Math.round(((riskDist.Low || 0) / totalRiskCount) * 100);
  const medPct = Math.round(((riskDist.Medium || 0) / totalRiskCount) * 100);
  const highPct = Math.round(((riskDist.High || 0) / totalRiskCount) * 100);

  return (
    <div className="container">
      {msg && <div className="alert alert-success">{msg}</div>}
      {error && <div className="alert alert-error">{error}</div>}

      {/* Section 1: Overview & Metrics */}
      <div className="card">
        <h3>System Overview & Metrics</h3>
        {overview ? (
          <div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12, marginBottom: 16 }}>
              <div style={{ padding: "10px 14px", background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 3 }}>
                <div style={{ fontSize: "0.75rem", color: "#64748b", fontWeight: 600, textTransform: "uppercase" }}>Total Doctors</div>
                <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "#0284c7" }}>{overview.total_doctors}</div>
              </div>
              <div style={{ padding: "10px 14px", background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 3 }}>
                <div style={{ fontSize: "0.75rem", color: "#64748b", fontWeight: 600, textTransform: "uppercase" }}>Total Patients</div>
                <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "#16a34a" }}>{overview.total_patients}</div>
              </div>
              <div style={{ padding: "10px 14px", background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 3 }}>
                <div style={{ fontSize: "0.75rem", color: "#64748b", fontWeight: 600, textTransform: "uppercase" }}>Assessments</div>
                <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "#7c3aed" }}>{overview.total_predictions}</div>
              </div>
              <div style={{ padding: "10px 14px", background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 3 }}>
                <div style={{ fontSize: "0.75rem", color: "#64748b", fontWeight: 600, textTransform: "uppercase" }}>Pending Self-Reg</div>
                <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "#d97706" }}>{pendingPatients.length}</div>
              </div>
            </div>

            <div>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4, fontSize: "0.8rem", color: "#475569" }}>
                <span>Population Risk Distribution</span>
                <span>Low: {riskDist.Low || 0} ({lowPct}%) | Medium: {riskDist.Medium || 0} ({medPct}%) | High: {riskDist.High || 0} ({highPct}%)</span>
              </div>
              <div style={{ display: "flex", height: 8, borderRadius: 3, overflow: "hidden", backgroundColor: "#e2e8f0" }}>
                <div style={{ width: `${lowPct}%`, backgroundColor: "#16a34a" }} />
                <div style={{ width: `${medPct}%`, backgroundColor: "#d97706" }} />
                <div style={{ width: `${highPct}%`, backgroundColor: "#dc2626" }} />
              </div>
            </div>
          </div>
        ) : (
          <p style={{ fontSize: "0.85rem", color: "#64748b" }}>Loading metrics...</p>
        )}
      </div>

      {/* Section 2: Medicine Procurement (Feature 4) */}
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <h3 style={{ margin: 0 }}>Doctor Medicine Procurement Queue</h3>
          <span style={{ fontSize: "0.8rem", color: "#64748b" }}>{medicineRequests.length} pending request{medicineRequests.length !== 1 ? "s" : ""}</span>
        </div>

        {medicineRequests.length === 0 ? (
          <p style={{ fontSize: "0.85rem", color: "#64748b" }}>No pending medicine requests from hospital doctors.</p>
        ) : (
          <div className="table-wrapper">
            <table className="table">
              <thead>
                <tr>
                  <th>Medicine Name</th>
                  <th>Generic / Category</th>
                  <th>Requested By</th>
                  <th>Requested Qty</th>
                  <th>Procure & Allocate Qty</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {medicineRequests.map((med) => (
                  <tr key={med.id}>
                    <td><strong>{med.name}</strong></td>
                    <td>{med.generic_name || "-"} <span style={{ color: "#64748b", fontSize: "0.75rem" }}>({med.category || "General"})</span></td>
                    <td>Dr. {med.requested_by_name || "Physician"}</td>
                    <td>{med.quantity} {med.unit || "units"}</td>
                    <td>
                      <input
                        type="number"
                        min="1"
                        style={{ width: 90, fontSize: "0.8rem", padding: "4px 8px" }}
                        placeholder="Quantity"
                        value={procureQuantities[med.id] !== undefined ? procureQuantities[med.id] : med.quantity}
                        onChange={(e) => setProcureQuantities({ ...procureQuantities, [med.id]: e.target.value })}
                      />
                    </td>
                    <td>
                      <button
                        type="button"
                        disabled={loading}
                        style={{ fontSize: "0.75rem", padding: "4px 10px", backgroundColor: "#15803d", borderColor: "#15803d" }}
                        onClick={() => handleProcureMedicine(med.id)}
                      >
                        Procure & Allocate
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Section 3: Pending Self-Registered Patients (Feature 6) */}
      {pendingPatients.length > 0 && (
        <div className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <h3 style={{ margin: 0 }}>Self-Registered Patient Intake Queue</h3>
            <span style={{ fontSize: "0.8rem", color: "#64748b" }}>{pendingPatients.length} awaiting assignment</span>
          </div>

          <div className="table-wrapper">
            <table className="table">
              <thead>
                <tr>
                  <th>Patient Name</th>
                  <th>Email</th>
                  <th>Preferred Department</th>
                  <th>Preferred Doctor</th>
                  <th>Registration Date</th>
                  <th>Assign Doctor</th>
                </tr>
              </thead>
              <tbody>
                {pendingPatients.map((p) => (
                  <tr key={p.id}>
                    <td><strong>{p.patient_name}</strong></td>
                    <td>{p.patient_email}</td>
                    <td>{p.department_preference || "Cardiology"}</td>
                    <td>{p.preferred_doctor_name || "Unassigned"}</td>
                    <td>{p.created_at}</td>
                    <td>
                      <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
                        <select
                          style={{ fontSize: "0.8rem", padding: "3px 6px" }}
                          value={reassignSelections[p.patient_id] || ""}
                          onChange={(e) => setReassignSelections({ ...reassignSelections, [p.patient_id]: e.target.value })}
                        >
                          <option value="">-- Choose Doctor --</option>
                          {doctorsList.map((d) => (
                            <option key={d.id} value={d.id}>
                              {d.name} ({d.specialization || "General"})
                            </option>
                          ))}
                        </select>
                        <button
                          type="button"
                          className="btn-secondary"
                          style={{ fontSize: "0.75rem", padding: "3px 8px" }}
                          onClick={() => handleReassignDoctor(p.patient_id)}
                        >
                          Assign
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Section 4: Quick Registration */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <div className="card">
          <h3>Register Doctor</h3>
          <form className="form" onSubmit={handleAddDoctor}>
            <div className="form-group">
              <label>Doctor Name</label>
              <input
                type="text"
                placeholder="Dr. Name"
                value={docForm.name}
                onChange={(e) => setDocForm({ ...docForm, name: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <label>Email Address</label>
              <input
                type="email"
                placeholder="doctor@hospital.com"
                value={docForm.email}
                onChange={(e) => setDocForm({ ...docForm, email: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <label>Password</label>
              <input
                type="password"
                placeholder="Password"
                value={docForm.password}
                onChange={(e) => setDocForm({ ...docForm, password: e.target.value })}
                required
              />
            </div>
            <div className="form-grid">
              <div className="form-group">
                <label>Specialization</label>
                <input
                  type="text"
                  placeholder="e.g. Cardiology"
                  value={docForm.specialization}
                  onChange={(e) => setDocForm({ ...docForm, specialization: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>License No.</label>
                <input
                  type="text"
                  placeholder="e.g. DOC-123"
                  value={docForm.license_number}
                  onChange={(e) => setDocForm({ ...docForm, license_number: e.target.value })}
                />
              </div>
            </div>
            <button type="submit" style={{ alignSelf: "flex-start" }}>Register Doctor</button>
          </form>
        </div>

        <div className="card">
          <h3>Register Patient (Admin)</h3>
          <form className="form" onSubmit={handleAddPatient}>
            <div className="form-group">
              <label>Patient Name</label>
              <input
                type="text"
                placeholder="Full Name"
                value={patForm.name}
                onChange={(e) => setPatForm({ ...patForm, name: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <label>Email Address</label>
              <input
                type="email"
                placeholder="patient@hospital.com"
                value={patForm.email}
                onChange={(e) => setPatForm({ ...patForm, email: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <label>Password</label>
              <input
                type="password"
                placeholder="Password"
                value={patForm.password}
                onChange={(e) => setPatForm({ ...patForm, password: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <label>Assign to Doctor</label>
              <select
                value={patForm.doctor_id}
                onChange={(e) => setPatForm({ ...patForm, doctor_id: e.target.value })}
              >
                <option value="">-- Select Doctor --</option>
                {doctorsList.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name} ({d.specialization || "General"})
                  </option>
                ))}
              </select>
            </div>
            <button type="submit" style={{ alignSelf: "flex-start" }}>Register Patient</button>
          </form>
        </div>
      </div>

      {/* Section 5: Hospital Directory Management */}
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <h3 style={{ margin: 0 }}>🏥 Hospital Directory & Emergency Availability</h3>
          <div style={{ display: "flex", gap: 8 }}>
            <span style={{ fontSize: "0.8rem", color: "#64748b" }}>{hospitals.length} registered</span>
            <button
              type="button"
              style={{ fontSize: "0.85rem", padding: "4px 12px" }}
              onClick={openNewHospitalModal}
            >
              + Add Hospital
            </button>
          </div>
        </div>

        {hospitals.length === 0 ? (
          <p style={{ fontSize: "0.85rem", color: "#64748b" }}>
            No hospitals registered yet. Click "Add Hospital" to add the first facility.
          </p>
        ) : (
          <div className="table-wrapper">
            <table className="table">
              <thead>
                <tr>
                  <th>Hospital Name</th>
                  <th>Address</th>
                  <th>Contact</th>
                  <th>Available Beds</th>
                  <th>ICU Beds</th>
                  <th>Ventilators</th>
                  <th>Blood Bank</th>
                  <th>Emergency</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {hospitals.map((h) => (
                  <tr key={h.id}>
                    <td><strong>{h.name}</strong></td>
                    <td style={{ fontSize: "0.85rem" }}>{h.address}</td>
                    <td style={{ fontSize: "0.85rem" }}>📞 {h.contact_number}</td>
                    <td style={{ color: h.available_beds > 0 ? "#16a34a" : "#dc2626" }}>{h.available_beds}</td>
                    <td style={{ color: h.icu_beds_available > 0 ? "#16a34a" : "#dc2626" }}>{h.icu_beds_available}</td>
                    <td style={{ color: h.ventilators_available > 0 ? "#16a34a" : "#dc2626" }}>{h.ventilators_available}</td>
                    <td>
                      <span className={`badge ${h.blood_bank_available ? "badge-low" : "badge-high"}`}>
                        {h.blood_bank_available ? "Available" : "Unavailable"}
                      </span>
                    </td>
                    <td>
                      <span className={`badge ${h.emergency_services_available ? "badge-low" : "badge-high"}`}>
                        {h.emergency_services_available ? "Open" : "Closed"}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: "flex", gap: 6 }}>
                        <button
                          type="button"
                          className="btn-secondary"
                          style={{ fontSize: "0.75rem", padding: "3px 8px" }}
                          onClick={() => handleEditHospital(h)}
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          className="btn-danger"
                          style={{ fontSize: "0.75rem", padding: "3px 8px" }}
                          onClick={() => handleDeleteHospital(h.id, h.name)}
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Section 6: User Management */}
      <div className="card">
        <h3>User Directory & Transfers</h3>
        <div className="table-wrapper">
          <table className="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Email</th>
                <th>Role</th>
                <th>Assigned Doctor / Specialty</th>
                <th>Status</th>
                <th>Transfer</th>
                <th>Reports</th>
                <th>Access</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>{u.id}</td>
                  <td><strong>{u.name}</strong></td>
                  <td>{u.email}</td>
                  <td>
                    <span className="badge badge-neutral" style={{ textTransform: "capitalize" }}>
                      {u.role}
                    </span>
                  </td>
                  <td>{u.specialization ? `Spec: ${u.specialization}` : u.assigned_doctor ? `Dr. ${u.assigned_doctor}` : "-"}</td>
                  <td>{u.is_active ? "Active" : "Disabled"}</td>
                  <td>
                    {u.role === "patient" ? (
                      <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
                        <select
                          style={{ fontSize: "0.8rem", padding: "3px 6px" }}
                          value={reassignSelections[u.id] || ""}
                          onChange={(e) => setReassignSelections({ ...reassignSelections, [u.id]: e.target.value })}
                        >
                          <option value="">-- Choose Doctor --</option>
                          {doctorsList.map((d) => (
                            <option key={d.id} value={d.id}>
                              {d.name}
                            </option>
                          ))}
                        </select>
                        <button
                          type="button"
                          className="btn-secondary"
                          style={{ fontSize: "0.75rem", padding: "3px 8px" }}
                          onClick={() => handleReassignDoctor(u.id)}
                        >
                          Transfer
                        </button>
                      </div>
                    ) : (
                      "-"
                    )}
                  </td>
                  <td>
                    {u.role === "patient" ? (
                      <button
                        type="button"
                        style={{ fontSize: "0.75rem", padding: "3px 8px", backgroundColor: "#15803d", borderColor: "#15803d" }}
                        onClick={() => handleDownloadPatientPdf(u.id, u.name)}
                        disabled={pdfLoading}
                      >
                        PDF
                      </button>
                    ) : (
                      "-"
                    )}
                  </td>
                  <td>
                    {u.role !== "admin" && (
                      <button
                        className={u.is_active ? "btn-danger" : "btn-secondary"}
                        style={{ fontSize: "0.75rem", padding: "3px 8px" }}
                        onClick={() => toggleStatus(u.id)}
                      >
                        {u.is_active ? "Deactivate" : "Activate"}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Section 7: Audit Activity Log */}
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
          <h3 style={{ margin: 0 }}>System Audit Trail</h3>
          <span style={{ fontSize: "0.8rem", color: "#64748b" }}>Latest events</span>
        </div>
        {activities.length === 0 ? (
          <p style={{ fontSize: "0.85rem", color: "#64748b" }}>No activity logged yet.</p>
        ) : (
          <div className="table-wrapper" style={{ maxHeight: 350, overflowY: "auto" }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Actor</th>
                  <th>Role</th>
                  <th>Action</th>
                  <th>Target</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {activities.map((a) => (
                  <tr key={a.id}>
                    <td style={{ fontSize: "0.75rem", whiteSpace: "nowrap" }}>
                      {a.created_at ? new Date(a.created_at).toLocaleString() : "-"}
                    </td>
                    <td><strong>{a.actor_name}</strong></td>
                    <td style={{ textTransform: "capitalize", fontSize: "0.8rem" }}>{a.actor_role}</td>
                    <td>
                      <span className="badge badge-neutral">{a.action}</span>
                    </td>
                    <td style={{ fontSize: "0.8rem" }}>{a.target_type ? `${a.target_type} #${a.target_id || ""}` : "-"}</td>
                    <td style={{ fontSize: "0.75rem", color: "#64748b", maxWidth: 280, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {a.details || "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Hospital Add/Edit Modal */}
      {showHospitalModal && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0, 0, 0, 0.5)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
          }}
        >
          <div
            className="card"
            style={{
              width: 600,
              maxHeight: "90vh",
              overflowY: "auto",
              position: "relative",
            }}
          >
            <button
              type="button"
              onClick={() => {
                setShowHospitalModal(false);
                setEditingHospital(null);
              }}
              style={{
                position: "absolute",
                top: 12,
                right: 12,
                background: "none",
                border: "none",
                fontSize: "1.5rem",
                cursor: "pointer",
                color: "#64748b",
              }}
            >
              ×
            </button>

            <h3 style={{ margin: "0 0 16px" }}>
              {editingHospital ? "Edit Hospital" : "Add New Hospital"}
            </h3>

            <form className="form" onSubmit={handleHospitalSave}>
              <div className="form-group">
                <label>Hospital Name *</label>
                <input
                  type="text"
                  value={hospitalForm.name}
                  onChange={(e) => setHospitalForm({ ...hospitalForm, name: e.target.value })}
                  placeholder="e.g. City General Hospital"
                  required
                />
              </div>

              <div className="form-group">
                <label>Address *</label>
                <input
                  type="text"
                  value={hospitalForm.address}
                  onChange={(e) => setHospitalForm({ ...hospitalForm, address: e.target.value })}
                  placeholder="Full address"
                  required
                />
              </div>

              <div className="form-group">
                <label>Contact Number *</label>
                <input
                  type="text"
                  value={hospitalForm.contact_number}
                  onChange={(e) => setHospitalForm({ ...hospitalForm, contact_number: e.target.value })}
                  placeholder="e.g. +1-555-0123"
                  required
                />
              </div>

              <div className="form-grid">
                <div className="form-group">
                  <label>Latitude *</label>
                  <input
                    type="number"
                    step="0.0001"
                    value={hospitalForm.latitude}
                    onChange={(e) => setHospitalForm({ ...hospitalForm, latitude: e.target.value })}
                    placeholder="e.g. 28.6139"
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Longitude *</label>
                  <input
                    type="number"
                    step="0.0001"
                    value={hospitalForm.longitude}
                    onChange={(e) => setHospitalForm({ ...hospitalForm, longitude: e.target.value })}
                    placeholder="e.g. 77.2090"
                    required
                  />
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
                <div className="form-group">
                  <label>Available Beds</label>
                  <input
                    type="number"
                    min="0"
                    value={hospitalForm.available_beds}
                    onChange={(e) => setHospitalForm({ ...hospitalForm, available_beds: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label>ICU Beds</label>
                  <input
                    type="number"
                    min="0"
                    value={hospitalForm.icu_beds_available}
                    onChange={(e) => setHospitalForm({ ...hospitalForm, icu_beds_available: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label>Ventilators</label>
                  <input
                    type="number"
                    min="0"
                    value={hospitalForm.ventilators_available}
                    onChange={(e) => setHospitalForm({ ...hospitalForm, ventilators_available: e.target.value })}
                  />
                </div>
              </div>

              <div style={{ display: "flex", gap: 16, marginTop: 8 }}>
                <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.9rem" }}>
                  <input
                    type="checkbox"
                    checked={hospitalForm.blood_bank_available}
                    onChange={(e) => setHospitalForm({ ...hospitalForm, blood_bank_available: e.target.checked })}
                  />
                  Blood Bank Available
                </label>
                <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.9rem" }}>
                  <input
                    type="checkbox"
                    checked={hospitalForm.emergency_services_available}
                    onChange={(e) => setHospitalForm({ ...hospitalForm, emergency_services_available: e.target.checked })}
                  />
                  Emergency Services Open
                </label>
              </div>

              <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
                <button type="submit" disabled={loading} style={{ alignSelf: "flex-start" }}>
                  {loading ? "Saving..." : editingHospital ? "Update Hospital" : "Add Hospital"}
                </button>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => {
                    setShowHospitalModal(false);
                    setEditingHospital(null);
                  }}
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
