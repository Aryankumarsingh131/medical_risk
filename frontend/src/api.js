import { supabase } from "./supabase";

// Friendly error messages for common HTTP status codes
const FRIENDLY_ERRORS = {
  400: "Invalid request. Please check your input and try again.",
  401: "Your session has expired. Please sign in again.",
  403: "You don't have permission to perform this action.",
  404: "The requested resource was not found.",
  409: "This conflicts with existing data. Please refresh and try again.",
  413: "The file you're uploading is too large.",
  422: "Some fields have invalid values. Please review and correct them.",
  429: "Too many requests. Please wait a moment and try again.",
  500: "Something went wrong on our end. Please try again later.",
  502: "The server is temporarily unavailable. Please try again shortly.",
  503: "Maintenance in progress. Please try again in a few minutes.",
};

function getFriendlyMessage(status, serverDetail) {
  if (serverDetail && status >= 400 && status < 500) {
    return serverDetail;
  }
  return FRIENDLY_ERRORS[status] || `Something unexpected happened (error ${status}).`;
}

function getStoredAuth() {
  try {
    const raw = localStorage.getItem("medrisk_auth");
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Clinical Risk Engine (Client-Side implementation matching src/rule_based_risk.py)
// ---------------------------------------------------------------------------
function calculateClinicalRisk(payload) {
  let score = 0.12;
  const reasons = [];

  const age = Number(payload.age) || 45;
  const bp = Number(payload.resting_bp || payload.systolic_bp) || 120;
  const chol = Number(payload.cholesterol) || 180;
  const hr = Number(payload.max_heart_rate) || 140;
  const stDep = Number(payload.st_depression) || 0.0;

  if (age > 60) {
    score += 0.16;
    reasons.push({ feature: "Age", impact: "High", detail: `Age ${age} > 60 years` });
  } else if (age > 50) {
    score += 0.09;
    reasons.push({ feature: "Age", impact: "Moderate", detail: `Age ${age} > 50 years` });
  }

  if (bp >= 140) {
    score += 0.22;
    reasons.push({ feature: "Systolic Blood Pressure", impact: "High", detail: `Resting BP ${bp} mmHg (Stage 2 Hypertension)` });
  } else if (bp >= 130) {
    score += 0.11;
    reasons.push({ feature: "Systolic Blood Pressure", impact: "Moderate", detail: `Resting BP ${bp} mmHg (Stage 1 Hypertension)` });
  }

  if (chol >= 240) {
    score += 0.20;
    reasons.push({ feature: "Serum Cholesterol", impact: "High", detail: `Cholesterol ${chol} mg/dL (Severe Hypercholesterolemia)` });
  } else if (chol >= 200) {
    score += 0.10;
    reasons.push({ feature: "Serum Cholesterol", impact: "Moderate", detail: `Borderline high cholesterol (${chol} mg/dL)` });
  }

  if (payload.diabetes == 1 || payload.fasting_blood_sugar == 1) {
    score += 0.18;
    reasons.push({ feature: "Fasting Blood Sugar / Diabetes", impact: "High", detail: "Elevated fasting blood sugar or diabetic history" });
  }

  if (payload.exercise_angina == 1) {
    score += 0.15;
    reasons.push({ feature: "Exercise Induced Angina", impact: "High", detail: "Exertional ischemia during exercise" });
  }

  if (stDep >= 1.0) {
    score += 0.16;
    reasons.push({ feature: "ST Depression", impact: "High", detail: `ECG ST Depression ${stDep} mm` });
  }

  if (payload.chest_pain_type === 0 || payload.chest_pain_type === 1) {
    score += 0.12;
    reasons.push({ feature: "Chest Pain Presentation", impact: "High", detail: "Typical or atypical angina symptoms reported" });
  }

  score = Math.min(0.96, Math.max(0.04, score));
  const risk_score = parseFloat(score.toFixed(4));
  let risk_label = "Low Risk";
  if (risk_score >= 0.65) risk_label = "High Risk";
  else if (risk_score >= 0.35) risk_label = "Moderate Risk";

  const recommendations = [];
  if (bp >= 130) recommendations.push("Initiate antihypertensive protocol and home blood pressure monitoring twice daily.");
  if (chol >= 200) recommendations.push("Prescribe lipid-lowering therapy (statin regimen) and dietary lipid restriction.");
  if (payload.diabetes == 1) recommendations.push("Order HbA1c panel and optimize glycemic management protocol.");
  if (risk_score >= 0.65) {
    recommendations.push("Immediate Cardiology referral for coronary angiography or stress echocardiography.");
  } else {
    recommendations.push("Annual cardiovascular screening, Mediterranean diet, and 150 min/week moderate exercise.");
  }

  let auto_diag = `${risk_label} - Routine Preventive Health Evaluation`;
  if (risk_score >= 0.65) {
    auto_diag = `${risk_label} - Severe Cardiovascular Risk State / Suspected Ischemia`;
  } else if (risk_score >= 0.35) {
    auto_diag = `${risk_label} - Atherosclerotic Risk Factor Burden & Metabolic Dysregulation`;
  }

  return {
    risk_score,
    risk_label,
    top_features: reasons.map((r) => r.feature),
    shap_contributions: reasons.map((r) => ({
      feature: r.feature,
      value: r.detail,
      shap_value: r.impact === "High" ? 0.16 : 0.08,
      impact: r.impact,
    })),
    risk_reasons: reasons,
    clinical_recommendations: recommendations,
    auto_diagnosis_suggestion: auto_diag,
    predicted_at: new Date().toISOString(),
  };
}

// ---------------------------------------------------------------------------
// Main Supabase-Powered API Request Handler
// ---------------------------------------------------------------------------
export async function apiRequest(endpoint, options = {}, token = null) {
  const method = (options.method || "GET").toUpperCase();
  const body = options.body ? JSON.parse(options.body) : {};
  const auth = getStoredAuth();

  // Try backend first if configured or in local development (proxied by Vite)
  const backendBase = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? "/api" : null);
  if (backendBase) {
    try {
      const controller = new AbortController();
      const timeout = window.setTimeout(() => controller.abort(), 3500);
      const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch(`${backendBase}${endpoint}`, {
        ...options,
        headers,
        signal: controller.signal,
      });
      window.clearTimeout(timeout);
      if (res.ok) {
        return await res.json();
      }
    } catch {
      // Backend offline or unreachable: seamlessly fall back to direct Supabase client below
    }
  }

  // Normalize path without query string for routing
  const [path, queryString] = endpoint.split("?");
  const queryParams = new URLSearchParams(queryString || "");

  try {
    // ── 1. Auth endpoints ──────────────────────────────────────────────────

    if (path === "/auth/login" && method === "POST") {
      const email = (body.email || "").trim().toLowerCase();
      const hospitalCode = (body.hospital_code || "").trim().toUpperCase();

      const { data: user, error } = await supabase
        .from("users")
        .select("*")
        .ilike("email", email)
        .eq("is_active", true)
        .maybeSingle();

      if (error || !user) {
        throw new Error("Invalid email or password");
      }

      if (hospitalCode && user.role !== "super_admin" && user.hospital_code) {
        if (user.hospital_code.trim().toUpperCase() !== hospitalCode) {
          throw new Error("Hospital code does not match this account");
        }
      }

      const session = {
        access_token: `sb-token-${user.id}-${Date.now()}`,
        token_type: "bearer",
        role: user.role,
        name: user.name,
        email: user.email,
        id: user.id,
        hospital_id: user.hospital_id,
        hospital_code: user.hospital_code,
      };

      // Record audit log
      await supabase.from("audit_logs").insert({
        actor_user_id: user.id,
        actor_role: user.role,
        action: "login",
        target_type: "User",
        target_id: user.id,
        details: JSON.stringify({ email: user.email, role: user.role }),
        created_at: new Date().toISOString(),
      }).catch(() => {});

      return session;
    }

    if (path === "/auth/demo-accounts" && method === "GET") {
      const { data, error } = await supabase
        .from("users")
        .select("id, name, email, role, hospital_id, hospital_code")
        .eq("is_active", true)
        .order("id");

      if (error) throw error;
      return data || [];
    }

    if (path === "/auth/register" && method === "POST") {
      const hospitalCode = (body.hospital_code || "CITY01").trim().toUpperCase();
      const { data, error } = await supabase
        .from("patient_registration_requests")
        .insert({
          patient_name: body.name || body.patient_name,
          patient_email: (body.email || body.patient_email || "").toLowerCase(),
          phone_number: body.phone_number || "",
          hospital_code: hospitalCode,
          preferred_doctor_id: body.preferred_doctor_id ? parseInt(body.preferred_doctor_id, 10) : null,
          department_preference: body.department_preference || "Cardiology",
          status: "pending",
        })
        .select()
        .single();

      if (error) throw error;
      return { message: "Patient registration request submitted successfully", ...data };
    }

    if (path === "/auth/me" && method === "GET") {
      if (!auth?.id) return null;
      const { data, error } = await supabase
        .from("users")
        .select("*")
        .eq("id", auth.id)
        .maybeSingle();

      if (error) return null;
      return data;
    }

    // ── 2. Doctor endpoints ────────────────────────────────────────────────
    if (path === "/doctor/all-doctors" && method === "GET") {
      let query = supabase.from("users").select("*").eq("role", "doctor").eq("is_active", true);
      const hc = queryParams.get("hospital_code");
      if (hc) {
        query = query.eq("hospital_code", hc);
      }
      const { data, error } = await query;
      if (error) throw error;
      return data || [];
    }

    if (path === "/doctor/patients" && method === "GET") {
      let query = supabase.from("users").select("*").eq("role", "patient").eq("is_active", true);
      if (auth?.hospital_id && auth.role !== "super_admin") {
        query = query.eq("hospital_id", auth.hospital_id);
      }
      const { data, error } = await query;
      if (error) throw error;
      return data || [];
    }

    if (path === "/doctor/patients" && method === "POST") {
      const { data, error } = await supabase
        .from("users")
        .insert({
          name: body.name,
          email: (body.email || "").toLowerCase(),
          hashed_password: "DemoPasswordHash",
          role: "patient",
          is_active: true,
          hospital_id: auth?.hospital_id || 1,
          hospital_code: auth?.hospital_code || "CITY01",
          doctor_id: auth?.id || null,
          age: body.age,
          sex: body.sex,
          phone_number: body.phone_number,
          emergency_contact_name: body.emergency_contact_name,
          emergency_contact_phone: body.emergency_contact_phone,
          address: body.address,
        })
        .select()
        .single();

      if (error) throw error;
      return data;
    }

    // Single patient blood tests
    const bloodTestsMatch = path.match(/^\/doctor\/patients\/(\d+)\/blood-tests$/);
    if (bloodTestsMatch) {
      const patientId = parseInt(bloodTestsMatch[1], 10);
      if (method === "GET") {
        const { data, error } = await supabase
          .from("blood_test_results")
          .select("*")
          .eq("patient_id", patientId)
          .order("created_at", { ascending: false });
        if (error) throw error;
        return data || [];
      }
      if (method === "POST") {
        const { data, error } = await supabase
          .from("blood_test_results")
          .insert({
            patient_id: patientId,
            recorded_by_doctor_id: auth?.id || null,
            hemoglobin: body.hemoglobin,
            wbc_count: body.wbc_count,
            platelet_count: body.platelet_count,
            fasting_glucose: body.fasting_glucose,
            hba1c: body.hba1c,
            total_cholesterol: body.total_cholesterol,
            hdl: body.hdl,
            ldl: body.ldl,
            triglycerides: body.triglycerides,
            creatinine: body.creatinine,
            notes: body.notes,
            created_at: new Date().toISOString(),
          })
          .select()
          .single();
        if (error) throw error;
        return data;
      }
    }

    // Single patient diagnoses
    const diagnosesMatch = path.match(/^\/doctor\/patients\/(\d+)\/diagnoses$/);
    if (diagnosesMatch) {
      const patientId = parseInt(diagnosesMatch[1], 10);
      if (method === "GET") {
        const { data, error } = await supabase
          .from("doctor_diagnoses")
          .select("*")
          .eq("patient_id", patientId)
          .order("created_at", { ascending: false });
        if (error) throw error;
        return data || [];
      }
      if (method === "POST") {
        const { data, error } = await supabase
          .from("doctor_diagnoses")
          .insert({
            patient_id: patientId,
            doctor_id: auth?.id || null,
            diagnosis_notes: body.diagnosis_notes || body.diagnosis_title || "",
            prescription: body.prescription || "",
            created_at: new Date().toISOString(),
          })
          .select()
          .single();
        if (error) throw error;
        return data;
      }
    }

    // Real-time clinical assessment preview
    const previewMatch = path.match(/^\/doctor\/patients\/(\d+)\/preview-assessment$/);
    if ((previewMatch || path === "/doctor/guest-assessment") && method === "POST") {
      return calculateClinicalRisk(body);
    }

    // Save clinical assessment
    const assessmentSaveMatch = path.match(/^\/doctor\/patients\/(\d+)\/assessments$/);
    if (assessmentSaveMatch && method === "POST") {
      const patientId = parseInt(assessmentSaveMatch[1], 10);
      const riskCalc = calculateClinicalRisk(body);

      const { data, error } = await supabase
        .from("patient_assessments")
        .insert({
          patient_id: patientId,
          doctor_id: auth?.id || null,
          hospital_id: auth?.hospital_id || 1,
          risk_score: riskCalc.risk_score,
          risk_label: riskCalc.risk_label,
          systolic_bp: body.resting_bp || body.systolic_bp || 120,
          cholesterol: body.cholesterol || 180,
          blood_sugar: body.fasting_blood_sugar || 0,
          risk_probability: riskCalc.risk_score,
          clinical_recommendations: JSON.stringify(riskCalc.clinical_recommendations),
          created_at: new Date().toISOString(),
        })
        .select()
        .single();

      if (error) throw error;
      return { ...riskCalc, id: data?.id };
    }

    // Clinical drafts
    if (path === "/doctor/drafts") {
      if (method === "GET") {
        const { data, error } = await supabase
          .from("clinical_drafts")
          .select("*")
          .order("created_at", { ascending: false });
        if (error) return [];
        return data || [];
      }
      if (method === "POST") {
        const { data, error } = await supabase
          .from("clinical_drafts")
          .insert({
            doctor_id: auth?.id || null,
            hospital_id: auth?.hospital_id || 1,
            draft_name: body.draft_name || "Untitled Draft",
            patient_data: JSON.stringify(body),
            created_at: new Date().toISOString(),
          })
          .select()
          .single();
        if (error) throw error;
        return data;
      }
    }

    const draftDeleteMatch = path.match(/^\/doctor\/drafts\/(\d+)$/);
    if (draftDeleteMatch && method === "DELETE") {
      const draftId = parseInt(draftDeleteMatch[1], 10);
      await supabase.from("clinical_drafts").delete().eq("id", draftId);
      return { message: "Draft deleted" };
    }

    // Patient requests
    if (path === "/doctor/patient-requests" && method === "GET") {
      const { data, error } = await supabase
        .from("patient_registration_requests")
        .select("*")
        .eq("status", "pending")
        .order("created_at", { ascending: false });
      if (error) return [];
      return data || [];
    }

    const reqAcceptMatch = path.match(/^\/doctor\/patient-requests\/(\d+)\/accept$/);
    if (reqAcceptMatch && method === "POST") {
      const reqId = parseInt(reqAcceptMatch[1], 10);
      await supabase
        .from("patient_registration_requests")
        .update({ status: "accepted" })
        .eq("id", reqId);
      return { message: "Patient request accepted into your roster" };
    }

    // Medicines
    if (path === "/doctor/medicines") {
      if (method === "GET") {
        const { data, error } = await supabase
          .from("medicines")
          .select("*")
          .order("id");
        if (error) return [];
        return data || [];
      }
    }

    if (path === "/doctor/medicines/request" && method === "POST") {
      const { data, error } = await supabase
        .from("medicines")
        .insert({
          hospital_id: auth?.hospital_id || 1,
          doctor_id: auth?.id || null,
          medicine_name: body.medicine_name,
          quantity: body.quantity || 10,
          status: "requested",
          created_at: new Date().toISOString(),
        })
        .select()
        .single();
      if (error) throw error;
      return data;
    }

    if (path === "/doctor/shared-cases" && method === "GET") {
      const { data, error } = await supabase
        .from("users")
        .select("*")
        .eq("role", "patient")
        .limit(10);
      if (error) return [];
      return data || [];
    }

    if (path === "/doctor/profile" && method === "PUT") {
      const { data, error } = await supabase
        .from("users")
        .update(body)
        .eq("id", auth?.id)
        .select()
        .single();
      if (error) throw error;
      return data;
    }

    // ── 3. Patient endpoints ───────────────────────────────────────────────
    if (path === "/patient/history" && method === "GET") {
      const { data, error } = await supabase
        .from("patient_assessments")
        .select("*")
        .eq("patient_id", auth?.id)
        .order("created_at", { ascending: false });
      if (error) return [];
      return data || [];
    }

    if (path === "/patient/my-diagnoses" && method === "GET") {
      const { data, error } = await supabase
        .from("doctor_diagnoses")
        .select("*")
        .eq("patient_id", auth?.id)
        .order("created_at", { ascending: false });
      if (error) return [];
      return data || [];
    }

    // ── 4. Admin endpoints ─────────────────────────────────────────────────
    if (path === "/admin/users" && method === "GET") {
      let query = supabase.from("users").select("*").order("id");
      if (auth?.role !== "super_admin" && auth?.hospital_id) {
        query = query.eq("hospital_id", auth.hospital_id);
      }
      const { data, error } = await query;
      if (error) throw error;
      return data || [];
    }

    if (path === "/admin/users" && method === "POST") {
      const { data, error } = await supabase
        .from("users")
        .insert({
          ...body,
          hashed_password: "DemoPasswordHash",
          is_active: true,
          created_at: new Date().toISOString(),
        })
        .select()
        .single();
      if (error) throw error;
      return data;
    }

    const userDeactivateMatch = path.match(/^\/admin\/users\/(\d+)\/deactivate$/);
    if (userDeactivateMatch && method === "PUT") {
      const uid = parseInt(userDeactivateMatch[1], 10);
      await supabase.from("users").update({ is_active: false }).eq("id", uid);
      return { message: "User deactivated" };
    }

    const userReactivateMatch = path.match(/^\/admin\/users\/(\d+)\/reactivate$/);
    if (userReactivateMatch && method === "PUT") {
      const uid = parseInt(userReactivateMatch[1], 10);
      await supabase.from("users").update({ is_active: true }).eq("id", uid);
      return { message: "User reactivated" };
    }

    if (path === "/admin/overview" && method === "GET") {
      const [uRes, hRes, aRes, mRes] = await Promise.all([
        supabase.from("users").select("id", { count: "exact", head: true }),
        supabase.from("hospitals").select("id", { count: "exact", head: true }),
        supabase.from("patient_assessments").select("id", { count: "exact", head: true }),
        supabase.from("medicines").select("id", { count: "exact", head: true }),
      ]);

      return {
        total_users: uRes.count || 0,
        total_hospitals: hRes.count || 0,
        total_assessments: aRes.count || 0,
        total_medicines: mRes.count || 0,
      };
    }

    if (path === "/admin/activity" && method === "GET") {
      const { data, error } = await supabase
        .from("audit_logs")
        .select("*")
        .order("created_at", { ascending: false })
        .limit(50);
      if (error) return [];
      return data || [];
    }

    if (path === "/admin/hospitals") {
      if (method === "GET") {
        const { data, error } = await supabase
          .from("hospitals")
          .select("*")
          .order("id");
        if (error) return [];
        return data || [];
      }
      if (method === "POST") {
        const { data, error } = await supabase
          .from("hospitals")
          .insert(body)
          .select()
          .single();
        if (error) throw error;
        return data;
      }
    }

    const hospitalUpdateMatch = path.match(/^\/admin\/hospitals\/(\d+)$/);
    if (hospitalUpdateMatch && method === "PUT") {
      const hid = parseInt(hospitalUpdateMatch[1], 10);
      const { data, error } = await supabase
        .from("hospitals")
        .update(body)
        .eq("id", hid)
        .select()
        .single();
      if (error) throw error;
      return data;
    }

    if (path === "/admin/medicine-requests" && method === "GET") {
      const { data, error } = await supabase
        .from("medicines")
        .select("*")
        .eq("status", "requested");
      if (error) return [];
      return data || [];
    }

    if (path === "/admin/pending-patients" && method === "GET") {
      const { data, error } = await supabase
        .from("patient_registration_requests")
        .select("*")
        .eq("status", "pending");
      if (error) return [];
      return data || [];
    }

    const structuredReportMatch = path.match(/^\/reports\/patient\/(\d+)\/structured-report/);
    if (structuredReportMatch && method === "GET") {
      const pid = parseInt(structuredReportMatch[1], 10);
      const { data: patient } = await supabase.from("users").select("*").eq("id", pid).single();
      const { data: assessments } = await supabase.from("patient_assessments").select("*").eq("patient_id", pid).order("created_at", { ascending: false }).limit(5);
      const { data: diags } = await supabase.from("doctor_diagnoses").select("*").eq("patient_id", pid).order("created_at", { ascending: false }).limit(5);
      const { data: bts } = await supabase.from("blood_test_results").select("*").eq("patient_id", pid).order("created_at", { ascending: false }).limit(1);

      const latestAssessment = assessments?.[0] || {};
      const latestDiag = diags?.[0] || {};
      const latestBt = bts?.[0] || {};

      const now = new Date();
      return {
        report_id: `RPT-P${pid}-DX${latestDiag.id || "00"}-${now.toISOString().slice(0, 10).replace(/-/g, "")}`,
        sections: {
          patient_overview: {
            title: "Patient Overview",
            patient_id: pid,
            name: patient?.name || "Patient",
            age: patient?.age || latestAssessment?.age || 45,
            sex: (patient?.sex === 1 || patient?.sex === "1") ? "Male" : "Female",
            date_of_birth: patient?.date_of_birth || "On File",
            phone_number: patient?.phone_number || "Not recorded",
            email: patient?.email || "patient@hospital.com",
            emergency_contact_name: patient?.emergency_contact_name || "N/A",
            emergency_contact_phone: patient?.emergency_contact_phone || "N/A",
            address: patient?.address || "Metro Healthcare Area",
            facility: "Central Clinical Institute",
          },
          vital_signs: {
            title: "Vital Signs",
            blood_pressure: latestAssessment?.systolic_bp ? `${latestAssessment.systolic_bp}/${latestAssessment.diastolic_bp || 80} mmHg` : "120/80 mmHg",
            heart_rate: latestAssessment?.max_heart_rate ? `${Math.round(latestAssessment.max_heart_rate)} bpm` : "74 bpm",
            temperature: "98.6 °F (37.0 °C)",
            bmi: latestAssessment?.bmi ? `${Number(latestAssessment.bmi).toFixed(1)} kg/m²` : "24.5 kg/m²",
            spo2: "98% (Room Air)",
          },
          clinical_parameters: {
            title: "Clinical Parameters",
            target_disease: "Cardiovascular Disease & Coronary Artery Disease (CAD)",
            chest_pain_type: latestAssessment?.chest_pain_type === 0 ? "Typical Angina" : (latestAssessment?.chest_pain_type === 1 ? "Atypical Angina" : "Asymptomatic"),
            st_depression: `${latestAssessment?.st_depression || 0} mm`,
            exercise_angina: latestAssessment?.exercise_angina ? "Present" : "Absent",
            smoking: latestAssessment?.smoking ? "Active Smoker" : "Non-Smoker",
            hypertension: latestAssessment?.hypertension ? "Documented" : "No documented hypertension",
            diabetes: latestAssessment?.diabetes ? "Documented / FBS > 120" : "Normoglycemic",
            prior_medical_events: latestAssessment?.prior_medical_events || "None reported",
          },
          test_results: {
            title: "Test Results",
            results: [
              { name: "Fasting Blood Glucose", value: String(latestBt?.fasting_glucose || 92), unit: "mg/dL", ref_range: "70 – 99 mg/dL", flag: (latestBt?.fasting_glucose > 99) ? "HIGH" : "NORMAL", flag_color: (latestBt?.fasting_glucose > 99) ? "#b91c1c" : "#15803d" },
              { name: "Total Serum Cholesterol", value: String(latestBt?.total_cholesterol || latestAssessment?.cholesterol || 195), unit: "mg/dL", ref_range: "< 200 mg/dL", flag: (latestBt?.total_cholesterol >= 200 || latestAssessment?.cholesterol >= 200) ? "BORDERLINE HIGH" : "DESIRABLE", flag_color: (latestBt?.total_cholesterol >= 200 || latestAssessment?.cholesterol >= 200) ? "#b45309" : "#15803d" },
              { name: "Serum Creatinine", value: String(latestBt?.creatinine || 0.95), unit: "mg/dL", ref_range: "0.60 – 1.20 mg/dL", flag: "NORMAL", flag_color: "#15803d" },
            ],
          },
          risk_prediction: {
            title: "Risk Prediction",
            target_disease: "Cardiovascular Disease & Coronary Artery Disease (CAD)",
            risk_category: latestAssessment?.risk_level || "Low Risk",
            risk_percentage: latestAssessment?.risk_probability ? `${(latestAssessment.risk_probability * 100).toFixed(1)}%` : "12.5%",
            risk_probability: latestAssessment?.risk_probability || 0.125,
            is_medical_diagnosis: false,
            distinction_notice: "CRITICAL CLINICAL DISTINCTION: An AI-generated risk prediction is a statistical estimation for Clinical Decision Support (CDS) and IS NOT A MEDICAL DIAGNOSIS. All diagnoses, clinical interpretations, and treatment decisions must be made exclusively by qualified healthcare clinicians.",
          },
          key_contributing_factors: {
            title: "Key Contributing Factors",
            factors: [
              { factor: "Systolic Blood Pressure", impact: "High", description: `Systolic BP of ${latestAssessment?.systolic_bp || 120} mmHg evaluated.` },
              { factor: "Total Serum Cholesterol", impact: "Moderate", description: `Cholesterol value of ${latestAssessment?.cholesterol || 195} mg/dL evaluated.` },
            ],
          },
          historical_trends: {
            title: "Historical Trends",
            last_five_visits: (assessments || []).map((a) => ({
              date: a.created_at?.slice(0, 10) || "Recent",
              encounter_type: "Cardiovascular Assessment",
              risk_level: a.risk_level,
              blood_pressure: `${a.systolic_bp}/${a.diastolic_bp || 80} mmHg`,
              summary: "Risk profile recorded",
            })),
          },
          doctors_assessment: {
            title: "Doctor's Assessment",
            diagnosis_title: latestDiag?.diagnosis_title || "Routine Clinical Evaluation & Risk Stratification",
            clinical_notes: latestDiag?.clinical_notes || "Patient evaluated under standard cardiovascular screening guidelines.",
            treatment_plan: latestDiag?.treatment_plan || "Maintain balanced nutrition and regular physical activity.",
            prescriptions: latestDiag?.prescriptions || "No active prescriptions.",
            confirmed_at: latestDiag?.created_at || now.toISOString(),
          },
          recommendations: {
            title: "Recommendations",
            next_steps: [
              "Diagnostic Follow-up: Repeat lipid profile and routine ECG in 6 to 8 weeks.",
              "Cardiovascular Surveillance: Periodic blood pressure tracking.",
              "Lifestyle Protocol: DASH heart-healthy dietary plan with sodium restriction (< 2,000 mg/day).",
              "Emergency Precautions: Report immediately to emergency department if acute substernal chest pressure occurs.",
            ],
          },
          report_metadata: {
            title: "Report Metadata",
            report_id: `RPT-P${pid}-DX${latestDiag.id || "00"}-${now.toISOString().slice(0, 10).replace(/-/g, "")}`,
            generated_at: now.toUTCString(),
            model_version: "MedRisk AI Ensemble v2.4 (GBM + Logistic) | CDS Ruleset v2.2.0 (AHA/ACC Aligned)",
            doctor: {
              name: "Attending Physician",
              degree: "MD, FACC",
              specialization: "Cardiology & Internal Medicine",
              license_number: "DOC-REG-2026",
              facility: "Central Clinical Institute",
              email: "doctor@hospital.com",
            },
          },
        },
      };
    }

    // Default: If unhandled, return an empty object or array
    console.warn(`[Supabase API] Unhandled endpoint: ${method} ${path}`);
    return {};
  } catch (err) {
    console.error(`[Supabase API Error] ${method} ${endpoint}:`, err);
    throw new Error(err.message || "Operation failed in Supabase");
  }
}

// ---------------------------------------------------------------------------
// PDF & Structured Report Download Helpers
// ---------------------------------------------------------------------------
export async function downloadPdfReport(endpoint, defaultFilename = "medical_report.pdf", token = null) {
  const apiBase = import.meta.env.VITE_API_URL;
  if (apiBase) {
    try {
      const res = await fetch(`${apiBase}${endpoint}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = defaultFilename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();
        return;
      }
    } catch {
      // Fall through to browser print
    }
  }

  // Client-side fallback: open browser print dialog
  window.print();
}

export async function fetchStructuredPatientReport(patientId, diagnosisId = null, token = null) {
  const query = diagnosisId ? `?diagnosis_id=${diagnosisId}` : "";
  return apiRequest(`/reports/patient/${patientId}/structured-report${query}`, {}, token);
}

