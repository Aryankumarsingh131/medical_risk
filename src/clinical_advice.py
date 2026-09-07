"""
src/clinical_advice.py
----------------------
Converts SHAP feature contributions + patient data into human-readable
clinical reasons and actionable medical recommendations.

Called from explain.py / api/main.py to enrich the prediction response.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Feature label mapping: internal name -> human-readable label
# ---------------------------------------------------------------------------

FEATURE_LABELS: Dict[str, str] = {
    "age": "Age",
    "resting_bp": "Systolic Blood Pressure",
    "systolic_bp": "Systolic Blood Pressure",
    "diastolic_bp": "Diastolic Blood Pressure",
    "cholesterol": "Cholesterol Level",
    "fasting_blood_sugar": "Fasting Blood Sugar",
    "max_heart_rate": "Maximum Heart Rate",
    "bmi": "Body Mass Index (BMI)",
    "smoking": "Smoking Status",
    "sex": "Sex",
    "temperature": "Body Temperature",
    "st_depression": "ST Depression (ECG)",
    "alcohol": "Alcohol Consumption",
    "drug": "Drug Use",
    "speech": "Speech Impairment",
    "movement": "Movement Impairment",
    "active_diagnosis": "Active Diagnosis",
    "prior_medical_events": "Prior Medical Events",
    "current_medication_list": "Current Medications",
    "chest_pain_type": "Chest Pain Type",
    "exercise_angina": "Exercise-Induced Angina",
    "hypertension": "Hypertension",
    "diabetes": "Diabetes",
    "family_history": "Family History",
    "exercise_frequency": "Exercise Frequency",
}


# ---------------------------------------------------------------------------
# Per-feature reason generators
# ---------------------------------------------------------------------------

def _reason_age(val: Optional[float], direction: str) -> str:
    if val is None:
        return "Age is a significant risk factor for cardiovascular disease."
    age = int(val)
    if age >= 65:
        return f"Age {age} — older age significantly increases cardiovascular risk."
    elif age >= 50:
        return f"Age {age} — middle age raises baseline risk of heart disease."
    elif age >= 40:
        return f"Age {age} — approaching middle age; risk begins to increase gradually."
    else:
        return f"Age {age} — relatively young; age is a lower-impact factor here."


def _reason_resting_bp(val: Optional[float], direction: str) -> str:
    if val is None:
        return "Blood pressure is a key cardiovascular risk marker."
    bp = float(val)
    if bp >= 160:
        return f"Systolic BP {bp:.0f} mmHg — stage 2 hypertension; very high risk of heart attack and stroke."
    elif bp >= 140:
        return f"Systolic BP {bp:.0f} mmHg — stage 1 hypertension; significantly elevated cardiac risk."
    elif bp >= 130:
        return f"Systolic BP {bp:.0f} mmHg — elevated BP (pre-hypertension); raises cardiac risk."
    elif bp >= 120:
        return f"Systolic BP {bp:.0f} mmHg — borderline elevated; monitor and manage lifestyle."
    else:
        return f"Systolic BP {bp:.0f} mmHg — normal range; protective against cardiac events."


def _reason_cholesterol(val: Optional[float], direction: str) -> str:
    if val is None:
        return "Cholesterol level is a major risk factor for artery blockage."
    chol = float(val)
    if chol >= 280:
        return f"Cholesterol {chol:.0f} mg/dL — very high; major risk for artery blockage and heart disease."
    elif chol >= 240:
        return f"Cholesterol {chol:.0f} mg/dL — high cholesterol; significantly elevates cardiovascular risk."
    elif chol >= 200:
        return f"Cholesterol {chol:.0f} mg/dL — borderline high; contributes to plaque buildup."
    else:
        return f"Cholesterol {chol:.0f} mg/dL — within healthy range; protective against heart disease."


def _reason_fasting_blood_sugar(val: Optional[float], direction: str) -> str:
    if val is None:
        return "Blood sugar control is linked to cardiovascular risk."
    fbs = float(val)
    if fbs >= 1 or fbs > 120:
        return "Elevated fasting blood sugar (>120 mg/dL) — indicates diabetes risk, strongly linked to heart disease."
    else:
        return "Normal fasting blood sugar (<120 mg/dL) — good metabolic control; protective factor."


def _reason_max_heart_rate(val: Optional[float], direction: str) -> str:
    if val is None:
        return "Maximum heart rate during stress reflects cardiac reserve."
    hr = float(val)
    if hr <= 100:
        return f"Max heart rate {hr:.0f} bpm — very low exercise capacity; may indicate poor cardiac function."
    elif hr <= 130:
        return f"Max heart rate {hr:.0f} bpm — reduced heart rate response; may signal decreased cardiac reserve."
    elif hr <= 160:
        return f"Max heart rate {hr:.0f} bpm — within expected range for age; reasonable exercise capacity."
    else:
        return f"Max heart rate {hr:.0f} bpm — high; indicates good cardiovascular fitness."


def _reason_bmi(val: Optional[float], direction: str) -> str:
    if val is None:
        return "BMI is associated with cardiovascular risk through obesity-related pathways."
    bmi = float(val)
    if bmi >= 35:
        return f"BMI {bmi:.1f} — severe obesity; significantly increases risk of heart disease, diabetes, and hypertension."
    elif bmi >= 30:
        return f"BMI {bmi:.1f} — obese range; increases cardiac load and raises cardiovascular risk."
    elif bmi >= 25:
        return f"BMI {bmi:.1f} — overweight; contributing to cardiovascular risk."
    elif bmi >= 18.5:
        return f"BMI {bmi:.1f} — healthy weight range; protective against cardiovascular disease."
    else:
        return f"BMI {bmi:.1f} — underweight; can also have cardiac implications."


def _reason_smoking(val: Optional[float], direction: str) -> str:
    if val is None or float(val) == 0:
        return "Non-smoker — absence of smoking is a significant protective factor."
    return "Smoker or past smoker — smoking causes artery damage and directly increases heart attack risk."


def _reason_hypertension(val: Optional[float], direction: str) -> str:
    if val is None or float(val) == 0:
        return "No hypertension diagnosis — reduces cardiovascular baseline risk."
    return "Diagnosed hypertension — chronically high blood pressure is a leading cause of heart disease and stroke."


def _reason_diabetes(val: Optional[float], direction: str) -> str:
    if val is None or float(val) == 0:
        return "No diabetes — absence of diabetes reduces risk of vascular complications."
    return "Diagnosed diabetes — damages blood vessels and nerves controlling the heart; 2–4× increased cardiac risk."


def _reason_exercise_angina(val: Optional[float], direction: str) -> str:
    if val is None or float(val) == 0:
        return "No exercise-induced chest pain — suggests adequate cardiac perfusion during activity."
    return "Exercise-induced angina — chest pain during exertion indicates possible coronary artery disease."


def _reason_st_depression(val: Optional[float], direction: str) -> str:
    if val is None:
        return "ST depression on ECG indicates potential myocardial ischemia."
    sd = float(val)
    if sd >= 2.0:
        return f"ST depression {sd:.1f} mm — significant ECG changes; strongly suggests myocardial ischemia."
    elif sd >= 0.5:
        return f"ST depression {sd:.1f} mm — ECG changes suggesting reduced blood flow to heart."
    else:
        return f"Minimal ST depression ({sd:.1f} mm) — no significant ECG ischemia pattern."


def _reason_prior_medical_events(val: Optional[float], direction: str) -> str:
    if val is None or float(val) == 0:
        return "No prior medical events — no history of previous cardiac episodes."
    return "Prior medical events recorded — history of cardiac/medical events significantly raises recurrence risk."


def _reason_chest_pain_type(val: Optional[float], direction: str) -> str:
    if val is None:
        return "Chest pain type is an important diagnostic indicator."
    cp = float(val)
    if cp == 0 or cp == 1:
        return "Typical angina (chest pain type) — classic symptom of coronary artery disease; high diagnostic value."
    elif cp == 2:
        return "Atypical chest pain — may indicate non-obstructive coronary disease."
    else:
        return "Asymptomatic chest pain type — can mask silent ischemia."


def _reason_sex(val: Optional[float], direction: str) -> str:
    if val is None:
        return "Sex is a biological risk factor for different cardiovascular disease patterns."
    if float(val) >= 1:
        return "Male sex — men have higher baseline risk of coronary artery disease at younger ages."
    return "Female sex — generally lower risk at this age, but risk increases significantly post-menopause."


def _reason_alcohol(val: Optional[float], direction: str) -> str:
    if val is None or float(val) == 0:
        return "No alcohol use — absence is a mildly protective factor."
    return "Alcohol consumption — heavy or regular drinking increases blood pressure and cardiac arrhythmia risk."


def _reason_generic(feature: str, val: Optional[float], direction: str) -> str:
    label = FEATURE_LABELS.get(feature, feature.replace("_", " ").title())
    direction_text = "is increasing" if direction == "increases risk" else "is decreasing"
    val_str = f" (value: {val})" if val is not None else ""
    return f"{label}{val_str} {direction_text} the risk based on the patient's clinical profile."


# ---------------------------------------------------------------------------
# Master reason dispatcher
# ---------------------------------------------------------------------------

REASON_GENERATORS = {
    "age": _reason_age,
    "resting_bp": _reason_resting_bp,
    "systolic_bp": _reason_resting_bp,
    "cholesterol": _reason_cholesterol,
    "fasting_blood_sugar": _reason_fasting_blood_sugar,
    "max_heart_rate": _reason_max_heart_rate,
    "bmi": _reason_bmi,
    "smoking": _reason_smoking,
    "hypertension": _reason_hypertension,
    "diabetes": _reason_diabetes,
    "exercise_angina": _reason_exercise_angina,
    "st_depression": _reason_st_depression,
    "prior_medical_events": _reason_prior_medical_events,
    "chest_pain_type": _reason_chest_pain_type,
    "sex": _reason_sex,
    "alcohol": _reason_alcohol,
}


def generate_reason(feature: str, val: Optional[float], direction: str) -> str:
    """Return a human-readable clinical reason for one SHAP feature contribution."""
    gen = REASON_GENERATORS.get(feature, None)
    if gen:
        return gen(val, direction)
    return _reason_generic(feature, val, direction)


# ---------------------------------------------------------------------------
# Recommendation generator
# ---------------------------------------------------------------------------

def generate_recommendations(
    risk_probability: float,
    top_contributions: List[Dict[str, Any]],
    patient_data: Dict[str, Any],
) -> List[str]:
    """
    Generate actionable clinical recommendations based on risk score and
    which features are driving the prediction upward.
    """
    recs: List[str] = []
    risk_pct = risk_probability * 100

    # Collect features that are increasing risk (positive SHAP)
    risk_drivers = [
        c["feature"]
        for c in top_contributions
        if c.get("shap_value", 0) > 0 and c.get("impact") in ("high impact", "moderate impact")
    ]

    # ---- Risk-level-based header recommendations ----
    if risk_pct >= 70:
        recs.append("URGENT: Immediate cardiology consultation recommended. Do not delay evaluation.")
        recs.append("Schedule a 12-lead ECG, stress test, and echocardiogram as soon as possible.")
    elif risk_pct >= 50:
        recs.append("Refer to a cardiologist for a thorough cardiovascular workup within 1–2 weeks.")
        recs.append("Consider ordering a lipid panel, fasting glucose, and resting ECG.")
    elif risk_pct >= 30:
        recs.append("Increased vigilance required. Schedule a follow-up within 1 month to reassess risk factors.")
    else:
        recs.append("Continue current healthy habits and maintain regular annual health checkups.")

    # ---- Feature-specific recommendations ----
    added = set()

    def add(text: str):
        if text not in added:
            recs.append(text)
            added.add(text)

    if "smoking" in risk_drivers or "smoking" in patient_data:
        smoking_val = patient_data.get("smoking", 0)
        if smoking_val and float(smoking_val) >= 1:
            add("Smoking cessation is the single most impactful lifestyle change — seek counseling or NRT (nicotine replacement therapy).")

    if "resting_bp" in risk_drivers or "systolic_bp" in risk_drivers:
        bp_val = patient_data.get("resting_bp") or patient_data.get("systolic_bp", 0) or 0
        if float(bp_val) >= 130:
            add("Blood pressure management: target <130/80 mmHg. Consider ACE inhibitors or ARBs, reduce sodium intake, limit alcohol.")

    if "cholesterol" in risk_drivers:
        chol_val = float(patient_data.get("cholesterol", 0) or 0)
        if chol_val >= 200:
            add("Cholesterol reduction: adopt a heart-healthy diet (less saturated fat, more fiber). Statins may be indicated if LDL >130 mg/dL.")

    if "bmi" in risk_drivers:
        bmi_val = float(patient_data.get("bmi", 0) or 0)
        if bmi_val >= 25:
            add(f"Weight management: target BMI <25. A 5–10% reduction in body weight can significantly lower cardiac risk.")

    if "fasting_blood_sugar" in risk_drivers:
        fbs_val = float(patient_data.get("fasting_blood_sugar", 0) or 0)
        if fbs_val >= 1:
            add("Diabetes management: monitor HbA1c, adopt a low-glycemic diet, consider metformin if pre-diabetic or diabetic.")

    if "exercise_angina" in risk_drivers:
        add("Exercise-induced chest pain requires immediate investigation — avoid strenuous activity until cleared by a cardiologist.")

    if "st_depression" in risk_drivers:
        add("Abnormal ECG pattern detected — refer for stress test or coronary angiography evaluation.")

    if "hypertension" in risk_drivers:
        add("Control hypertension with medication adherence, DASH diet, and regular BP monitoring at home.")

    if "diabetes" in risk_drivers:
        add("Tight glycemic control (HbA1c <7%) is essential to prevent vascular complications.")

    if "prior_medical_events" in risk_drivers:
        add("History of medical events: ensure patient is on secondary prevention therapy (aspirin, statins, beta-blockers as appropriate).")

    if "age" in risk_drivers:
        age_val = float(patient_data.get("age", 0) or 0)
        if age_val >= 50:
            add("Age-related risk: regular cardiac screening (ECG, BP, lipids) every 6–12 months is recommended.")

    # ---- General lifestyle recommendations ----
    if risk_pct >= 30:
        add("Adopt a Mediterranean-style diet: high in fruits, vegetables, whole grains, olive oil, and fish.")
        add("Physical activity: aim for at least 150 minutes of moderate aerobic exercise per week (e.g., brisk walking, cycling).")
        add("Avoid excessive alcohol — limit to <1 drink/day for women and <2 drinks/day for men.")
        add("Stress reduction: chronic stress raises cortisol and blood pressure. Consider mindfulness, yoga, or counseling.")

    if not recs:
        recs.append("Maintain a heart-healthy lifestyle: balanced diet, regular exercise, and avoid smoking.")

    return recs


# ---------------------------------------------------------------------------
# Risk category with percentage
# ---------------------------------------------------------------------------

def get_risk_category(probability: float) -> Dict[str, Any]:
    """Return structured risk tier info including percentage and label.
    
    Updated to match rule_based_risk.py thresholds for consistency:
    - Critical Risk: >= 0.80
    - High Risk: >= 0.55 and < 0.80
    - Moderate Risk: >= 0.30 and < 0.55
    - Low Risk: < 0.30
    """
    pct = round(probability * 100, 1)
    if probability >= 0.80:
        return {"label": "Critical Risk", "percentage": pct, "tier": "critical", "color": "#991b1b"}
    elif probability >= 0.55:
        return {"label": "High Risk", "percentage": pct, "tier": "high", "color": "#dc2626"}
    elif probability >= 0.30:
        return {"label": "Moderate Risk", "percentage": pct, "tier": "moderate", "color": "#d97706"}
    else:
        return {"label": "Low Risk", "percentage": pct, "tier": "low", "color": "#16a34a"}



# ---------------------------------------------------------------------------
# Main enrichment entry point
# ---------------------------------------------------------------------------

def enrich_explanation(
    explanation: Dict[str, Any],
    patient_data: Dict[str, Any],
    max_reasons: int = 5,
) -> Dict[str, Any]:
    """
    Takes raw explain_prediction() output and augments it with:
      - risk_percentage (float)
      - risk_category (dict with label, tier, color)
      - reasons (list of human-readable clinical reasons for top drivers)
      - recommendations (list of actionable advice strings)

    Returns the enriched dict ready to be sent in the API response.
    """
    contributions = explanation.get("top_contributions", [])
    prob = float(explanation.get("risk_score", 0))

    # Determine which feature names were actually provided by the caller
    # (also treat resting_bp as provided when systolic_bp was given)
    provided_feats = set(patient_data.keys())
    if "systolic_bp" in provided_feats:
        provided_feats.add("resting_bp")

    # Build reasons — prefer features that were explicitly provided.
    # For imputed-zero features (alcohol=0, movement=0, etc.) only include
    # them if they actually came from the caller's data.
    reasons: List[Dict[str, Any]] = []
    for c in contributions:
        feat = c["feature"]
        val = c.get("value")
        shap_val = c.get("shap_value", 0)
        direction = c.get("direction", "")
        impact = c.get("impact", "low impact")

        # Skip features that were not explicitly given (imputed from population defaults)
        if feat not in provided_feats:
            continue

        # Skip low-impact features that were provided but barely matter
        if impact == "low impact" and abs(float(shap_val)) < 0.05:
            continue

        label = FEATURE_LABELS.get(feat, feat.replace("_", " ").title())
        reason_text = generate_reason(feat, val, direction)

        reasons.append({
            "feature": feat,
            "label": label,
            "value": val,
            "shap_value": round(float(shap_val), 4),
            "impact": impact,
            "direction": direction,
            "reason": reason_text,
        })

        if len(reasons) >= max_reasons:
            break

    # If somehow we have no reasons (very sparse input), fall back to top contributors
    if not reasons:
        for c in contributions[:3]:
            feat = c["feature"]
            val = c.get("value")
            shap_val = c.get("shap_value", 0)
            direction = c.get("direction", "")
            impact = c.get("impact", "low impact")
            label = FEATURE_LABELS.get(feat, feat.replace("_", " ").title())
            reason_text = generate_reason(feat, val, direction)
            reasons.append({
                "feature": feat,
                "label": label,
                "value": val,
                "shap_value": round(float(shap_val), 4),
                "impact": impact,
                "direction": direction,
                "reason": reason_text,
            })

    risk_cat = get_risk_category(prob)
    
    # Use clinical recommendations from rule engine if available, otherwise generate our own
    if "clinical_recommendations" in explanation and explanation["clinical_recommendations"]:
        recommendations = explanation["clinical_recommendations"]
    else:
        recommendations = generate_recommendations(prob, contributions, patient_data)

    return {
        **explanation,
        "risk_percentage": risk_cat["percentage"],
        "risk_category": risk_cat,
        "reasons": reasons,
        "recommendations": recommendations,
    }
