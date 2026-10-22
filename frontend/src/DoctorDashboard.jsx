import React, { useState, useEffect, useRef } from "react";
import { useAuth } from "./AuthContext";
import { apiRequest, downloadPdfReport, fetchStructuredPatientReport } from "./api";
import { useToast } from "./ToastContext";
import { SkeletonList, SkeletonTable } from "./Skeleton";
import PasswordToggle from "./PasswordToggle";
import InformationDrawer from "./components/ui/information-drawer";
import PatientReportModal from "./PatientReportModal";

export default function DoctorDashboard() {
  const { auth } = useAuth();
  const toast = useToast();
  const [patients, setPatients] = useState([]);
  const [allDoctors, setAllDoctors] = useState([]);
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [isGuestMode, setIsGuestMode] = useState(false);
  const [mainView, setMainView] = useState("my_patients"); // 'my_patients' | 'requests' | 'medicines' | 'shared_area' | 'drafts'
  const [activeTab, setActiveTab] = useState("assessment"); // 'assessment' | 'diagnosis' | 'blood_test' | 'collaborative'
  
  // Assessment workflow state: 'idle' | 'preview' | 'approved'
  const [assessmentStatus, setAssessmentStatus] = useState("idle");
  const [assessmentResult, setAssessmentResult] = useState(null);
  const [pendingAssessmentPayload, setPendingAssessmentPayload] = useState(null);

  const [bloodTests, setBloodTests] = useState([]);
  const [patientDiagnoses, setPatientDiagnoses] = useState([]);
  const [sharedCases, setSharedCases] = useState([]);
  const [sharedSearch, setSharedSearch] = useState("");
  const [sharedRiskFilter, setSharedRiskFilter] = useState("all");
  const [collaborativeFile, setCollaborativeFile] = useState(null);
  const [drafts, setDrafts] = useState([]);
  const [patientRequests, setPatientRequests] = useState([]);
  const [medicines, setMedicines] = useState([]);
  const [selectedMedicineIds, setSelectedMedicineIds] = useState([]);
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [dataLoading, setDataLoading] = useState(true);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [reportModalOpen, setReportModalOpen] = useState(false);
  const [reportData, setReportData] = useState(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [reportPdfEndpoint, setReportPdfEndpoint] = useState(null);
  const [reportPatientName, setReportPatientName] = useState("patient");

  const [hospitalDirectory, setHospitalDirectory] = useState([]);
  const [hospitalLoading, setHospitalLoading] = useState(false);
  const [userLocation, setUserLocation] = useState(null);

  const [doctorProfile, setDoctorProfile] = useState(null);
  const [doctorProfileForm, setDoctorProfileForm] = useState({
    name: "",
    specialization: "",
    license_number: "",
    degree: "",
    years_of_experience: "",
    certifications: "",
  });
  const [profileSaveMsg, setProfileSaveMsg] = useState("");

  const resultRef = useRef(null);

  // Transfer Modal State
  const [showTransferModal, setShowTransferModal] = useState(false);
  const [transferTargetDocId, setTransferTargetDocId] = useState("");
  const [transferReason, setTransferReason] = useState("");

  // Forward Patient Request Modal State
  const [showForwardModal, setShowForwardModal] = useState(false);
  const [forwardTargetReq, setForwardTargetReq] = useState(null);
  const [forwardTargetDocId, setForwardTargetDocId] = useState("");
  const [forwardNotes, setForwardNotes] = useState("");

  // Request Medicine Modal State
  const [showMedRequestModal, setShowMedRequestModal] = useState(false);
  const [medRequestForm, setMedRequestForm] = useState({
    name: "",
    generic_name: "",
    category: "Cardiovascular & Internal Medicine",
    unit: "tablets",
    quantity: 100,
    notes: "",
  });

  // Convert Draft Modal State
  const [showConvertModal, setShowConvertModal] = useState(false);
  const [convertDraftTarget, setConvertDraftTarget] = useState(null);
  const [convertForm, setConvertForm] = useState({
    patient_name: "",
    patient_email: "",
    password: "Demo@123",
    phone_number: "",
    emergency_contact_name: "",
    emergency_contact_phone: "",
    address: "",
  });

  // New Patient Registration Modal State
  const [showAddPatientModal, setShowAddPatientModal] = useState(false);
  const [newPatientForm, setNewPatientForm] = useState({
    name: "",
    email: "",
    password: "Demo@123",
    date_of_birth: "",
    age: "",
    sex: "1",
    phone_number: "",
    emergency_contact_name: "",
    emergency_contact_phone: "",
    address: "",
  });

  const calcAgeFromDob = (dobStr) => {
    if (!dobStr) return null;
    const dob = new Date(dobStr);
    if (isNaN(dob.getTime())) return null;
    const today = new Date();
    let age = today.getFullYear() - dob.getFullYear();
    const m = today.getMonth() - dob.getMonth();
    if (m < 0 || (m === 0 && today.getDate() < dob.getDate())) age--;
    return age >= 0 ? age : 0;
  };

  // Clinical Assessment Form State
  const [assessmentForm, setAssessmentForm] = useState({
    guest_name: "",
    age: "",
    sex: "1",
    systolic_bp: "",
    diastolic_bp: "",
    cholesterol: "",
    fasting_blood_sugar: "0",
    max_heart_rate: "",
    bmi: "",
    smoking: "0",
    chest_pain_type: "3",
    exercise_angina: "0",
    st_depression: "0.0",
    hypertension: false,
    diabetes: false,
    family_history_cad: false,
    prior_heart_event: false,
    history_stroke: false,
    exercise_frequency: "Moderate (3-4x/week)",
    diet_notes: "",
  });

  // Doctor Diagnosis Form State
  const [diagnosisForm, setDiagnosisForm] = useState({
    diagnosis_title: "",
    clinical_notes: "",
    treatment_plan: "",
    prescriptions: "",
    risk_summary: "",
  });

  // Blood Test Form State
  const [bloodTestForm, setBloodTestForm] = useState({
    hemoglobin: "",
    wbc_count: "",
    platelet_count: "",
    fasting_glucose: "",
    hba1c: "",
    total_cholesterol: "",
    hdl: "",
    ldl: "",
    triglycerides: "",
    creatinine: "",
    notes: "",
  });

  const loadPatients = async (selectPatientId = null) => {
    try {
      const data = await apiRequest("/doctor/patients", {}, auth?.access_token);
      setPatients(data);
      if (selectPatientId) {
        const found = data.find((p) => p.id === selectPatientId);
        if (found) {
          setSelectedPatient(found);
          setIsGuestMode(false);
        }
      } else if (data.length > 0 && !selectedPatient && !isGuestMode) {
        setSelectedPatient(data[0]);
      }
    } catch (err) {
      setError(err.message);
    }
  };

  const loadAllDoctors = async () => {
    try {
      const docs = await apiRequest("/doctor/all-doctors", {}, auth?.access_token);
      setAllDoctors(docs.filter((d) => d.id !== auth?.id));
    } catch (err) {
      console.error("Failed to load doctors list:", err);
    }
  };

  const loadPatientData = async (patientId) => {
    if (!patientId) return;
    try {
      const [tests, diags] = await Promise.all([
        apiRequest(`/doctor/patients/${patientId}/blood-tests`, {}, auth?.access_token).catch(() => []),
        apiRequest(`/doctor/patients/${patientId}/diagnoses`, {}, auth?.access_token).catch(() => []),
      ]);
      setBloodTests(tests);
      setPatientDiagnoses(diags);
    } catch (err) {
      console.error("Error loading patient sub-data:", err);
    }
  };

  const loadSharedCases = async () => {
    try {
      const cases = await apiRequest("/doctor/shared-cases", {}, auth?.access_token);
      setSharedCases(cases);
    } catch (err) {
      console.error("Failed to load shared cases:", err);
    }
  };

  const loadDrafts = async () => {
    try {
      const data = await apiRequest("/doctor/drafts", {}, auth?.access_token);
      setDrafts(data);
    } catch (err) {
      console.error("Failed to load drafts:", err);
    }
  };

  const loadPatientRequests = async () => {
    try {
      const reqs = await apiRequest("/doctor/patient-requests", {}, auth?.access_token);
      setPatientRequests(reqs);
    } catch (err) {
      console.error("Failed to load patient requests:", err);
    }
  };

  const loadMedicines = async () => {
    try {
      const meds = await apiRequest("/doctor/medicines", {}, auth?.access_token);
      setMedicines(meds);
    } catch (err) {
      console.error("Failed to load medicines:", err);
    }
  };

  const loadHospitalDirectory = async (latitude = null, longitude = null) => {
    setHospitalLoading(true);
    try {
      let url = "/doctor/hospitals";
      if (latitude && longitude) {
        url = `/doctor/hospitals/nearby?latitude=${latitude}&longitude=${longitude}&radius_km=100`;
      }
      const data = await apiRequest(url, {}, auth?.access_token);
      setHospitalDirectory(data);
    } catch (err) {
      console.error("Failed to load hospital directory:", err);
    } finally {
      setHospitalLoading(false);
    }
  };

  const loadCollaborativeFile = async (patientId) => {
    if (!patientId) return;
    setLoading(true);
    try {
      const file = await apiRequest(`/doctor/patients/${patientId}/collaborative-file`, {}, auth?.access_token);
      setCollaborativeFile(file);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    Promise.all([
      loadPatients(),
      loadAllDoctors(),
      loadSharedCases(),
      loadDrafts(),
      loadPatientRequests(),
      loadMedicines(),
    ]).finally(() => setDataLoading(false));
    // Load own doctor profile
    apiRequest("/auth/me", {}, auth?.access_token).then((me) => {
      setDoctorProfile(me);
      setDoctorProfileForm({
        name: me.name || "",
        specialization: me.specialization || "",
        license_number: me.license_number || "",
        degree: me.degree || "",
        years_of_experience: me.years_of_experience !== null && me.years_of_experience !== undefined ? String(me.years_of_experience) : "",
        certifications: me.certifications || "",
      });
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (selectedPatient && !isGuestMode) {
      loadPatientData(selectedPatient.id);
      setAssessmentResult(null);
      setAssessmentStatus("idle");
      setPendingAssessmentPayload(null);
      setMsg("");
      setError("");

      setAssessmentForm((prev) => ({
        ...prev,
        age: selectedPatient.age !== null && selectedPatient.age !== undefined ? String(selectedPatient.age) : "",
        sex: selectedPatient.sex !== null && selectedPatient.sex !== undefined ? String(selectedPatient.sex) : "1",
      }));

      if (activeTab === "collaborative") {
        loadCollaborativeFile(selectedPatient.id);
      }
    }
  }, [selectedPatient, activeTab, isGuestMode]);

  // Auto-scroll to prediction result when generated
  useEffect(() => {
    if (assessmentResult && resultRef.current) {
      resultRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [assessmentResult]);

  const handleSelectGuestMode = () => {
    setIsGuestMode(true);
    setSelectedPatient(null);
    setAssessmentResult(null);
    setAssessmentStatus("idle");
    setPendingAssessmentPayload(null);
    setMsg("Guest Evaluation Mode active. Enter patient vitals below to predict risk immediately without registering an account.");
    setError("");
    setActiveTab("assessment");
    setAssessmentForm({
      guest_name: `Walk-in Guest #${drafts.length + 1}`,
      age: "",
      sex: "1",
      systolic_bp: "",
      diastolic_bp: "",
      cholesterol: "",
      fasting_blood_sugar: "0",
      max_heart_rate: "",
      bmi: "",
      smoking: "0",
      chest_pain_type: "3",
      exercise_angina: "0",
      st_depression: "0.0",
      hypertension: false,
      diabetes: false,
      family_history_cad: false,
      prior_heart_event: false,
      history_stroke: false,
      exercise_frequency: "Moderate (3-4x/week)",
      diet_notes: "",
    });
  };

  const handleSaveAsDraft = async () => {
    setError("");
    setMsg("");
    setLoading(true);

    try {
      const draftPayload = {
        draft_name: assessmentForm.guest_name || "Guest Patient Assessment Draft",
        guest_identifier: assessmentForm.guest_name || "Walk-in Guest",
        data: assessmentForm,
        risk_level: assessmentResult?.risk_level || null,
        risk_probability: assessmentResult?.risk_probability || null,
      };

      await apiRequest(
        "/doctor/drafts",
        {
          method: "POST",
          body: JSON.stringify(draftPayload),
        },
        auth?.access_token
      );

      setMsg("Assessment saved as clinical draft successfully.");
      toast.success("Assessment saved as clinical draft successfully.");
      setAssessmentStatus("approved");
      loadDrafts();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleResumeDraft = (draft) => {
    try {
      const data = typeof draft.raw_data_json === "string" ? JSON.parse(draft.raw_data_json) : draft.raw_data_json;
      setIsGuestMode(true);
      setSelectedPatient(null);
      setAssessmentForm(data);
      if (draft.risk_level && draft.risk_probability) {
        setAssessmentResult({
          risk_level: draft.risk_level,
          risk_probability: draft.risk_probability,
          risk_percentage: draft.risk_probability * 100,
          risk_category: {
            label: draft.risk_level,
            color: draft.risk_level === "Critical Risk" ? "#991b1b" : draft.risk_level === "High Risk" ? "#dc2626" : draft.risk_level === "Moderate Risk" ? "#d97706" : "#16a34a",
          },
          top_features: ["Age", "Blood Pressure", "Cholesterol"],
          reasons: [],
          recommendations: ["Follow-up clinical assessment", "Routine dietary monitoring"],
          auto_diagnosis_suggestion: `${draft.risk_level} - Cardiovascular Evaluation`,
        });
        setAssessmentStatus("preview");
      } else {
        setAssessmentResult(null);
        setAssessmentStatus("idle");
      }
      setMainView("my_patients");
      setActiveTab("assessment");
      setMsg(`Resumed draft: ${draft.draft_name}`);
    } catch (err) {
      setError("Failed to parse draft data.");
    }
  };

  const handleDeleteDraft = async (draftId) => {
    if (!window.confirm("Delete this draft?")) return;
    try {
      await apiRequest(`/doctor/drafts/${draftId}`, { method: "DELETE" }, auth?.access_token);
      setMsg("Draft deleted.");
      toast.success("Draft deleted.");
      loadDrafts();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleConvertDraftSubmit = async (e) => {
    e.preventDefault();
    if (!convertDraftTarget) return;
    setLoading(true);
    setError("");
    setMsg("");

    try {
      const res = await apiRequest(
        `/doctor/drafts/${convertDraftTarget.id}/convert`,
        {
          method: "POST",
          body: JSON.stringify(convertForm),
        },
        auth?.access_token
      );

      setMsg(res.message || "Draft converted to registered patient successfully.");
      toast.success(res.message || "Draft converted to registered patient successfully.");
      setShowConvertModal(false);
      setConvertDraftTarget(null);
      setConvertForm({
        patient_name: "",
        patient_email: "",
        password: "Demo@123",
        phone_number: "",
        emergency_contact_name: "",
        emergency_contact_phone: "",
        address: "",
      });
      await loadPatients(res.patient_id);
      loadDrafts();
      setMainView("my_patients");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCreatePatient = async (e) => {
    e.preventDefault();
    setError("");
    setMsg("");
    setLoading(true);

    try {
      // Calculate age from DOB; fall back to manual age field if DOB not provided
      const dobAge = calcAgeFromDob(newPatientForm.date_of_birth);
      const resolvedAge = dobAge !== null ? dobAge : (newPatientForm.age ? parseFloat(newPatientForm.age) : null);

      const payload = {
        name: newPatientForm.name,
        email: newPatientForm.email,
        password: newPatientForm.password,
        date_of_birth: newPatientForm.date_of_birth || null,
        age: resolvedAge,
        sex: newPatientForm.sex !== "" ? parseFloat(newPatientForm.sex) : null,
        phone_number: newPatientForm.phone_number || null,
        emergency_contact_name: newPatientForm.emergency_contact_name || null,
        emergency_contact_phone: newPatientForm.emergency_contact_phone || null,
        address: newPatientForm.address || null,
      };

      const created = await apiRequest(
        "/doctor/patients",
        {
          method: "POST",
          body: JSON.stringify(payload),
        },
        auth?.access_token
      );

      setMsg(`Patient ${created.name} registered and assigned to you.`);
      toast.success(`Patient "${created.name}" registered and assigned to you.`);
      setShowAddPatientModal(false);
      setNewPatientForm({
        name: "",
        email: "",
        password: "Demo@123",
        date_of_birth: "",
        age: "",
        sex: "1",
        phone_number: "",
        emergency_contact_name: "",
        emergency_contact_phone: "",
        address: "",
      });
      await loadPatients(created.id);
      loadSharedCases();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleTransferPatient = async (e) => {
    e.preventDefault();
    if (!selectedPatient || !transferTargetDocId) {
      setError("Please select a target doctor.");
      return;
    }
    setError("");
    setMsg("");
    setLoading(true);

    try {
      const res = await apiRequest(
        `/doctor/patients/${selectedPatient.id}/transfer`,
        {
          method: "POST",
          body: JSON.stringify({
            new_doctor_id: parseInt(transferTargetDocId, 10),
            reason: transferReason || "Care referral",
          }),
        },
        auth?.access_token
      );

      setMsg(res.message || `Patient ${selectedPatient.name} transferred successfully.`);
      toast.success(res.message || `Patient "${selectedPatient.name}" transferred successfully.`);
      setShowTransferModal(false);
      setTransferReason("");
      setTransferTargetDocId("");
      setSelectedPatient(null);
      await loadPatients();
      loadSharedCases();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAcceptPatientRequest = async (requestId) => {
    setError("");
    setMsg("");
    setLoading(true);
    try {
      const res = await apiRequest(
        `/doctor/patient-requests/${requestId}/accept`,
        { method: "POST" },
        auth?.access_token
      );
      setMsg(res.message || "Patient request accepted into your roster.");
      toast.success(res.message || "Patient request accepted into your roster.");
      loadPatientRequests();
      await loadPatients(res.patient_id);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenForwardModal = (req) => {
    setForwardTargetReq(req);
    setForwardTargetDocId("");
    setForwardNotes("");
    setShowForwardModal(true);
  };

  const handleForwardPatientRequest = async (e) => {
    e.preventDefault();
    if (!forwardTargetReq || !forwardTargetDocId) {
      setError("Please select a target doctor to forward to.");
      return;
    }
    setError("");
    setMsg("");
    setLoading(true);
    try {
      const res = await apiRequest(
        `/doctor/patient-requests/${forwardTargetReq.id}/forward`,
        {
          method: "POST",
          body: JSON.stringify({
            new_doctor_id: parseInt(forwardTargetDocId, 10),
            notes: forwardNotes,
          }),
        },
        auth?.access_token
      );
      setMsg(res.message || "Patient request forwarded to doctor.");
      toast.success(res.message || "Patient request forwarded to doctor.");
      setShowForwardModal(false);
      setForwardTargetReq(null);
      loadPatientRequests();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRequestMedicineSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setMsg("");
    setLoading(true);
    try {
      const res = await apiRequest(
        "/doctor/medicines/request",
        {
          method: "POST",
          body: JSON.stringify(medRequestForm),
        },
        auth?.access_token
      );
      setMsg(`Procurement request submitted for ${res.name} (${res.quantity} ${res.unit}).`);
      toast.success(`Procurement request submitted for "${res.name}".`);
      setShowMedRequestModal(false);
      setMedRequestForm({
        name: "",
        generic_name: "",
        category: "Cardiovascular & Internal Medicine",
        unit: "tablets",
        quantity: 100,
        notes: "",
      });
      loadMedicines();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAddMedicinesToPrescription = () => {
    const availableProcured = medicines.filter((m) => m.status === "procured" && selectedMedicineIds.includes(m.id));
    if (availableProcured.length === 0) {
      setError("Please select at least one available medicine.");
      return;
    }
    const medTextList = availableProcured.map((m) => `${m.name} (${m.generic_name || m.category || "Rx"})`);
    const newRx = diagnosisForm.prescriptions
      ? `${diagnosisForm.prescriptions}, ${medTextList.join(", ")}`
      : medTextList.join(", ");
    setDiagnosisForm((prev) => ({ ...prev, prescriptions: newRx }));
    setMsg("Selected medicines added to prescription notes.");
    toast.success("Selected medicines added to prescription notes.");
    setActiveTab("diagnosis");
  };

  const handleDiagnosisSubmit = async (e) => {
    e.preventDefault();
    if (!selectedPatient) return;
    setError("");
    setMsg("");
    setLoading(true);

    try {
      await apiRequest(
        `/doctor/patients/${selectedPatient.id}/diagnosis`,
        {
          method: "POST",
          body: JSON.stringify(diagnosisForm),
        },
        auth?.access_token
      );

      setMsg("Clinical diagnosis and treatment plan recorded.");
      toast.success("Clinical diagnosis and treatment plan recorded.");
      setDiagnosisForm({
        diagnosis_title: "",
        clinical_notes: "",
        treatment_plan: "",
        prescriptions: "",
        risk_summary: "",
      });
      loadPatientData(selectedPatient.id);
      loadSharedCases();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // STEP 1: Run AI Assessment & Preview Output on Screen
  const handleAssessmentSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setMsg("");
    setAssessmentResult(null);
    setAssessmentStatus("idle");
    setLoading(true);

    try {
      const familyHistArr = [];
      if (assessmentForm.family_history_cad) familyHistArr.push("CAD/Heart Disease");
      if (assessmentForm.diabetes) familyHistArr.push("Diabetes");
      if (assessmentForm.hypertension) familyHistArr.push("Hypertension");

      const priorEventsArr = [];
      if (assessmentForm.prior_heart_event) priorEventsArr.push("Prior Myocardial Infarction");
      if (assessmentForm.history_stroke) priorEventsArr.push("Stroke/TIA");

      const effectiveAge = (!isGuestMode && selectedPatient?.age !== null && selectedPatient?.age !== undefined)
        ? parseFloat(selectedPatient.age)
        : (assessmentForm.age ? parseFloat(assessmentForm.age) : null);

      const effectiveSex = (!isGuestMode && selectedPatient?.sex !== null && selectedPatient?.sex !== undefined)
        ? parseFloat(selectedPatient.sex)
        : (assessmentForm.sex !== "" ? parseFloat(assessmentForm.sex) : 1.0);

      const payload = {
        age: effectiveAge,
        sex: effectiveSex,
        systolic_bp: assessmentForm.systolic_bp ? parseInt(assessmentForm.systolic_bp, 10) : null,
        diastolic_bp: assessmentForm.diastolic_bp ? parseInt(assessmentForm.diastolic_bp, 10) : null,
        cholesterol: assessmentForm.cholesterol ? parseFloat(assessmentForm.cholesterol) : null,
        fasting_blood_sugar: assessmentForm.fasting_blood_sugar !== "" ? parseFloat(assessmentForm.fasting_blood_sugar) : null,
        max_heart_rate: assessmentForm.max_heart_rate ? parseFloat(assessmentForm.max_heart_rate) : null,
        bmi: assessmentForm.bmi ? parseFloat(assessmentForm.bmi) : null,
        smoking: assessmentForm.smoking !== "" ? parseFloat(assessmentForm.smoking) : null,
        chest_pain_type: assessmentForm.chest_pain_type !== "" ? parseFloat(assessmentForm.chest_pain_type) : null,
        exercise_angina: assessmentForm.exercise_angina !== "" ? parseFloat(assessmentForm.exercise_angina) : null,
        st_depression: assessmentForm.st_depression !== "" ? parseFloat(assessmentForm.st_depression) : null,
        hypertension: assessmentForm.hypertension ? 1.0 : 0.0,
        diabetes: assessmentForm.diabetes ? 1.0 : 0.0,
        prior_medical_events: priorEventsArr.length > 0 ? priorEventsArr.join("; ") : null,
        family_history: familyHistArr.length > 0 ? familyHistArr.join("; ") : "None reported",
        exercise_frequency: assessmentForm.exercise_frequency || null,
        diet_notes: assessmentForm.diet_notes || null,
      };

      setPendingAssessmentPayload(payload);

      let res;
      if (isGuestMode) {
        res = await apiRequest(
          "/doctor/guest-assessment",
          {
            method: "POST",
            body: JSON.stringify(payload),
          },
          auth?.access_token
        );
      } else {
        // Step 1: Real-time preview without writing to DB until doctor approves
        res = await apiRequest(
          `/doctor/patients/${selectedPatient.id}/preview-assessment`,
          {
            method: "POST",
            body: JSON.stringify(payload),
          },
          auth?.access_token
        );
      }

      setAssessmentResult(res);
      setAssessmentStatus("preview");
      setMsg("ML Model prediction generated. Please review the AI output below and click 'Approve Assessment & Save' to record, or 'Re-evaluate' to adjust parameters.");

      // Auto-populate editable diagnosis suggestion headline if available
      if (res?.auto_diagnosis_suggestion) {
        setDiagnosisForm((prev) => ({
          ...prev,
          diagnosis_title: res.auto_diagnosis_suggestion,
          risk_summary: `${res.risk_level} (${res.risk_percentage?.toFixed(1) || (res.risk_probability * 100).toFixed(1)}%)`,
        }));
      }
    } catch (err) {
      setError(err.message || "Failed to process clinical assessment.");
      toast.error(err.message || "Failed to process clinical assessment.");
    } finally {
      setLoading(false);
    }
  };

  // STEP 2: Doctor Approves Assessment & Permanently Saves to DB
  const handleApproveAssessment = async () => {
    if (!pendingAssessmentPayload) {
      setError("No pending assessment data to approve.");
      return;
    }

    if (isGuestMode) {
      setAssessmentStatus("approved");
      setMsg("Guest assessment verified. You can now save it as a draft or convert it into a registered patient.");
      return;
    }

    if (!selectedPatient) return;

    setError("");
    setMsg("");
    setLoading(true);

    try {
      const res = await apiRequest(
        `/doctor/patients/${selectedPatient.id}/record`,
        {
          method: "POST",
          body: JSON.stringify(pendingAssessmentPayload),
        },
        auth?.access_token
      );

      setAssessmentResult(res);
      setAssessmentStatus("approved");
      setMsg(`Assessment approved by physician and permanently saved to patient record.`);
      toast.success(`Assessment approved and saved to patient record.`);
      await loadPatients(selectedPatient.id);
      loadSharedCases();
    } catch (err) {
      setError(err.message || "Failed to commit assessment to database.");
    } finally {
      setLoading(false);
    }
  };

  // RE-EVALUATE: Clears preview output so doctor can edit vitals and rerun
  const handleReassess = () => {
    setAssessmentResult(null);
    setAssessmentStatus("idle");
    setPendingAssessmentPayload(null);
    setMsg("Assessment preview cleared. Adjust clinical inputs and re-run prediction.");
  };

  const handleBloodTestSubmit = async (e) => {
    e.preventDefault();
    if (!selectedPatient) return;
    setError("");
    setMsg("");
    setLoading(true);

    try {
      const payload = {
        hemoglobin: bloodTestForm.hemoglobin ? parseFloat(bloodTestForm.hemoglobin) : null,
        wbc_count: bloodTestForm.wbc_count ? parseFloat(bloodTestForm.wbc_count) : null,
        platelet_count: bloodTestForm.platelet_count ? parseFloat(bloodTestForm.platelet_count) : null,
        fasting_glucose: bloodTestForm.fasting_glucose ? parseFloat(bloodTestForm.fasting_glucose) : null,
        hba1c: bloodTestForm.hba1c ? parseFloat(bloodTestForm.hba1c) : null,
        total_cholesterol: bloodTestForm.total_cholesterol ? parseFloat(bloodTestForm.total_cholesterol) : null,
        hdl: bloodTestForm.hdl ? parseFloat(bloodTestForm.hdl) : null,
        ldl: bloodTestForm.ldl ? parseFloat(bloodTestForm.ldl) : null,
        triglycerides: bloodTestForm.triglycerides ? parseFloat(bloodTestForm.triglycerides) : null,
        creatinine: bloodTestForm.creatinine ? parseFloat(bloodTestForm.creatinine) : null,
        notes: bloodTestForm.notes || null,
      };

      await apiRequest(
        `/doctor/patients/${selectedPatient.id}/blood-test`,
        {
          method: "POST",
          body: JSON.stringify(payload),
        },
        auth?.access_token
      );

      setMsg("Blood test panel recorded.");
      toast.success("Blood test panel recorded.");
      setBloodTestForm({
        hemoglobin: "",
        wbc_count: "",
        platelet_count: "",
        fasting_glucose: "",
        hba1c: "",
        total_cholesterol: "",
        hdl: "",
        ldl: "",
        triglycerides: "",
        creatinine: "",
        notes: "",
      });
      loadPatientData(selectedPatient.id);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
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

  const handleDownloadDiagnosisPdf = async (diagId, patientName) => {
    setPdfLoading(true);
    try {
      await downloadPdfReport(
        `/reports/diagnosis/${diagId}/pdf`,
        `diagnosis_report_${(patientName || "patient").toLowerCase().replace(/\s+/g, "_")}_${diagId}.pdf`,
        auth?.access_token
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setPdfLoading(false);
    }
  };

  const handleViewPatientReport = async (patientId, patientName, diagId = null) => {
    setReportModalOpen(true);
    setReportLoading(true);
    setReportPatientName(patientName || "patient");
    const endpoint = diagId ? `/reports/diagnosis/${diagId}/pdf` : `/reports/patient/${patientId}/latest-pdf`;
    setReportPdfEndpoint(endpoint);
    try {
      const data = await fetchStructuredPatientReport(patientId, diagId, auth?.access_token);
      setReportData(data);
    } catch (err) {
      console.error("Failed to load structured report:", err);
      toast.error("Failed to load clinical report data.");
    } finally {
      setReportLoading(false);
    }
  };

  const isDemographicsLocked = Boolean(
    !isGuestMode &&
    selectedPatient &&
    (selectedPatient.is_demographics_locked ||
      (selectedPatient.age !== null && selectedPatient.age !== undefined && selectedPatient.sex !== null && selectedPatient.sex !== undefined))
  );

  const procuredMeds = medicines.filter((m) => m.status === "procured");
  const requestedMeds = medicines.filter((m) => m.status === "requested");
  const normalizedSharedSearch = sharedSearch.trim().toLowerCase();
  const filteredSharedCases = sharedCases.filter((patient) => {
    const matchesSearch = !normalizedSharedSearch || [
      patient.name,
      patient.email,
      patient.assigned_doctor_name,
      patient.assigned_doctor_specialty,
      patient.latest_diagnosis_title,
    ].some((value) => String(value || "").toLowerCase().includes(normalizedSharedSearch));
    const matchesRisk = sharedRiskFilter === "all" || patient.latest_risk_level === sharedRiskFilter;
    return matchesSearch && matchesRisk;
  });
  const sharedHistoryCount = sharedCases.filter((patient) => patient.has_shared_history).length;
  const mySharedCaseCount = sharedCases.filter((patient) => patient.is_my_patient).length;
  const highRiskSharedCount = sharedCases.filter((patient) => patient.latest_risk_level === "High Risk").length;
  const riskBadgeClass = (riskLevel) => {
    if (riskLevel === "High Risk") return "badge-high";
    if (riskLevel === "Moderate Risk") return "badge-med";
    if (riskLevel === "Low Risk") return "badge-low";
    return "badge-neutral";
  };

  return (
    <div className="container">
      {msg && <div className="alert alert-success">{msg}</div>}
      {error && <div className="alert alert-error">{error}</div>}

      {dataLoading ? (
        <>
          <SkeletonTable rows={1} cols={6} />
          <div style={{ display: "grid", gridTemplateColumns: "220px 1fr", gap: 16, marginTop: 16 }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <div className="skeleton" style={{ height: 44 }} />
              <div className="skeleton" style={{ height: 44 }} />
              <SkeletonList items={4} />
            </div>
            <SkeletonTable rows={6} cols={5} />
          </div>
        </>
      ) : (
      <>
      {/* Main Mode Navigation */}
      <div className="nav-buttons-row" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14, flexWrap: "wrap", gap: 8 }}>
        <div className="nav-buttons-row" style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          <button
            type="button"
            className={mainView === "my_patients" && !isGuestMode ? "" : "btn-secondary"}
            onClick={() => {
              setMainView("my_patients");
              setIsGuestMode(false);
              if (patients.length > 0 && !selectedPatient) setSelectedPatient(patients[0]);
            }}
          >
            My Assigned Patients ({patients.length})
          </button>

          <button
            type="button"
            className={mainView === "requests" ? "" : "btn-secondary"}
            onClick={() => {
              setMainView("requests");
              setIsGuestMode(false);
              loadPatientRequests();
            }}
          >
            Patient Requests ({patientRequests.length})
          </button>

          <button
            type="button"
            className={mainView === "medicines" ? "" : "btn-secondary"}
            onClick={() => {
              setMainView("medicines");
              setIsGuestMode(false);
              loadMedicines();
            }}
          >
            Medicines & Inventory ({procuredMeds.length})
          </button>

          <button
            type="button"
            className={isGuestMode ? "" : "btn-secondary"}
            onClick={handleSelectGuestMode}
            style={isGuestMode ? { backgroundColor: "#475569", borderColor: "#475569" } : {}}
          >
            Guest / Walk-in Mode
          </button>

          <button
            type="button"
            className={mainView === "shared_area" ? "" : "btn-secondary"}
            onClick={() => {
              setMainView("shared_area");
              setIsGuestMode(false);
              loadSharedCases();
            }}
          >
            Cross-Doctor Shared Area ({sharedCases.length})
          </button>

          <button
            type="button"
            className={mainView === "drafts" ? "" : "btn-secondary"}
            onClick={() => {
              setMainView("drafts");
              loadDrafts();
            }}
          >
            Saved Drafts ({drafts.length})
          </button>

          <button
            type="button"
            className={mainView === "hospital_directory" ? "" : "btn-secondary"}
            onClick={() => {
              setMainView("hospital_directory");
              setIsGuestMode(false);
              loadHospitalDirectory();
            }}
          >
            🏥 Emergency Hospitals
          </button>

          <button
            type="button"
            className={mainView === "my_profile" ? "" : "btn-secondary"}
            onClick={() => {
              setMainView("my_profile");
              setIsGuestMode(false);
            }}
          >
            My Profile
          </button>
        </div>

        {selectedPatient && !isGuestMode && (
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button
              type="button"
              onClick={() => handleViewPatientReport(selectedPatient.id, selectedPatient.name)}
              style={{ backgroundColor: "#0284c7", borderColor: "#0284c7", color: "#ffffff" }}
            >
              📋 View Patient Report
            </button>
            <button
              type="button"
              onClick={() => handleDownloadPatientPdf(selectedPatient.id, selectedPatient.name)}
              disabled={pdfLoading}
              style={{ backgroundColor: "#15803d", borderColor: "#15803d" }}
            >
              {pdfLoading ? "Generating..." : "Export Medical PDF"}
            </button>
          </div>
        )}
      </div>

      {/* VIEW 1: MY PATIENTS & CLINICAL ASSESSMENT */}
      {mainView === "my_patients" && (
        <div style={{ display: "grid", gridTemplateColumns: "240px 1fr", gap: 16 }}>
          {/* Left Sidebar */}
          <div className="card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
              <h3 style={{ margin: 0 }}>Roster</h3>
              <span style={{ fontSize: "0.8rem", color: "#64748b" }}>{patients.length} total</span>
            </div>

            <button
              type="button"
              onClick={handleSelectGuestMode}
              style={{ width: "100%", marginBottom: 6, backgroundColor: isGuestMode ? "#475569" : "#ffffff", color: isGuestMode ? "#ffffff" : "#0f172a", border: "1px solid #cbd5e1" }}
            >
              Evaluate Guest Patient
            </button>

            <button
              type="button"
              onClick={() => setShowAddPatientModal(true)}
              style={{ width: "100%", marginBottom: 12 }}
            >
              Register New Patient
            </button>

            {isGuestMode && (
              <div style={{ padding: "8px 10px", borderRadius: 3, backgroundColor: "#f1f5f9", border: "1px solid #cbd5e1", marginBottom: 8 }}>
                <strong style={{ fontSize: "0.85rem" }}>{assessmentForm.guest_name || "Guest Patient"}</strong>
                <div style={{ fontSize: "0.75rem", color: "#64748b" }}>Unassigned Walk-in</div>
              </div>
            )}

            <div style={{ fontSize: "0.8rem", fontWeight: 600, color: "#64748b", marginBottom: 6 }}>Assigned Patients:</div>
            {patients.length === 0 ? (
              <p style={{ fontSize: "0.85rem", color: "#64748b" }}>No patients assigned.</p>
            ) : (
              <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: 4, padding: 0, margin: 0 }}>
                {patients.map((p) => (
                  <li
                    key={p.id}
                    onClick={() => {
                      setSelectedPatient(p);
                      setIsGuestMode(false);
                    }}
                    style={{
                      padding: "8px 10px",
                      borderRadius: 3,
                      border: "1px solid",
                      cursor: "pointer",
                      backgroundColor: (!isGuestMode && selectedPatient?.id === p.id) ? "#e0f2fe" : "#ffffff",
                      borderColor: (!isGuestMode && selectedPatient?.id === p.id) ? "#0284c7" : "#e2e8f0",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <strong style={{ fontSize: "0.85rem" }}>{p.name}</strong>
                      {p.age && <span style={{ fontSize: "0.75rem", color: "#64748b" }}>{p.age}y</span>}
                    </div>
                    <div style={{ fontSize: "0.75rem", color: "#64748b" }}>{p.email}</div>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Right Main Content */}
          <div>
            {/* Live Loading Indicator Bar */}
            {loading && <div className="loading-bar" />}

            {/* Assessment Prediction Result Panel (Prominently Rendered with Auto-Scroll Anchor and Approval Gate) */}
            {assessmentResult && (
              <div
                ref={resultRef}
                className="result-card-highlight"
                style={{
                  marginBottom: 16,
                  padding: 16,
                  borderRadius: 4,
                  border: "1px solid",
                  borderColor: assessmentResult.risk_level === "Critical Risk" ? "#991b1b" : assessmentResult.risk_level === "High Risk" ? "#fca5a5" : assessmentResult.risk_level === "Moderate Risk" ? "#fde68a" : "#bbf7d0",
                  backgroundColor: assessmentResult.risk_level === "Critical Risk" ? "#fef2f2" : assessmentResult.risk_level === "High Risk" ? "#fef2f2" : assessmentResult.risk_level === "Moderate Risk" ? "#fffbeb" : "#f0fdf4",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ fontSize: "0.8rem", color: "#475569", textTransform: "uppercase", fontWeight: 700 }}>
                        AI Model Prediction Output
                      </span>
                      {assessmentStatus === "preview" && (
                        <span className="badge badge-med">Pending Doctor Approval</span>
                      )}
                      {assessmentStatus === "approved" && (
                        <span className="badge badge-low">Verified & Recorded</span>
                      )}
                    </div>

                    {/* Auto Diagnosis Heading (Feature 5) */}
                    <h3 style={{ margin: "4px 0 0", color: "#0f172a", fontSize: "1.15rem" }}>
                      {assessmentResult.auto_diagnosis_suggestion || `${assessmentResult.risk_level} Clinical Evaluation`}
                    </h3>
                  </div>
                  <span
                    className={`badge ${
                      assessmentResult.risk_level === "Critical Risk"
                        ? "badge-critical"
                        : assessmentResult.risk_level === "High Risk"
                        ? "badge-high"
                        : assessmentResult.risk_level === "Moderate Risk"
                        ? "badge-med"
                        : "badge-low"
                    }`}
                    style={{ fontSize: "0.85rem", padding: "4px 10px" }}
                  >
                    {assessmentResult.risk_level} ({(assessmentResult.risk_percentage ?? assessmentResult.risk_probability * 100).toFixed(1)}%)
                  </span>
                </div>

                <div style={{ marginBottom: 12 }}>
                  <div style={{ height: 8, width: "100%", backgroundColor: "#e2e8f0", borderRadius: 4, overflow: "hidden" }}>
                    <div
                      style={{
                        width: `${Math.min(100, assessmentResult.risk_percentage ?? assessmentResult.risk_probability * 100)}%`,
                        height: "100%",
                        backgroundColor: assessmentResult.risk_level === "Critical Risk" ? "#991b1b" : assessmentResult.risk_level === "High Risk" ? "#dc2626" : assessmentResult.risk_level === "Moderate Risk" ? "#d97706" : "#16a34a",
                      }}
                    />
                  </div>
                </div>

                <div style={{ marginBottom: 12 }}>
                  <div style={{ fontSize: "0.85rem", fontWeight: 600, color: "#334155", marginBottom: 6 }}>Key Contributing Risk Factors (TreeSHAP):</div>
                  {assessmentResult.reasons && assessmentResult.reasons.length > 0 ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                      {assessmentResult.reasons.map((r, idx) => (
                        <div key={idx} style={{ fontSize: "0.8rem", color: "#334155", display: "flex", justifyContent: "space-between", padding: "5px 10px", backgroundColor: "#ffffff", border: "1px solid #e2e8f0", borderRadius: 3 }}>
                          <span><strong>{r.label || r.feature}:</strong> {r.reason}</span>
                          <span style={{ color: "#64748b", textTransform: "capitalize", fontSize: "0.75rem" }}>{r.impact}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <ul style={{ paddingLeft: 18, fontSize: "0.8rem" }}>
                      {assessmentResult.top_features?.map((f, idx) => <li key={idx}>{f}</li>)}
                    </ul>
                  )}
                </div>

                {assessmentResult.recommendations && assessmentResult.recommendations.length > 0 && (
                  <div style={{ marginBottom: 12 }}>
                    <div style={{ fontSize: "0.85rem", fontWeight: 600, color: "#334155", marginBottom: 4 }}>Actionable Clinical Recommendations:</div>
                    <ul style={{ paddingLeft: 18, fontSize: "0.8rem", color: "#334155" }}>
                      {assessmentResult.recommendations.map((rec, idx) => <li key={idx}>{rec}</li>)}
                    </ul>
                  </div>
                )}

                {/* DOCTOR APPROVAL GATE & RE-ASSESSMENT CONTROLS */}
                <div style={{ display: "flex", gap: 8, marginTop: 12, paddingTop: 10, borderTop: "1px solid rgba(0,0,0,0.08)", flexWrap: "wrap" }}>
                  {assessmentStatus === "preview" && (
                    <>
                      <button
                        type="button"
                        onClick={handleApproveAssessment}
                        disabled={loading}
                        style={{ backgroundColor: "#15803d", borderColor: "#15803d", flex: 2 }}
                      >
                        Approve Assessment & Save to Medical Record
                      </button>
                      <button
                        type="button"
                        className="btn-secondary"
                        onClick={handleReassess}
                        disabled={loading}
                        style={{ flex: 1 }}
                      >
                        Re-evaluate / Adjust
                      </button>
                    </>
                  )}

                  {assessmentStatus === "approved" && !isGuestMode && (
                    <button
                      type="button"
                      onClick={() => setActiveTab("diagnosis")}
                      style={{ backgroundColor: "#0284c7", width: "100%" }}
                    >
                      Proceed to Write Treatment Plan & Prescriptions
                    </button>
                  )}
                </div>
              </div>
            )}

            {isGuestMode || selectedPatient ? (
              <div className="card">
                {/* Header Bar */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #e2e8f0", paddingBottom: 8, marginBottom: 12 }}>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      {isGuestMode ? (
                        <>
                          <h3 style={{ margin: 0 }}>Guest Patient Evaluation</h3>
                          <span className="badge badge-neutral">Walk-in Mode</span>
                        </>
                      ) : (
                        <>
                          <h3 style={{ margin: 0 }}>Patient: {selectedPatient.name}</h3>
                          {isDemographicsLocked ? (
                            <span className="badge badge-med">
                              Demographics Locked: {selectedPatient.age}y, {selectedPatient.sex === 1 ? "Male" : "Female"}
                            </span>
                          ) : (
                            <span className="badge badge-neutral">Demographics Pending</span>
                          )}
                        </>
                      )}
                    </div>
                    <div style={{ fontSize: "0.8rem", color: "#64748b", marginTop: 2 }}>
                      {isGuestMode ? "Walk-in risk prediction mode (no registration required)." : selectedPatient.email}
                    </div>
                  </div>

                  <div style={{ display: "flex", gap: 6 }}>
                    {isGuestMode ? (
                      <>
                        <button
                          type="button"
                          className="btn-secondary"
                          onClick={handleSaveAsDraft}
                          disabled={loading}
                        >
                          Save Draft
                        </button>
                        <button
                          type="button"
                          disabled={!assessmentResult}
                          onClick={async () => {
                            let draftId = convertDraftTarget?.id;
                            if (!draftId || draftId === 0) {
                              const draftRes = await apiRequest(
                                "/doctor/drafts",
                                {
                                  method: "POST",
                                  body: JSON.stringify({
                                    draft_name: assessmentForm.guest_name || "Walk-in Guest Assessment",
                                    guest_identifier: assessmentForm.guest_name || "Walk-in Guest",
                                    data: assessmentForm,
                                    risk_level: assessmentResult?.risk_level || null,
                                    risk_probability: assessmentResult?.risk_probability || null,
                                  }),
                                },
                                auth?.access_token
                              );
                              draftId = draftRes.id;
                              setConvertDraftTarget(draftRes);
                              loadDrafts();
                            }
                            setConvertForm({
                              patient_name: assessmentForm.guest_name || "New Patient",
                              patient_email: "",
                              password: "Demo@123",
                              phone_number: "",
                              emergency_contact_name: "",
                              emergency_contact_phone: "",
                              address: "",
                            });
                            setShowConvertModal(true);
                          }}
                        >
                          Convert to Patient
                        </button>
                      </>
                    ) : (
                      <button
                        type="button"
                        className="btn-secondary"
                        onClick={() => {
                          setShowTransferModal(true);
                          setTransferTargetDocId("");
                          setTransferReason("");
                        }}
                      >
                        Transfer Patient
                      </button>
                    )}
                  </div>
                </div>

                {/* Tab Navigation */}
                {!isGuestMode && (
                  <div style={{ display: "flex", gap: 6, marginBottom: 14 }}>
                    <button
                      type="button"
                      className={activeTab === "assessment" ? "" : "btn-secondary"}
                      onClick={() => setActiveTab("assessment")}
                    >
                      Clinical Assessment
                    </button>
                    <button
                      type="button"
                      className={activeTab === "diagnosis" ? "" : "btn-secondary"}
                      onClick={() => setActiveTab("diagnosis")}
                    >
                      Diagnosis & Prescriptions ({patientDiagnoses.length})
                    </button>
                    <button
                      type="button"
                      className={activeTab === "blood_test" ? "" : "btn-secondary"}
                      onClick={() => setActiveTab("blood_test")}
                    >
                      Blood Test Panel ({bloodTests.length})
                    </button>
                    <button
                      type="button"
                      className={activeTab === "collaborative" ? "" : "btn-secondary"}
                      onClick={() => setActiveTab("collaborative")}
                    >
                      Shared Case History
                    </button>
                  </div>
                )}

                {/* TAB 1: Assessment Form */}
                {(activeTab === "assessment" || isGuestMode) && (
                  <form className="form" onSubmit={handleAssessmentSubmit}>
                    {isGuestMode && (
                      <div className="form-group">
                        <label>Guest Patient Name / Reference</label>
                        <input
                          type="text"
                          placeholder="e.g. Walk-in Guest"
                          value={assessmentForm.guest_name}
                          onChange={(e) => setAssessmentForm({ ...assessmentForm, guest_name: e.target.value })}
                        />
                      </div>
                    )}

                    <h4>1. Demographics & Vitals</h4>
                    <div className="form-grid">
                      <div className="form-group">
                        <label>Age (years) {isDemographicsLocked ? "(Locked)" : "*"}</label>
                        <input
                          type="number"
                          step="any"
                          value={assessmentForm.age}
                          onChange={(e) => setAssessmentForm({ ...assessmentForm, age: e.target.value })}
                          placeholder="Age in years"
                          disabled={isDemographicsLocked}
                          required
                        />
                      </div>
                      <div className="form-group">
                        <label>Biological Sex {isDemographicsLocked ? "(Locked)" : "*"}</label>
                        <select
                          value={assessmentForm.sex}
                          onChange={(e) => setAssessmentForm({ ...assessmentForm, sex: e.target.value })}
                          disabled={isDemographicsLocked}
                        >
                          <option value="1">Male</option>
                          <option value="0">Female</option>
                        </select>
                      </div>
                      <div className="form-group">
                        <label>Systolic BP (mmHg) *</label>
                        <input
                          type="number"
                          value={assessmentForm.systolic_bp}
                          onChange={(e) => setAssessmentForm({ ...assessmentForm, systolic_bp: e.target.value })}
                          placeholder="e.g. 130"
                          required
                        />
                      </div>
                      <div className="form-group">
                        <label>Diastolic BP (mmHg) *</label>
                        <input
                          type="number"
                          value={assessmentForm.diastolic_bp}
                          onChange={(e) => setAssessmentForm({ ...assessmentForm, diastolic_bp: e.target.value })}
                          placeholder="e.g. 85"
                          required
                        />
                      </div>
                      <div className="form-group">
                        <label>Max Heart Rate (bpm)</label>
                        <input
                          type="number"
                          step="any"
                          value={assessmentForm.max_heart_rate}
                          onChange={(e) => setAssessmentForm({ ...assessmentForm, max_heart_rate: e.target.value })}
                          placeholder="e.g. 145"
                        />
                      </div>
                      <div className="form-group">
                        <label>BMI (kg/m²)</label>
                        <input
                          type="number"
                          step="any"
                          value={assessmentForm.bmi}
                          onChange={(e) => setAssessmentForm({ ...assessmentForm, bmi: e.target.value })}
                          placeholder="e.g. 26.5"
                        />
                      </div>
                    </div>

                    <h4>2. Cardiac Presentation & Symptoms</h4>
                    <div className="form-grid">
                      <div className="form-group">
                        <label>Chest Pain Presentation</label>
                        <select
                          value={assessmentForm.chest_pain_type}
                          onChange={(e) => setAssessmentForm({ ...assessmentForm, chest_pain_type: e.target.value })}
                        >
                          <option value="3">Asymptomatic</option>
                          <option value="0">Typical Angina (Exertional Pressure)</option>
                          <option value="1">Atypical Angina (Sharp Non-exertional)</option>
                          <option value="2">Non-Anginal Discomfort</option>
                        </select>
                      </div>
                      <div className="form-group">
                        <label>Exercise Angina</label>
                        <select
                          value={assessmentForm.exercise_angina}
                          onChange={(e) => setAssessmentForm({ ...assessmentForm, exercise_angina: e.target.value })}
                        >
                          <option value="0">No exertional angina</option>
                          <option value="1">Yes, exertional angina present</option>
                        </select>
                      </div>
                      <div className="form-group">
                        <label>ECG ST Depression (mm)</label>
                        <select
                          value={assessmentForm.st_depression}
                          onChange={(e) => setAssessmentForm({ ...assessmentForm, st_depression: e.target.value })}
                        >
                          <option value="0.0">0.0 mm (Normal)</option>
                          <option value="0.5">0.5 mm (Mild)</option>
                          <option value="1.0">1.0 mm (Moderate)</option>
                          <option value="2.0">2.0 mm (Significant)</option>
                          <option value="3.0">3.0+ mm (Severe)</option>
                        </select>
                      </div>
                    </div>

                    <h4>3. Metabolic & Lab Profile</h4>
                    <div className="form-grid">
                      <div className="form-group">
                        <label>Total Cholesterol (mg/dL)</label>
                        <input
                          type="number"
                          step="any"
                          value={assessmentForm.cholesterol}
                          onChange={(e) => setAssessmentForm({ ...assessmentForm, cholesterol: e.target.value })}
                          placeholder="e.g. 210"
                        />
                      </div>
                      <div className="form-group">
                        <label>Fasting Blood Sugar</label>
                        <select
                          value={assessmentForm.fasting_blood_sugar}
                          onChange={(e) => setAssessmentForm({ ...assessmentForm, fasting_blood_sugar: e.target.value })}
                        >
                          <option value="0">Normal (le 120 mg/dL)</option>
                          <option value="1">Elevated (gt 120 mg/dL)</option>
                        </select>
                      </div>
                    </div>

                    <h4>4. Comorbidities</h4>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, padding: 10, backgroundColor: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 3 }}>
                      <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.85rem", cursor: "pointer" }}>
                        <input
                          type="checkbox"
                          checked={assessmentForm.hypertension}
                          onChange={(e) => setAssessmentForm({ ...assessmentForm, hypertension: e.target.checked })}
                        />
                        <span>Hypertension</span>
                      </label>
                      <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.85rem", cursor: "pointer" }}>
                        <input
                          type="checkbox"
                          checked={assessmentForm.diabetes}
                          onChange={(e) => setAssessmentForm({ ...assessmentForm, diabetes: e.target.checked })}
                        />
                        <span>Diabetes Mellitus</span>
                      </label>
                      <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.85rem", cursor: "pointer" }}>
                        <input
                          type="checkbox"
                          checked={assessmentForm.family_history_cad}
                          onChange={(e) => setAssessmentForm({ ...assessmentForm, family_history_cad: e.target.checked })}
                        />
                        <span>Family CAD History</span>
                      </label>
                      <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.85rem", cursor: "pointer" }}>
                        <input
                          type="checkbox"
                          checked={assessmentForm.prior_heart_event}
                          onChange={(e) => setAssessmentForm({ ...assessmentForm, prior_heart_event: e.target.checked })}
                        />
                        <span>Prior Cardiac Event</span>
                      </label>
                    </div>

                    <h4>5. Lifestyle</h4>
                    <div className="form-grid">
                      <div className="form-group">
                        <label>Smoking Status</label>
                        <select
                          value={assessmentForm.smoking}
                          onChange={(e) => setAssessmentForm({ ...assessmentForm, smoking: e.target.value })}
                        >
                          <option value="0">Non-Smoker</option>
                          <option value="1">Smoker / Former Smoker</option>
                        </select>
                      </div>
                      <div className="form-group">
                        <label>Physical Activity</label>
                        <select
                          value={assessmentForm.exercise_frequency}
                          onChange={(e) => setAssessmentForm({ ...assessmentForm, exercise_frequency: e.target.value })}
                        >
                          <option value="Sedentary (<1x/week)">Sedentary</option>
                          <option value="Light (1-2x/week)">Light</option>
                          <option value="Moderate (3-4x/week)">Moderate</option>
                          <option value="Active (5+x/week)">Active</option>
                        </select>
                      </div>
                    </div>

                    <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
                      <button type="submit" disabled={loading} style={{ flex: 2 }}>
                        {loading ? "Running AI Inference..." : (isGuestMode ? "Run AI Risk Prediction" : "Run AI Risk Assessment (Preview)")}
                      </button>
                      {isGuestMode && (
                        <button type="button" className="btn-secondary" onClick={handleSaveAsDraft} disabled={loading} style={{ flex: 1 }}>
                          Save Draft
                        </button>
                      )}
                    </div>
                  </form>
                )}

                {/* TAB 2: Diagnosis & Prescriptions */}
                {activeTab === "diagnosis" && !isGuestMode && (
                  <div>
                    <form className="form" onSubmit={handleDiagnosisSubmit} style={{ marginBottom: 16 }}>
                      <h4>Record Physician Diagnosis & Prescriptions</h4>
                      
                      {/* Auto-suggested / Editable Diagnosis Title */}
                      <div className="form-group">
                        <label>Diagnosis Heading (Auto-Generated from ML / Fully Editable) *</label>
                        <input
                          type="text"
                          placeholder="e.g. Essential Hypertension & Dyslipidemia"
                          value={diagnosisForm.diagnosis_title}
                          onChange={(e) => setDiagnosisForm({ ...diagnosisForm, diagnosis_title: e.target.value })}
                          required
                        />
                      </div>

                      <div className="form-group">
                        <label>Clinical Notes & Rationale *</label>
                        <textarea
                          rows={3}
                          placeholder="Physician clinical findings, symptom history, and auscultation..."
                          value={diagnosisForm.clinical_notes}
                          onChange={(e) => setDiagnosisForm({ ...diagnosisForm, clinical_notes: e.target.value })}
                          required
                        />
                      </div>

                      <div className="form-grid">
                        <div className="form-group">
                          <label>Treatment & Care Plan</label>
                          <textarea
                            rows={2}
                            placeholder="Lifestyle modifications, dietary regimen, activity advice..."
                            value={diagnosisForm.treatment_plan}
                            onChange={(e) => setDiagnosisForm({ ...diagnosisForm, treatment_plan: e.target.value })}
                          />
                        </div>
                        <div className="form-group">
                          <label>Prescriptions & Dosage</label>
                          <textarea
                            rows={2}
                            placeholder="Medications prescribed (or select from your inventory below)..."
                            value={diagnosisForm.prescriptions}
                            onChange={(e) => setDiagnosisForm({ ...diagnosisForm, prescriptions: e.target.value })}
                          />
                        </div>
                      </div>

                      {/* Multi-Select Medicine Selector from Procured Inventory */}
                      {procuredMeds.length > 0 && (
                        <div style={{ padding: 10, backgroundColor: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 3, marginTop: 4 }}>
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                            <strong style={{ fontSize: "0.85rem" }}>Select Medicines from Your Procured Inventory:</strong>
                            <button
                              type="button"
                              className="btn-secondary"
                              style={{ fontSize: "0.75rem", padding: "2px 8px" }}
                              onClick={handleAddMedicinesToPrescription}
                            >
                              Add Selected to Prescriptions
                            </button>
                          </div>
                          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 6 }}>
                            {procuredMeds.map((med) => (
                              <label key={med.id} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.8rem", cursor: "pointer" }}>
                                <input
                                  type="checkbox"
                                  checked={selectedMedicineIds.includes(med.id)}
                                  onChange={(e) => {
                                    if (e.target.checked) {
                                      setSelectedMedicineIds([...selectedMedicineIds, med.id]);
                                    } else {
                                      setSelectedMedicineIds(selectedMedicineIds.filter((id) => id !== med.id));
                                    }
                                  }}
                                />
                                <span>{med.name} <span style={{ color: "#64748b", fontSize: "0.75rem" }}>({med.quantity} {med.unit})</span></span>
                              </label>
                            ))}
                          </div>
                        </div>
                      )}

                      <button type="submit" disabled={loading} style={{ alignSelf: "flex-start", marginTop: 8 }}>
                        {loading ? "Saving..." : "Save Diagnosis"}
                      </button>
                    </form>

                    <h4>Patient Diagnosis History ({patientDiagnoses.length})</h4>
                    {patientDiagnoses.length === 0 ? (
                      <p style={{ fontSize: "0.85rem", color: "#64748b" }}>No diagnoses recorded for this patient.</p>
                    ) : (
                      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                        {patientDiagnoses.map((diag) => (
                          <div key={diag.id} style={{ padding: 12, border: "1px solid #e2e8f0", borderRadius: 3, backgroundColor: "#f8fafc" }}>
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                              <div>
                                <strong style={{ fontSize: "0.95rem" }}>{diag.diagnosis_title}</strong>
                                <div style={{ fontSize: "0.75rem", color: "#64748b" }}>
                                  By Dr. {diag.doctor_name} ({diag.doctor_specialization || "Physician"}) - {new Date(diag.created_at).toLocaleString()}
                                </div>
                              </div>
                              <div style={{ display: "flex", gap: 6 }}>
                                <button
                                  type="button"
                                  className="btn-secondary"
                                  onClick={() => handleViewPatientReport(selectedPatient.id, selectedPatient.name, diag.id)}
                                  style={{ fontSize: "0.75rem", padding: "3px 8px" }}
                                >
                                  View Report
                                </button>
                                <button
                                  type="button"
                                  className="btn-secondary"
                                  onClick={() => handleDownloadDiagnosisPdf(diag.id, selectedPatient.name)}
                                  disabled={pdfLoading}
                                  style={{ fontSize: "0.75rem", padding: "3px 8px" }}
                                >
                                  Export PDF
                                </button>
                              </div>
                            </div>
                            <p style={{ fontSize: "0.85rem", color: "#334155", margin: "6px 0" }}>{diag.clinical_notes}</p>
                            {diag.treatment_plan && <div style={{ fontSize: "0.8rem", color: "#475569" }}><strong>Plan:</strong> {diag.treatment_plan}</div>}
                            {diag.prescriptions && <div style={{ fontSize: "0.8rem", color: "#0369a1" }}><strong>Rx:</strong> {diag.prescriptions}</div>}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* TAB 3: Blood Test Form */}
                {activeTab === "blood_test" && !isGuestMode && (
                  <form className="form" onSubmit={handleBloodTestSubmit}>
                    <h4>Complete Blood Count (CBC)</h4>
                    <div className="form-grid">
                      <div className="form-group">
                        <label>Hemoglobin (g/dL)</label>
                        <input
                          type="number"
                          step="any"
                          value={bloodTestForm.hemoglobin}
                          onChange={(e) => setBloodTestForm({ ...bloodTestForm, hemoglobin: e.target.value })}
                          placeholder="e.g. 14.5"
                        />
                      </div>
                      <div className="form-group">
                        <label>WBC Count (10³/µL)</label>
                        <input
                          type="number"
                          step="any"
                          value={bloodTestForm.wbc_count}
                          onChange={(e) => setBloodTestForm({ ...bloodTestForm, wbc_count: e.target.value })}
                          placeholder="e.g. 6.5"
                        />
                      </div>
                      <div className="form-group">
                        <label>Platelet Count (10³/µL)</label>
                        <input
                          type="number"
                          step="any"
                          value={bloodTestForm.platelet_count}
                          onChange={(e) => setBloodTestForm({ ...bloodTestForm, platelet_count: e.target.value })}
                          placeholder="e.g. 240"
                        />
                      </div>
                    </div>

                    <h4>Metabolic Panel</h4>
                    <div className="form-grid">
                      <div className="form-group">
                        <label>Fasting Glucose (mg/dL)</label>
                        <input
                          type="number"
                          step="any"
                          value={bloodTestForm.fasting_glucose}
                          onChange={(e) => setBloodTestForm({ ...bloodTestForm, fasting_glucose: e.target.value })}
                          placeholder="e.g. 95"
                        />
                      </div>
                      <div className="form-group">
                        <label>HbA1c (%)</label>
                        <input
                          type="number"
                          step="any"
                          value={bloodTestForm.hba1c}
                          onChange={(e) => setBloodTestForm({ ...bloodTestForm, hba1c: e.target.value })}
                          placeholder="e.g. 5.6"
                        />
                      </div>
                      <div className="form-group">
                        <label>Total Cholesterol (mg/dL)</label>
                        <input
                          type="number"
                          step="any"
                          value={bloodTestForm.total_cholesterol}
                          onChange={(e) => setBloodTestForm({ ...bloodTestForm, total_cholesterol: e.target.value })}
                          placeholder="e.g. 210"
                        />
                      </div>
                      <div className="form-group">
                        <label>HDL (mg/dL)</label>
                        <input
                          type="number"
                          step="any"
                          value={bloodTestForm.hdl}
                          onChange={(e) => setBloodTestForm({ ...bloodTestForm, hdl: e.target.value })}
                          placeholder="e.g. 50"
                        />
                      </div>
                      <div className="form-group">
                        <label>LDL (mg/dL)</label>
                        <input
                          type="number"
                          step="any"
                          value={bloodTestForm.ldl}
                          onChange={(e) => setBloodTestForm({ ...bloodTestForm, ldl: e.target.value })}
                          placeholder="e.g. 125"
                        />
                      </div>
                    </div>

                    <h4>Renal Panel</h4>
                    <div className="form-grid">
                      <div className="form-group">
                        <label>Serum Creatinine (mg/dL)</label>
                        <input
                          type="number"
                          step="any"
                          value={bloodTestForm.creatinine}
                          onChange={(e) => setBloodTestForm({ ...bloodTestForm, creatinine: e.target.value })}
                          placeholder="e.g. 0.9"
                        />
                      </div>
                      <div className="form-group" style={{ gridColumn: "span 2" }}>
                        <label>Notes</label>
                        <input
                          type="text"
                          value={bloodTestForm.notes}
                          onChange={(e) => setBloodTestForm({ ...bloodTestForm, notes: e.target.value })}
                          placeholder="Observations..."
                        />
                      </div>
                    </div>

                    <button type="submit" disabled={loading}>
                      {loading ? "Recording..." : "Save Blood Test"}
                    </button>
                  </form>
                )}

                {/* TAB 4: Collaborative File */}
                {activeTab === "collaborative" && !isGuestMode && (
                  <div>
                    {loading ? (
                      <p style={{ color: "#64748b" }}>Loading case history...</p>
                    ) : collaborativeFile ? (
                      <div>
                        <div style={{ marginBottom: 16 }}>
                          <h4>Referral & Transfer Timeline</h4>
                          {collaborativeFile.transfers.length === 0 ? (
                            <p style={{ fontSize: "0.85rem", color: "#64748b" }}>Direct assignment (no transfers).</p>
                          ) : (
                            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                              {collaborativeFile.transfers.map((tx) => (
                                <div key={tx.id} style={{ padding: 8, backgroundColor: "#fef3c7", border: "1px solid #fde68a", borderRadius: 3, fontSize: "0.85rem" }}>
                                  <strong>{tx.date}</strong>: From {tx.from_doctor} to {tx.to_doctor}
                                  <div style={{ color: "#92400e", fontSize: "0.8rem" }}>Reason: {tx.reason}</div>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>

                        <div>
                          <h4>Multi-Doctor Diagnoses</h4>
                          {collaborativeFile.diagnoses.length === 0 ? (
                            <p style={{ fontSize: "0.85rem", color: "#64748b" }}>No diagnoses on record.</p>
                          ) : (
                            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                              {collaborativeFile.diagnoses.map((d) => (
                                <div key={d.id} style={{ padding: 10, backgroundColor: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 3 }}>
                                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                                    <strong>{d.diagnosis_title}</strong>
                                    <span style={{ fontSize: "0.75rem", color: "#64748b" }}>{d.created_at}</span>
                                  </div>
                                  <div style={{ fontSize: "0.75rem", color: "#64748b" }}>Attending: Dr. {d.doctor_name} ({d.doctor_specialty})</div>
                                  <div style={{ fontSize: "0.85rem", color: "#334155", marginTop: 4 }}>{d.clinical_notes}</div>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    ) : null}
                  </div>
                )}
              </div>
            ) : (
              <div className="card">
                <p style={{ color: "#64748b" }}>Select a patient from the roster or enter Guest Mode to begin.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* VIEW 2: PATIENT REQUESTS QUEUE */}
      {mainView === "requests" && (
        <div className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <h3 style={{ margin: 0 }}>Self-Registered Patient Intake & Forwarding Queue</h3>
            <span style={{ fontSize: "0.8rem", color: "#64748b" }}>{patientRequests.length} pending request{patientRequests.length !== 1 ? "s" : ""}</span>
          </div>

          {patientRequests.length === 0 ? (
            <p style={{ fontSize: "0.85rem", color: "#64748b" }}>No pending patient intake requests in your queue.</p>
          ) : (
            <div className="table-wrapper">
              <table className="table">
                <thead>
                  <tr>
                    <th>Patient Name</th>
                    <th>Email</th>
                    <th>Department Preference</th>
                    <th>Requested Doctor</th>
                    <th>Status</th>
                    <th>Received Date</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {patientRequests.map((req) => (
                    <tr key={req.id}>
                      <td><strong>{req.patient_name}</strong></td>
                      <td>{req.patient_email}</td>
                      <td>{req.department_preference || "Cardiology"}</td>
                      <td>{req.preferred_doctor_name || "Department Queue"}</td>
                      <td>
                        <span className="badge badge-med" style={{ textTransform: "capitalize" }}>
                          {req.status}
                        </span>
                      </td>
                      <td>{new Date(req.created_at).toLocaleDateString()}</td>
                      <td>
                        <div style={{ display: "flex", gap: 6 }}>
                          <button
                            type="button"
                            onClick={() => handleAcceptPatientRequest(req.id)}
                            disabled={loading}
                            style={{ fontSize: "0.75rem", padding: "4px 8px", backgroundColor: "#15803d", borderColor: "#15803d" }}
                          >
                            Accept into My Panel
                          </button>
                          <button
                            type="button"
                            className="btn-secondary"
                            onClick={() => handleOpenForwardModal(req)}
                            disabled={loading}
                            style={{ fontSize: "0.75rem", padding: "4px 8px" }}
                          >
                            Forward to Doctor
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
      )}

      {/* VIEW 3: MEDICINES & INVENTORY */}
      {mainView === "medicines" && (
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
            <h3 style={{ margin: 0 }}>My Clinical Medicine Inventory</h3>
            <button
              type="button"
              onClick={() => setShowMedRequestModal(true)}
            >
              Request Medicine from Admin
            </button>
          </div>

          <div className="card" style={{ marginBottom: 16 }}>
            <h4>Procured & Available Medicines ({procuredMeds.length})</h4>
            {procuredMeds.length === 0 ? (
              <p style={{ fontSize: "0.85rem", color: "#64748b" }}>
                No medicines procured yet. Click "Request Medicine from Admin" to submit procurement orders.
              </p>
            ) : (
              <div className="table-wrapper">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Medicine Name</th>
                      <th>Generic Name</th>
                      <th>Category</th>
                      <th>Available Stock</th>
                      <th>Procured Date</th>
                    </tr>
                  </thead>
                  <tbody>
                    {procuredMeds.map((med) => (
                      <tr key={med.id}>
                        <td><strong>{med.name}</strong></td>
                        <td>{med.generic_name || "-"}</td>
                        <td>{med.category || "General Medicine"}</td>
                        <td>
                          <span className="badge badge-low">
                            {med.quantity} {med.unit || "units"}
                          </span>
                        </td>
                        <td>{med.procured_at ? new Date(med.procured_at).toLocaleDateString() : "Active"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="card">
            <h4>Pending Procurement Requests to Admin ({requestedMeds.length})</h4>
            {requestedMeds.length === 0 ? (
              <p style={{ fontSize: "0.85rem", color: "#64748b" }}>No pending medicine requests.</p>
            ) : (
              <div className="table-wrapper">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Medicine Name</th>
                      <th>Generic Name</th>
                      <th>Requested Quantity</th>
                      <th>Status</th>
                      <th>Request Date</th>
                    </tr>
                  </thead>
                  <tbody>
                    {requestedMeds.map((med) => (
                      <tr key={med.id}>
                        <td><strong>{med.name}</strong></td>
                        <td>{med.generic_name || "-"}</td>
                        <td>{med.quantity} {med.unit || "units"}</td>
                        <td><span className="badge badge-med">Pending Admin Procurement</span></td>
                        <td>{new Date(med.requested_at).toLocaleDateString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* VIEW 4: CROSS-DOCTOR SHARED AREA */}
      {mainView === "shared_area" && (
        <div className="card collaborative-area">
          <div className="collaborative-heading">
            <div>
              <p className="section-eyebrow">Hospital care coordination</p>
              <h3>Cross-Doctor Collaborative Area</h3>
              <p className="section-description">Review shared clinical context, ownership, transfers, and the latest risk decision before opening a patient file.</p>
            </div>
            <button type="button" className="btn-secondary" onClick={loadSharedCases}>Refresh cases</button>
          </div>

          <div className="collaborative-stats" aria-label="Collaborative case summary">
            <div className="collaborative-stat"><span>Hospital patients</span><strong>{sharedCases.length}</strong></div>
            <div className="collaborative-stat"><span>Shared history</span><strong>{sharedHistoryCount}</strong></div>
            <div className="collaborative-stat"><span>My assigned cases</span><strong>{mySharedCaseCount}</strong></div>
            <div className="collaborative-stat collaborative-stat-alert"><span>High-risk cases</span><strong>{highRiskSharedCount}</strong></div>
          </div>

          <div className="collaborative-controls">
            <input aria-label="Search shared cases" value={sharedSearch} onChange={(event) => setSharedSearch(event.target.value)} placeholder="Search patient, doctor, specialty, or diagnosis" />
            <select aria-label="Filter shared cases by risk" value={sharedRiskFilter} onChange={(event) => setSharedRiskFilter(event.target.value)}>
              <option value="all">All risk levels</option>
              <option value="High Risk">High risk</option>
              <option value="Moderate Risk">Moderate risk</option>
              <option value="Low Risk">Low risk</option>
              <option value="Not Assessed">Not assessed</option>
            </select>
            <span>{filteredSharedCases.length} of {sharedCases.length} cases shown</span>
          </div>

          {filteredSharedCases.length === 0 ? (
            <div className="collaborative-empty">
              <strong>No cases match these filters.</strong>
              <span>Try clearing the search or selecting another risk level.</span>
            </div>
          ) : (
            <div className="table-wrapper">
              <table className="table collaborative-table">
              <thead>
                <tr>
                  <th>Patient Name</th>
                  <th>Care owner</th>
                  <th>Collaboration</th>
                  <th>Clinical snapshot</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredSharedCases.map((c) => (
                  <tr key={c.id}>
                    <td>
                      <strong>{c.name}</strong>
                      <div className="cell-muted">{c.age ? `${c.age} years` : "Age unavailable"} · {c.sex !== null ? (c.sex === 1 ? "Male" : "Female") : "Sex unavailable"}</div>
                      <div className="cell-muted">{c.email}</div>
                    </td>
                    <td>
                      <strong>Dr. {c.assigned_doctor_name}</strong>
                      <div className="cell-muted">{c.assigned_doctor_specialty || "General care"}</div>
                      {c.is_my_patient && <span className="badge badge-neutral">My patient</span>}
                    </td>
                    <td>
                      <span className={`badge ${c.has_shared_history ? "badge-med" : "badge-neutral"}`}>{c.has_shared_history ? "Shared history" : "Primary care"}</span>
                      <div className="cell-muted">{c.transfers_count} transfer{c.transfers_count === 1 ? "" : "s"}</div>
                    </td>
                    <td>
                      <span className={`badge ${riskBadgeClass(c.latest_risk_level)}`}>{c.latest_risk_level}</span>
                      {c.latest_risk_probability !== null && <div className="cell-muted">Risk score: {c.latest_risk_probability}%</div>}
                      <div className="clinical-title">{c.latest_diagnosis_title}</div>
                      {c.latest_diagnosis_by && <div className="cell-muted">By Dr. {c.latest_diagnosis_by}</div>}
                    </td>
                    <td>
                      <button
                        type="button"
                        className="btn-secondary"
                        style={{ fontSize: "0.75rem", padding: "3px 8px" }}
                        onClick={() => {
                          const found = patients.find((p) => p.id === c.id);
                          if (found) {
                            setSelectedPatient(found);
                          } else {
                            setSelectedPatient({
                              id: c.id,
                              name: c.name,
                              email: c.email,
                              age: c.age,
                              sex: c.sex,
                              is_demographics_locked: c.is_demographics_locked,
                            });
                          }
                          setCollaborativeFile(null);
                          loadCollaborativeFile(c.id);
                          setMainView("my_patients");
                          setActiveTab("collaborative");
                        }}
                      >
                        Open shared file
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* VIEW 5: SAVED DRAFTS */}
      {mainView === "drafts" && (
        <div className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <h3 style={{ margin: 0 }}>Saved Clinical Drafts</h3>
            <span style={{ fontSize: "0.8rem", color: "#64748b" }}>{drafts.length} draft{drafts.length !== 1 ? "s" : ""}</span>
          </div>

          {drafts.length === 0 ? (
            <p style={{ fontSize: "0.85rem", color: "#64748b" }}>No saved drafts.</p>
          ) : (
            <div className="table-wrapper">
              <table className="table">
                <thead>
                  <tr>
                    <th>Draft Name</th>
                    <th>Risk Estimate</th>
                    <th>Last Saved</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {drafts.map((d) => (
                    <tr key={d.id}>
                      <td><strong>{d.draft_name}</strong></td>
                      <td>{d.risk_level ? `${d.risk_level} (${(d.risk_probability * 100).toFixed(1)}%)` : "Not evaluated"}</td>
                      <td>{new Date(d.created_at).toLocaleString()}</td>
                      <td>
                        <div style={{ display: "flex", gap: 6 }}>
                          <button
                            type="button"
                            style={{ fontSize: "0.75rem", padding: "3px 8px" }}
                            onClick={() => handleResumeDraft(d)}
                          >
                            Resume
                          </button>
                          <button
                            type="button"
                            className="btn-danger"
                            style={{ fontSize: "0.75rem", padding: "3px 8px" }}
                            onClick={() => handleDeleteDraft(d.id)}
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
      )}

      {/* VIEW 6: EMERGENCY HOSPITAL DIRECTORY */}
      {mainView === "hospital_directory" && (
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
            <div>
              <h3 style={{ margin: "0 0 4px" }}>🏥 Emergency Hospital Directory</h3>
              <p style={{ margin: 0, fontSize: "0.85rem", color: "#64748b" }}>
                Find nearby hospitals with live resource availability sorted by distance.
              </p>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button
                type="button"
                onClick={() => {
                  if (navigator.geolocation) {
                    navigator.geolocation.getCurrentPosition(
                      (pos) => {
                        setUserLocation(pos.coords);
                        loadHospitalDirectory(pos.coords.latitude, pos.coords.longitude);
                      },
                      () => loadHospitalDirectory(19.076, 72.8777)
                    );
                  } else {
                    loadHospitalDirectory(19.076, 72.8777);
                  }
                }}
                disabled={hospitalLoading}
                style={{ backgroundColor: "#dc2626", borderColor: "#dc2626" }}
              >
                {hospitalLoading ? "Locating..." : "📍 Find Nearest"}
              </button>
              <button type="button" className="btn-secondary" onClick={() => loadHospitalDirectory()} disabled={hospitalLoading}>
                List All
              </button>
            </div>
          </div>

          {hospitalDirectory.length === 0 ? (
            <div className="card" style={{ textAlign: "center", padding: "32px 16px", color: "#64748b" }}>
              <div style={{ fontSize: "2rem", marginBottom: 8 }}>🏥</div>
              <p>Click "Find Nearest" to sort hospitals by your location, or "List All" to show all facilities.</p>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {hospitalDirectory.map((h) => (
                <div key={h.id} className="card" style={{ borderLeft: `4px solid ${h.emergency_services_available ? "#16a34a" : "#dc2626"}` }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                        <strong style={{ fontSize: "1rem" }}>{h.name}</strong>
                        <span className={`badge ${h.emergency_services_available ? "badge-low" : "badge-high"}`}>
                          {h.emergency_services_available ? "Emergency Open" : "Emergency Closed"}
                        </span>
                        {h.distance_km && <span className="badge badge-neutral">{h.distance_km} km away</span>}
                      </div>
                      <div style={{ fontSize: "0.82rem", color: "#475569" }}>📍 {h.address}</div>
                      <a href={`tel:${h.contact_number}`} style={{ fontSize: "0.82rem", color: "#0369a1", textDecoration: "none" }}>📞 {h.contact_number}</a>
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: 16, flexWrap: "wrap", fontSize: "0.82rem", marginBottom: 8 }}>
                    <span style={{ color: h.available_beds > 0 ? "#16a34a" : "#dc2626", fontWeight: 600 }}>🛏️ Beds: {h.available_beds}</span>
                    <span style={{ color: h.icu_beds_available > 0 ? "#16a34a" : "#dc2626", fontWeight: 600 }}>ICU: {h.icu_beds_available}</span>
                    <span style={{ color: h.ventilators_available > 0 ? "#16a34a" : "#dc2626", fontWeight: 600 }}>💨 Ventilators: {h.ventilators_available}</span>
                    <span style={{ color: h.blood_bank_available ? "#16a34a" : "#dc2626", fontWeight: 600 }}>🩸 Blood Bank: {h.blood_bank_available ? "Available" : "Unavailable"}</span>
                  </div>
                  {h.doctor_availability && h.doctor_availability.length > 0 && (
                    <div>
                      <div style={{ fontSize: "0.78rem", fontWeight: 600, color: "#475569", marginBottom: 4 }}>Available Specialists:</div>
                      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                        {h.doctor_availability.map((a) => (
                          <span key={a.id} className="badge badge-med" style={{ fontSize: "0.75rem" }}>
                            {a.specialization}: {a.available_doctors} Dr{a.available_doctors !== 1 ? "s" : ""}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* VIEW 7: MY PROFILE & QUALIFICATIONS */}
      {mainView === "my_profile" && (
        <div style={{ maxWidth: 700 }}>
          <div className="card" style={{ marginBottom: 16, backgroundColor: "#f0f9ff", borderLeft: "4px solid #0284c7" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 12 }}>
              <div style={{ width: 56, height: 56, borderRadius: "50%", backgroundColor: "#0284c7", display: "flex", alignItems: "center", justifyContent: "center", color: "white", fontWeight: 700, fontSize: "1.5rem" }}>
                {(doctorProfile?.name || auth?.name || "D").charAt(0)}
              </div>
              <div>
                <div style={{ fontWeight: 700, fontSize: "1.1rem", color: "#0c4a6e" }}>Dr. {doctorProfile?.name || auth?.name}</div>
                <div style={{ fontSize: "0.85rem", color: "#475569" }}>{doctorProfile?.specialization || "Physician"} · {doctorProfile?.email}</div>
                {doctorProfile?.degree && <div style={{ fontSize: "0.8rem", color: "#64748b" }}>{doctorProfile.degree}</div>}
              </div>
            </div>
            {doctorProfile?.certifications && (
              <div style={{ fontSize: "0.82rem", color: "#334155" }}>🏅 {doctorProfile.certifications}</div>
            )}
          </div>

          {/* Interactive Information Drawer for Doctor Profile */}
          <div className="card" style={{ marginBottom: 16, backgroundColor: "#0B111A", border: "1px solid #1E293B" }}>
            <InformationDrawer
              title="Doctor Profile Card & Clinical Drawer"
              description="Hover over your profile card to see the interaction effect, or tap to slide open your full medical credentials drawer."
              backgroundColor="#0D1520"
              textColor="#F8FAFC"
              sidebarWidth="50%"
              overlayOpacity={0.4}
              items={[
                {
                  id: "my-doc-profile",
                  role: "doctor",
                  name: doctorProfile?.name || auth?.name || "Cardiologist",
                  specialization: doctorProfile?.specialization || "Cardiology & Internal Medicine",
                  degree: doctorProfile?.degree || "MBBS, MD (Cardiology)",
                  years_of_experience: doctorProfile?.years_of_experience || 12,
                  license_number: doctorProfile?.license_number || "MCI-IND-89421",
                  certifications: doctorProfile?.certifications || "Fellow of the Cardiological Society of India (FCSI), ACLS Certified",
                  email: doctorProfile?.email || auth?.email,
                  phone_number: "+91 98765 43210",
                  image: "https://images.unsplash.com/photo-1559839734-2b71ea197ec2?auto=format&fit=crop&q=80&w=600",
                  description: "Senior consultant dedicated to explainable AI-driven cardiovascular risk stratification, patient-centric treatment planning, and multi-disciplinary clinical decision support.",
                  hospital: "Apex Super Speciality Hospital, India",
                },
              ]}
            />
          </div>


          <div className="card">
            <h3 style={{ marginTop: 0 }}>Edit Profile & Qualifications</h3>
            {profileSaveMsg && <div className="alert alert-success">{profileSaveMsg}</div>}
            <form
              className="form"
              onSubmit={async (e) => {
                e.preventDefault();
                setProfileSaveMsg("");
                try {
                  const payload = {
                    ...doctorProfileForm,
                    years_of_experience: doctorProfileForm.years_of_experience ? parseInt(doctorProfileForm.years_of_experience, 10) : null,
                  };
                  const updated = await apiRequest("/doctor/profile", { method: "PUT", body: JSON.stringify(payload) }, auth?.access_token);
                  setDoctorProfile(updated);
                  setProfileSaveMsg("Profile updated successfully.");
                  toast.success("Profile updated successfully.");
                } catch (err) {
                  setError(err.message);
                  toast.error(err.message);
                }
              }}
            >
              <div className="form-grid">
                <div className="form-group">
                  <label>Display Name</label>
                  <input type="text" value={doctorProfileForm.name} onChange={(e) => setDoctorProfileForm({ ...doctorProfileForm, name: e.target.value })} />
                </div>
                <div className="form-group">
                  <label>Specialization</label>
                  <input type="text" value={doctorProfileForm.specialization} onChange={(e) => setDoctorProfileForm({ ...doctorProfileForm, specialization: e.target.value })} />
                </div>
                <div className="form-group">
                  <label>License Number</label>
                  <input type="text" value={doctorProfileForm.license_number} onChange={(e) => setDoctorProfileForm({ ...doctorProfileForm, license_number: e.target.value })} />
                </div>
                <div className="form-group">
                  <label>Years of Experience</label>
                  <input type="number" min="0" max="70" value={doctorProfileForm.years_of_experience} onChange={(e) => setDoctorProfileForm({ ...doctorProfileForm, years_of_experience: e.target.value })} />
                </div>
              </div>
              <div className="form-group">
                <label>Degree(s)</label>
                <input type="text" placeholder="e.g. MBBS, MD (Cardiology), FACC" value={doctorProfileForm.degree} onChange={(e) => setDoctorProfileForm({ ...doctorProfileForm, degree: e.target.value })} />
              </div>
              <div className="form-group">
                <label>Certifications</label>
                <textarea rows={3} placeholder="e.g. Board Certified Cardiologist, ACLS Certified..." value={doctorProfileForm.certifications} onChange={(e) => setDoctorProfileForm({ ...doctorProfileForm, certifications: e.target.value })} />
              </div>
              <button type="submit" disabled={loading}>Save Profile</button>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 1: Patient Transfer */}
      {showTransferModal && selectedPatient && (
        <div className="modal-overlay">
          <div className="modal-card">
            <h3>Transfer Patient: {selectedPatient.name}</h3>
            <form className="form" onSubmit={handleTransferPatient}>
              <div className="form-group">
                <label>Select Target Doctor *</label>
                <select
                  value={transferTargetDocId}
                  onChange={(e) => setTransferTargetDocId(e.target.value)}
                  required
                >
                  <option value="">-- Choose Colleague Doctor --</option>
                  {allDoctors.map((doc) => (
                    <option key={doc.id} value={doc.id}>
                      Dr. {doc.name} ({doc.specialization || "Clinical Specialist"})
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label>Referral Reason & Handover Notes *</label>
                <textarea
                  rows={3}
                  placeholder="Reason for care transfer or subspecialty consultation..."
                  value={transferReason}
                  onChange={(e) => setTransferReason(e.target.value)}
                  required
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 10 }}>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setShowTransferModal(false)}
                >
                  Cancel
                </button>
                <button type="submit" disabled={loading}>
                  {loading ? "Transferring..." : "Confirm Patient Transfer"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 2: Forward Patient Request */}
      {showForwardModal && forwardTargetReq && (
        <div className="modal-overlay">
          <div className="modal-card">
            <h3>Forward Patient Request: {forwardTargetReq.patient_name}</h3>
            <form className="form" onSubmit={handleForwardPatientRequest}>
              <div className="form-group">
                <label>Forward To Colleague Doctor *</label>
                <select
                  value={forwardTargetDocId}
                  onChange={(e) => setForwardTargetDocId(e.target.value)}
                  required
                >
                  <option value="">-- Choose Target Doctor --</option>
                  {allDoctors.map((doc) => (
                    <option key={doc.id} value={doc.id}>
                      Dr. {doc.name} ({doc.specialization || "Specialist"})
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label>Forwarding / Triage Notes</label>
                <textarea
                  rows={3}
                  placeholder="Clinical triage rationale or department recommendation..."
                  value={forwardNotes}
                  onChange={(e) => setForwardNotes(e.target.value)}
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 10 }}>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setShowForwardModal(false)}
                >
                  Cancel
                </button>
                <button type="submit" disabled={loading}>
                  {loading ? "Forwarding..." : "Confirm Forward"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 3: Request Medicine from Admin */}
      {showMedRequestModal && (
        <div className="modal-overlay">
          <div className="modal-card">
            <h3>Request Medicine from Hospital Admin</h3>
            <form className="form" onSubmit={handleRequestMedicineSubmit}>
              <div className="form-group">
                <label>Medicine Brand / Trade Name *</label>
                <input
                  type="text"
                  placeholder="e.g. Metoprolol Succinate 50mg"
                  value={medRequestForm.name}
                  onChange={(e) => setMedRequestForm({ ...medRequestForm, name: e.target.value })}
                  required
                />
              </div>

              <div className="form-grid">
                <div className="form-group">
                  <label>Generic Name</label>
                  <input
                    type="text"
                    placeholder="e.g. Metoprolol"
                    value={medRequestForm.generic_name}
                    onChange={(e) => setMedRequestForm({ ...medRequestForm, generic_name: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label>Category</label>
                  <input
                    type="text"
                    placeholder="e.g. Beta-Blocker"
                    value={medRequestForm.category}
                    onChange={(e) => setMedRequestForm({ ...medRequestForm, category: e.target.value })}
                  />
                </div>
              </div>

              <div className="form-grid">
                <div className="form-group">
                  <label>Unit</label>
                  <input
                    type="text"
                    placeholder="e.g. tablets, vials"
                    value={medRequestForm.unit}
                    onChange={(e) => setMedRequestForm({ ...medRequestForm, unit: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label>Requested Quantity *</label>
                  <input
                    type="number"
                    min="1"
                    value={medRequestForm.quantity}
                    onChange={(e) => setMedRequestForm({ ...medRequestForm, quantity: parseInt(e.target.value, 10) || 1 })}
                    required
                  />
                </div>
              </div>

              <div className="form-group">
                <label>Procurement Clinical Justification</label>
                <textarea
                  rows={2}
                  placeholder="Clinical usage rationale for hospital administration..."
                  value={medRequestForm.notes}
                  onChange={(e) => setMedRequestForm({ ...medRequestForm, notes: e.target.value })}
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 10 }}>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setShowMedRequestModal(false)}
                >
                  Cancel
                </button>
                <button type="submit" disabled={loading}>
                  {loading ? "Submitting..." : "Submit Procurement Request"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 4: Convert Draft into Patient */}
      {showConvertModal && convertDraftTarget && (
        <div className="modal-overlay">
          <div className="modal-card">
            <h3>Convert Guest Draft into Registered Patient</h3>
            <form className="form" onSubmit={handleConvertDraftSubmit}>
              <div className="form-group">
                <label>Patient Full Name *</label>
                <input
                  type="text"
                  value={convertForm.patient_name}
                  onChange={(e) => setConvertForm({ ...convertForm, patient_name: e.target.value })}
                  required
                />
              </div>

              <div className="form-group">
                <label>Patient Email *</label>
                <input
                  type="email"
                  placeholder="patient@hospital.com"
                  value={convertForm.patient_email}
                  onChange={(e) => setConvertForm({ ...convertForm, patient_email: e.target.value })}
                  required
                />
              </div>

              <div className="form-group">
                <label>Password *</label>
                <PasswordToggle
                  value={convertForm.password}
                  onChange={(e) => setConvertForm({ ...convertForm, password: e.target.value })}
                  placeholder="Set a password"
                  required
                />
              </div>

              <div className="form-grid">
                <div className="form-group">
                  <label>Phone Number</label>
                  <input
                    type="text"
                    value={convertForm.phone_number}
                    onChange={(e) => setConvertForm({ ...convertForm, phone_number: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label>Emergency Contact</label>
                  <input
                    type="text"
                    value={convertForm.emergency_contact_name}
                    onChange={(e) => setConvertForm({ ...convertForm, emergency_contact_name: e.target.value })}
                  />
                </div>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 10 }}>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setShowConvertModal(false)}
                >
                  Cancel
                </button>
                <button type="submit" disabled={loading}>
                  {loading ? "Converting..." : "Convert & Create Account"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 5: Register New Patient Directly */}
      {showAddPatientModal && (
        <div className="modal-overlay">
          <div className="modal-card" style={{ maxWidth: 520 }}>
            <h3>Register Patient (Assigned to You)</h3>
            <form className="form" onSubmit={handleCreatePatient}>
              <div className="form-grid">
                <div className="form-group">
                  <label>Patient Full Name *</label>
                  <input
                    type="text"
                    placeholder="Full Name"
                    value={newPatientForm.name}
                    onChange={(e) => setNewPatientForm({ ...newPatientForm, name: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Email Address *</label>
                  <input
                    type="email"
                    placeholder="patient@hospital.com"
                    value={newPatientForm.email}
                    onChange={(e) => setNewPatientForm({ ...newPatientForm, email: e.target.value })}
                    required
                  />
                </div>
              </div>

              {/* Demographics */}
              <div style={{ backgroundColor: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 8, padding: 12, marginBottom: 10 }}>
                <div style={{ fontWeight: 600, fontSize: "0.85rem", marginBottom: 8, color: "#1e293b" }}>🎂 Demographics</div>
                <div className="form-grid">
                  <div className="form-group">
                    <label style={{ display: "flex", justifyContent: "space-between" }}>
                      <span>Date of Birth</span>
                      {calcAgeFromDob(newPatientForm.date_of_birth) !== null && (
                        <span style={{ fontSize: "0.75rem", background: "#e0f2fe", color: "#0369a1", padding: "1px 6px", borderRadius: 12 }}>
                          Age: {calcAgeFromDob(newPatientForm.date_of_birth)} yrs
                        </span>
                      )}
                    </label>
                    <input
                      type="date"
                      value={newPatientForm.date_of_birth}
                      onChange={(e) => setNewPatientForm({ ...newPatientForm, date_of_birth: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label>Biological Sex</label>
                    <select
                      value={newPatientForm.sex}
                      onChange={(e) => setNewPatientForm({ ...newPatientForm, sex: e.target.value })}
                    >
                      <option value="1">Male</option>
                      <option value="0">Female</option>
                    </select>
                  </div>
                </div>
                {!newPatientForm.date_of_birth && (
                  <div className="form-group" style={{ marginBottom: 0 }}>
                    <label>Age (years) — if DOB not available</label>
                    <input
                      type="number"
                      placeholder="e.g. 45"
                      value={newPatientForm.age}
                      onChange={(e) => setNewPatientForm({ ...newPatientForm, age: e.target.value })}
                    />
                  </div>
                )}
              </div>

              {/* Contact Info */}
              <div className="form-grid">
                <div className="form-group">
                  <label>Phone Number</label>
                  <input
                    type="tel"
                    placeholder="+91 9876543210"
                    value={newPatientForm.phone_number}
                    onChange={(e) => setNewPatientForm({ ...newPatientForm, phone_number: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label>Address</label>
                  <input
                    type="text"
                    placeholder="City / Area"
                    value={newPatientForm.address}
                    onChange={(e) => setNewPatientForm({ ...newPatientForm, address: e.target.value })}
                  />
                </div>
              </div>

              <div className="form-grid">
                <div className="form-group">
                  <label>Emergency Contact Name</label>
                  <input
                    type="text"
                    placeholder="Contact Person"
                    value={newPatientForm.emergency_contact_name}
                    onChange={(e) => setNewPatientForm({ ...newPatientForm, emergency_contact_name: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label>Emergency Contact Phone</label>
                  <input
                    type="tel"
                    placeholder="Emergency Phone"
                    value={newPatientForm.emergency_contact_phone}
                    onChange={(e) => setNewPatientForm({ ...newPatientForm, emergency_contact_phone: e.target.value })}
                  />
                </div>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 10 }}>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setShowAddPatientModal(false)}
                >
                  Cancel
                </button>
                <button type="submit" disabled={loading}>
                  {loading ? "Registering..." : "Register & Assign Patient"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
      </>
      )}

      {/* 10-Section Structured Clinical Report Modal */}
      <PatientReportModal
        isOpen={reportModalOpen}
        onClose={() => setReportModalOpen(false)}
        reportData={reportData}
        loading={reportLoading}
        downloadPdfEndpoint={reportPdfEndpoint}
        patientName={reportPatientName}
        token={auth?.access_token}
      />
    </div>
  );
}
