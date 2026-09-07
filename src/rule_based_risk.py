"""
src/rule_based_risk.py
-----------------------
Structured, deterministic clinical rule engine for cardiovascular / general
medical risk assessment.

DESIGN GOALS (v2)
==================
1. Every threshold is centralized in `ClinicalThresholds` and commented with
   the guideline it is drawn from (AHA/ACC 2017 hypertension, NCEP ATP III
   lipids, ADA diabetes criteria, WHO BMI classes, KDIGO CKD staging). This
   keeps the numbers auditable and easy to update as guidelines change.
2. Inputs are normalized defensively (binary flags may arrive as
   0/1, True/False, "yes"/"no", etc.) instead of silently mis-parsing.
3. Score aggregation uses a noisy-OR combination instead of an ad hoc
   "top-4 weighted average". Noisy-OR is the standard way to combine several
   roughly-independent risk factors into one probability-like score: it
   saturates smoothly toward 1.0 as more factors stack, rather than being
   dominated only by whichever four rules happen to fire highest.
4. A small number of "critical override" rules can force a Critical
   classification regardless of the aggregate score (e.g. a hypertensive
   crisis should never be diluted into "Moderate" just because nothing else
   is abnormal).
5. The engine reports a data-completeness score so a consumer can tell a
   confident "Low Risk" (lots of normal data) apart from an unreliable one
   (almost nothing was submitted).
6. Output dict keeps the original v1 keys (risk_score, risk_label,
   risk_category, triggered_rules, top_contributions, scoring_method) so
   existing UI code keeps working, and adds a few new, clearly-named keys.

IMPORTANT / DISCLAIMER
=======================
This module is a transparent, rule-based decision-support heuristic. It is
NOT a validated diagnostic tool, is NOT a substitute for clinical judgment,
and has NOT been cleared by any regulatory body. Thresholds reflect commonly
cited population-level guidelines and will not fit every patient. Any
production use requires review by a qualified clinician and validation
against real outcome data.

File Path: src/rule_based_risk.py
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

RULES_VERSION = "2.1.0"

# Point bands are deliberately separate from the legacy ``rule_score`` value.
# ``rule_score`` remains in the public response for existing clients, while
# points are the only values used to determine the final clinical band.  This
# prevents probability-like scores from being multiplied together (the former
# noisy-OR implementation made several ordinary findings look critical).
RISK_POINT_BANDS = (
    (0, "Normal", "Low Risk"),
    (10, "Medium", "Moderate Risk"),
    (30, "High", "High Risk"),
    (55, "Critical", "Critical Risk"),
)

# Explicit weight schedule for every rule score used by the evaluators.  A
# rule's score is retained as backwards-compatible metadata; this table is
# the authoritative scoring contract and can be unit-tested independently.
RULE_SCORE_POINTS = {
    0.00: 0, 0.04: 1, 0.05: 1, 0.06: 1, 0.08: 2, 0.10: 2,
    0.12: 3, 0.15: 3, 0.20: 4, 0.25: 5, 0.30: 5, 0.35: 6,
    0.40: 7, 0.45: 8, 0.50: 9, 0.55: 10, 0.60: 11, 0.65: 12,
    0.70: 13, 0.75: 14, 0.80: 15, 0.82: 16, 0.85: 17, 0.88: 18,
    0.90: 20, 0.92: 22, 0.95: 25, 0.98: 30,
}


# ---------------------------------------------------------------------------
# Safe parsing helpers
# ---------------------------------------------------------------------------

def _to_float(val: Any) -> Optional[float]:
    """Safely cast value to float. Returns None for missing/invalid data."""
    if val is None:
        return None
    try:
        f = float(val)
        return f if math.isfinite(f) else None
    except (ValueError, TypeError):
        return None


_TRUTHY = {"1", "true", "t", "yes", "y"}
_FALSY = {"0", "false", "f", "no", "n"}


def _to_binary_flag(val: Any) -> Optional[bool]:
    """
    Normalizes a value that is *meant* to be a binary clinical flag
    (e.g. smoking, diabetes diagnosis, exercise-induced angina) into
    True / False / None.

    Handles 1/0, 1.0/0.0, True/False, and common string forms
    ("yes"/"no", "y"/"n", "true"/"false"). Anything else is treated as
    unknown (None) rather than silently coerced, which was a source of
    bugs in v1 (e.g. a raw glucose reading of "1" being misread as a
    positive flag).
    """
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        v = val.strip().lower()
        if v in _TRUTHY:
            return True
        if v in _FALSY:
            return False
        return None
    f = _to_float(val)
    if f == 1.0:
        return True
    if f == 0.0:
        return False
    return None  # e.g. 120 mg/dL raw glucose is NOT a binary flag


# ---------------------------------------------------------------------------
# Thresholds — centralized & guideline-referenced
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ClinicalThresholds:
    # Blood pressure (mmHg) — AHA/ACC 2017 hypertension guideline categories
    bp_crisis_sys: float = 180.0
    bp_crisis_dia: float = 120.0
    bp_stage2_sys: float = 140.0
    bp_stage2_dia: float = 90.0
    bp_stage1_sys: float = 130.0
    bp_stage1_dia: float = 80.0
    bp_elevated_sys: float = 120.0

    # Total cholesterol (mg/dL) — NCEP ATP III
    chol_high: float = 240.0
    chol_borderline: float = 200.0
    chol_very_high: float = 280.0  # local extension for "very high" tier

    # LDL (mg/dL) — NCEP ATP III
    ldl_very_high: float = 190.0
    ldl_high: float = 160.0
    ldl_borderline: float = 130.0
    ldl_near_optimal: float = 100.0

    # HDL (mg/dL) — low HDL is itself an independent risk factor
    hdl_low: float = 40.0
    hdl_protective: float = 60.0

    # Triglycerides (mg/dL)
    trig_very_high: float = 500.0
    trig_high: float = 200.0
    trig_borderline: float = 150.0

    # Glucose / diabetes — ADA criteria
    fbs_diabetes_mgdl: float = 126.0
    fbs_prediabetes_mgdl: float = 100.0
    hba1c_diabetes: float = 6.5
    hba1c_prediabetes: float = 5.7

    # ECG ST depression (mm), exercise stress test "oldpeak"
    st_dep_severe: float = 2.0
    st_dep_moderate: float = 1.0
    st_dep_mild: float = 0.5

    # BMI (kg/m^2) — WHO classification
    bmi_obese_3: float = 40.0
    bmi_obese_2: float = 35.0
    bmi_obese_1: float = 30.0
    bmi_overweight: float = 25.0
    bmi_underweight: float = 18.5

    # Heart-rate reserve ratio bounds (max_hr / age-predicted max)
    hr_reserve_low_ratio: float = 0.55
    hr_reserve_high_ratio: float = 1.05

    # Age bands (years)
    age_senior: float = 65.0
    age_middle: float = 50.0
    age_adult: float = 40.0

    # Family history of premature coronary artery disease
    premature_cad_male_age: float = 55.0
    premature_cad_female_age: float = 65.0

    # eGFR (mL/min/1.73m^2) — KDIGO CKD stages
    egfr_stage2: float = 90.0
    egfr_stage3a: float = 60.0
    egfr_stage3b: float = 45.0
    egfr_stage4: float = 30.0
    egfr_stage5: float = 15.0

    # Number of major vessels with fluoroscopic narrowing (0-3)
    vessels_high_risk: float = 2.0


DEFAULT_THRESHOLDS = ClinicalThresholds()


class RiskTier(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


TIER_META = {
    RiskTier.LOW: ("Low Risk", "#16a34a"),
    RiskTier.MODERATE: ("Moderate Risk", "#d97706"),
    RiskTier.HIGH: ("High Risk", "#dc2626"),
    RiskTier.CRITICAL: ("Critical Risk", "#991b1b"),
}


@dataclass
class RuleTrigger:
    rule_code: str
    category: str
    description: str
    rule_score: float
    value: Optional[float] = None
    severity: str = "info"  # "info" | "warning" | "critical"
    guideline: str = ""     # short reference, e.g. "AHA/ACC 2017"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_code": self.rule_code,
            "category": self.category,
            "description": self.description,
            "rule_score": round(self.rule_score, 4),
            "points": points_for_rule(self),
            "value": self.value,
            "severity": self.severity,
            "guideline": self.guideline,
        }


def points_for_rule(rule: RuleTrigger) -> int:
    """Return the documented point weight for one fired rule."""
    return RULE_SCORE_POINTS.get(round(rule.rule_score, 2), int(round(rule.rule_score * 20)))


def risk_band_for_points(total_points: int) -> Tuple[str, RiskTier]:
    """Deterministically map point totals to the externally stable risk tier."""
    tiers = {
        "Normal": RiskTier.LOW,
        "Medium": RiskTier.MODERATE,
        "High": RiskTier.HIGH,
        "Critical": RiskTier.CRITICAL,
    }
    for minimum, band, _legacy_label in reversed(RISK_POINT_BANDS):
        if total_points >= minimum:
            return band, tiers[band]
    return "Normal", RiskTier.LOW


# ---------------------------------------------------------------------------
# Individual clinical factor evaluators
# ---------------------------------------------------------------------------

def evaluate_blood_pressure(
    sys_bp: Optional[float],
    dia_bp: Optional[float],
    t: ClinicalThresholds = DEFAULT_THRESHOLDS,
) -> List[RuleTrigger]:
    """Evaluates blood pressure per AHA/ACC 2017 categories."""
    if sys_bp is None and dia_bp is None:
        return []

    sys_v = sys_bp if sys_bp is not None else 120.0
    dia_v = dia_bp if dia_bp is not None else 80.0

    if sys_v >= t.bp_crisis_sys or dia_v >= t.bp_crisis_dia:
        return [RuleTrigger(
            "BP_CRISIS", "Blood Pressure",
            f"Hypertensive Crisis (Systolic {sys_v:.0f} / Diastolic {dia_v:.0f} mmHg)",
            0.95, sys_v, "critical", "AHA/ACC 2017",
        )]
    if sys_v >= t.bp_stage2_sys or dia_v >= t.bp_stage2_dia:
        return [RuleTrigger(
            "BP_STAGE2", "Blood Pressure",
            f"Stage 2 Hypertension (Systolic {sys_v:.0f} / Diastolic {dia_v:.0f} mmHg)",
            0.75, sys_v, "warning", "AHA/ACC 2017",
        )]
    if sys_v >= t.bp_stage1_sys or dia_v >= t.bp_stage1_dia:
        return [RuleTrigger(
            "BP_STAGE1", "Blood Pressure",
            f"Stage 1 Hypertension (Systolic {sys_v:.0f} / Diastolic {dia_v:.0f} mmHg)",
            0.45, sys_v, "warning", "AHA/ACC 2017",
        )]
    if sys_v >= t.bp_elevated_sys and dia_v < t.bp_stage1_dia:
        return [RuleTrigger(
            "BP_ELEVATED", "Blood Pressure",
            f"Elevated Blood Pressure (Systolic {sys_v:.0f} mmHg)",
            0.20, sys_v, "info", "AHA/ACC 2017",
        )]
    return [RuleTrigger(
        "BP_NORMAL", "Blood Pressure",
        f"Normal Blood Pressure (Systolic {sys_v:.0f} / Diastolic {dia_v:.0f} mmHg)",
        0.05, sys_v, "info", "AHA/ACC 2017",
    )]


def evaluate_lipid_panel(
    chol: Optional[float],
    ldl: Optional[float] = None,
    hdl: Optional[float] = None,
    triglycerides: Optional[float] = None,
    t: ClinicalThresholds = DEFAULT_THRESHOLDS,
) -> List[RuleTrigger]:
    """
    Evaluates the lipid panel. Total cholesterol is scored on its own (v1
    behavior preserved), and LDL / HDL / triglycerides are scored
    independently when available since each carries distinct clinical
    meaning (e.g. a patient can have a "normal" total cholesterol while
    still having dangerously low HDL or high triglycerides).
    """
    triggers: List[RuleTrigger] = []

    if chol is not None:
        if chol >= t.chol_very_high:
            triggers.append(RuleTrigger(
                "CHOL_VERY_HIGH", "Cholesterol",
                f"Very High Total Cholesterol ({chol:.0f} mg/dL)",
                0.85, chol, "critical", "NCEP ATP III",
            ))
        elif chol >= t.chol_high:
            triggers.append(RuleTrigger(
                "CHOL_HIGH", "Cholesterol",
                f"High Total Cholesterol ({chol:.0f} mg/dL)",
                0.65, chol, "warning", "NCEP ATP III",
            ))
        elif chol >= t.chol_borderline:
            triggers.append(RuleTrigger(
                "CHOL_BORDERLINE", "Cholesterol",
                f"Borderline High Total Cholesterol ({chol:.0f} mg/dL)",
                0.35, chol, "info", "NCEP ATP III",
            ))
        else:
            triggers.append(RuleTrigger(
                "CHOL_DESIRABLE", "Cholesterol",
                f"Desirable Total Cholesterol ({chol:.0f} mg/dL)",
                0.05, chol, "info", "NCEP ATP III",
            ))

    if ldl is not None:
        if ldl >= t.ldl_very_high:
            triggers.append(RuleTrigger(
                "LDL_VERY_HIGH", "Cholesterol",
                f"Very High LDL ({ldl:.0f} mg/dL)", 0.80, ldl, "critical", "NCEP ATP III",
            ))
        elif ldl >= t.ldl_high:
            triggers.append(RuleTrigger(
                "LDL_HIGH", "Cholesterol",
                f"High LDL ({ldl:.0f} mg/dL)", 0.60, ldl, "warning", "NCEP ATP III",
            ))
        elif ldl >= t.ldl_borderline:
            triggers.append(RuleTrigger(
                "LDL_BORDERLINE", "Cholesterol",
                f"Borderline High LDL ({ldl:.0f} mg/dL)", 0.35, ldl, "info", "NCEP ATP III",
            ))

    if hdl is not None:
        if hdl < t.hdl_low:
            triggers.append(RuleTrigger(
                "HDL_LOW", "Cholesterol",
                f"Low HDL — independent cardiovascular risk factor ({hdl:.0f} mg/dL)",
                0.45, hdl, "warning", "NCEP ATP III",
            ))
        elif hdl >= t.hdl_protective:
            triggers.append(RuleTrigger(
                "HDL_PROTECTIVE", "Cholesterol",
                f"High HDL — protective factor ({hdl:.0f} mg/dL)",
                0.0, hdl, "info", "NCEP ATP III",
            ))

    if triglycerides is not None:
        if triglycerides >= t.trig_very_high:
            triggers.append(RuleTrigger(
                "TRIG_VERY_HIGH", "Cholesterol",
                f"Very High Triglycerides ({triglycerides:.0f} mg/dL) — pancreatitis risk",
                0.70, triglycerides, "critical", "NCEP ATP III",
            ))
        elif triglycerides >= t.trig_high:
            triggers.append(RuleTrigger(
                "TRIG_HIGH", "Cholesterol",
                f"High Triglycerides ({triglycerides:.0f} mg/dL)",
                0.45, triglycerides, "warning", "NCEP ATP III",
            ))
        elif triglycerides >= t.trig_borderline:
            triggers.append(RuleTrigger(
                "TRIG_BORDERLINE", "Cholesterol",
                f"Borderline High Triglycerides ({triglycerides:.0f} mg/dL)",
                0.25, triglycerides, "info", "NCEP ATP III",
            ))

    return [x for x in triggers if x.rule_score > 0.0]


def evaluate_glucose_diabetes(
    fbs_raw: Any,
    glucose_mgdl: Optional[float] = None,
    hba1c: Optional[float] = None,
    diabetes_dx: Any = None,
    t: ClinicalThresholds = DEFAULT_THRESHOLDS,
) -> List[RuleTrigger]:
    """
    Evaluates glucose / diabetes status.

    v1 bug fixed: `fasting_blood_sugar` was being read both as a raw mg/dL
    value AND as a binary "fasting blood sugar > 120" flag (a common
    convention in clinical datasets), which meant a raw reading of exactly
    1 mg/dL was misread as a positive flag. Here the binary flag and the
    raw value are treated as distinct, separately-supplied inputs:
      - `fbs_raw`: the conventional binary "fasting glucose > 120 mg/dL?"
        flag (0/1/True/False/yes/no).
      - `glucose_mgdl`: an actual fasting glucose lab value, if available.
      - `hba1c`: hemoglobin A1c percentage, if available.
      - `diabetes_dx`: a clinician-diagnosed diabetes flag.
    Any subset may be supplied; whichever carries the clearest signal wins.
    """
    triggers: List[RuleTrigger] = []
    dx = _to_binary_flag(diabetes_dx)
    fbs_flag = _to_binary_flag(fbs_raw)
    glucose = _to_float(glucose_mgdl)
    a1c = _to_float(hba1c)

    if dx is True:
        triggers.append(RuleTrigger(
            "DIABETES_DX", "Blood Sugar / Diabetes",
            "Clinician-Diagnosed Diabetes", 0.75, None, "critical", "ADA",
        ))

    if a1c is not None:
        if a1c >= t.hba1c_diabetes:
            triggers.append(RuleTrigger(
                "HBA1C_DIABETES", "Blood Sugar / Diabetes",
                f"HbA1c in Diabetic Range ({a1c:.1f}%)", 0.70, a1c, "critical", "ADA",
            ))
        elif a1c >= t.hba1c_prediabetes:
            triggers.append(RuleTrigger(
                "HBA1C_PREDIABETES", "Blood Sugar / Diabetes",
                f"HbA1c in Prediabetic Range ({a1c:.1f}%)", 0.35, a1c, "warning", "ADA",
            ))

    if glucose is not None:
        if glucose >= t.fbs_diabetes_mgdl:
            triggers.append(RuleTrigger(
                "FBS_DIABETES_RANGE", "Blood Sugar / Diabetes",
                f"Fasting Glucose in Diabetic Range ({glucose:.0f} mg/dL)",
                0.70, glucose, "critical", "ADA",
            ))
        elif glucose >= t.fbs_prediabetes_mgdl:
            triggers.append(RuleTrigger(
                "FBS_PREDIABETES_RANGE", "Blood Sugar / Diabetes",
                f"Impaired Fasting Glucose ({glucose:.0f} mg/dL)",
                0.35, glucose, "warning", "ADA",
            ))

    # Fallback: only the conventional binary "fbs > 120" flag was supplied,
    # with no diagnosis and no raw values.
    if not triggers and fbs_flag is True:
        triggers.append(RuleTrigger(
            "FBS_FLAG_POSITIVE", "Blood Sugar / Diabetes",
            "Fasting Blood Sugar Flag Positive (> 120 mg/dL)",
            0.60, None, "warning", "ADA",
        ))

    return triggers


def evaluate_ecg(
    st_dep: Optional[float],
    st_slope: Any = None,
    resting_ecg: Any = None,
    t: ClinicalThresholds = DEFAULT_THRESHOLDS,
) -> List[RuleTrigger]:
    """
    Evaluates exercise ECG findings.
      - st_dep: ST-segment depression in mm ("oldpeak").
      - st_slope: 0 = upsloping (favorable), 1 = flat, 2 = downsloping
        (least favorable) — standard exercise-ECG coding; treated as
        optional and only scored if present.
      - resting_ecg: 0 = normal, 1 = ST-T wave abnormality,
        2 = probable/definite left ventricular hypertrophy.
    """
    triggers: List[RuleTrigger] = []
    dep = _to_float(st_dep)
    slope = _to_float(st_slope)
    ecg = _to_float(resting_ecg)

    if dep is not None and dep > 0.0:
        if dep >= t.st_dep_severe:
            triggers.append(RuleTrigger(
                "ST_DEP_SEVERE", "ECG",
                f"Severe ST Depression ({dep:.1f} mm) — strong ischemic sign",
                0.90, dep, "critical", "Exercise ECG",
            ))
        elif dep >= t.st_dep_moderate:
            triggers.append(RuleTrigger(
                "ST_DEP_MODERATE", "ECG",
                f"Moderate ST Depression ({dep:.1f} mm)", 0.65, dep, "warning", "Exercise ECG",
            ))
        elif dep >= t.st_dep_mild:
            triggers.append(RuleTrigger(
                "ST_DEP_MILD", "ECG",
                f"Mild ST Depression ({dep:.1f} mm)", 0.35, dep, "info", "Exercise ECG",
            ))

    if slope == 2.0:
        triggers.append(RuleTrigger(
            "ST_SLOPE_DOWN", "ECG",
            "Downsloping ST Segment — least favorable exercise ECG pattern",
            0.55, slope, "warning", "Exercise ECG",
        ))
    elif slope == 1.0:
        triggers.append(RuleTrigger(
            "ST_SLOPE_FLAT", "ECG",
            "Flat ST Segment on Exercise ECG", 0.30, slope, "info", "Exercise ECG",
        ))

    if ecg == 2.0:
        triggers.append(RuleTrigger(
            "RESTING_ECG_LVH", "ECG",
            "Resting ECG: Probable/Definite Left Ventricular Hypertrophy",
            0.50, ecg, "warning", "Resting ECG",
        ))
    elif ecg == 1.0:
        triggers.append(RuleTrigger(
            "RESTING_ECG_STT", "ECG",
            "Resting ECG: ST-T Wave Abnormality", 0.35, ecg, "info", "Resting ECG",
        ))

    return triggers


def evaluate_chest_pain_and_angina(
    cp_type: Optional[float], ex_angina: Any,
) -> List[RuleTrigger]:
    """
    Evaluates chest-pain classification and exercise-induced angina.

    Standard coding: 0 = typical angina, 1 = atypical angina,
    2 = non-anginal pain, 3 = asymptomatic.

    v1 bug fixed: cp_type == 3 ("asymptomatic") produced no trigger at
    all. In practice, asymptomatic patients undergoing cardiac workup can
    still have significant silent ischemia, so this is now scored (at a
    moderate level, reflecting genuine diagnostic uncertainty) rather than
    silently treated as zero risk.
    """
    cp = _to_float(cp_type)
    ang = _to_binary_flag(ex_angina)
    triggers: List[RuleTrigger] = []

    if cp in (0.0, 1.0):
        triggers.append(RuleTrigger(
            "CHEST_PAIN_ANGINA", "Chest Pain & Angina",
            "Typical/Atypical Angina Pectoris Symptoms", 0.70, cp, "critical",
        ))
    elif cp == 2.0:
        triggers.append(RuleTrigger(
            "CHEST_PAIN_NONANGINAL", "Chest Pain & Angina",
            "Non-Anginal Chest Pain Present", 0.35, cp, "info",
        ))
    elif cp == 3.0:
        triggers.append(RuleTrigger(
            "CHEST_PAIN_ASYMPTOMATIC", "Chest Pain & Angina",
            "Asymptomatic — cannot rule out silent ischemia on symptoms alone",
            0.30, cp, "warning",
        ))

    if ang is True:
        triggers.append(RuleTrigger(
            "EXERCISE_ANGINA", "Chest Pain & Angina",
            "Exercise-Induced Angina Present", 0.75, 1.0, "critical",
        ))

    return triggers


def evaluate_bmi(bmi: Optional[float], t: ClinicalThresholds = DEFAULT_THRESHOLDS) -> List[RuleTrigger]:
    """Evaluates Body Mass Index per WHO classification."""
    if bmi is None:
        return []

    if bmi >= t.bmi_obese_3:
        return [RuleTrigger("BMI_OBESE_3", "BMI", f"Obesity Class III (BMI {bmi:.1f} kg/m²)", 0.85, bmi, "critical", "WHO")]
    if bmi >= t.bmi_obese_2:
        return [RuleTrigger("BMI_OBESE_2", "BMI", f"Obesity Class II (BMI {bmi:.1f} kg/m²)", 0.70, bmi, "warning", "WHO")]
    if bmi >= t.bmi_obese_1:
        return [RuleTrigger("BMI_OBESE_1", "BMI", f"Obesity Class I (BMI {bmi:.1f} kg/m²)", 0.55, bmi, "warning", "WHO")]
    if bmi >= t.bmi_overweight:
        return [RuleTrigger("BMI_OVERWEIGHT", "BMI", f"Overweight (BMI {bmi:.1f} kg/m²)", 0.30, bmi, "info", "WHO")]
    if bmi < t.bmi_underweight:
        return [RuleTrigger("BMI_UNDERWEIGHT", "BMI", f"Underweight (BMI {bmi:.1f} kg/m²)", 0.25, bmi, "info", "WHO")]
    return [RuleTrigger("BMI_NORMAL", "BMI", f"Normal BMI ({bmi:.1f} kg/m²)", 0.05, bmi, "info", "WHO")]


def evaluate_heart_rate_reserve(
    hr: Optional[float], age: Optional[float], t: ClinicalThresholds = DEFAULT_THRESHOLDS,
) -> List[RuleTrigger]:
    """Evaluates achieved max heart rate relative to age-predicted maximum (220 - age)."""
    if hr is None:
        return []
    age_val = age if age is not None else 50.0
    expected_max = max(100.0, 220.0 - age_val)
    ratio = hr / expected_max

    if ratio < t.hr_reserve_low_ratio:
        return [RuleTrigger(
            "HR_CHRONOTROPIC_INCOMPETENCE", "Heart Rate",
            f"Reduced Max Heart Rate Reserve ({hr:.0f} bpm, {ratio*100:.0f}% of predicted max)",
            0.65, hr, "warning",
        )]
    if ratio > t.hr_reserve_high_ratio:
        return [RuleTrigger(
            "HR_EXCESSIVE_TACHYCARDIA", "Heart Rate",
            f"Excessive Peak Heart Rate ({hr:.0f} bpm, {ratio*100:.0f}% of predicted max)",
            0.40, hr, "info",
        )]
    return [RuleTrigger("HR_NORMAL", "Heart Rate", f"Normal Heart Rate Response ({hr:.0f} bpm)", 0.05, hr, "info")]


def evaluate_age_sex(
    age: Optional[float], sex: Any = None, t: ClinicalThresholds = DEFAULT_THRESHOLDS,
) -> List[RuleTrigger]:
    """
    Evaluates age-related baseline cardiovascular risk. Sex is accepted
    only to disambiguate downstream sex-specific rules (e.g. family
    history of *premature* CAD) — it is not scored on its own here, since
    doing so without a validated sex-specific risk model would be
    misleading.
    """
    if age is None:
        return []
    if age >= t.age_senior:
        return [RuleTrigger("AGE_SENIOR", "Age", f"Age {age:.0f} — advanced-age baseline risk", 0.60, age, "warning")]
    if age >= t.age_middle:
        return [RuleTrigger("AGE_MIDDLE", "Age", f"Age {age:.0f} — middle-age baseline risk", 0.40, age, "info")]
    if age >= t.age_adult:
        return [RuleTrigger("AGE_ADULT", "Age", f"Age {age:.0f} — adult baseline risk", 0.20, age, "info")]
    return [RuleTrigger("AGE_YOUNG", "Age", f"Age {age:.0f} — low baseline age-related risk", 0.05, age, "info")]


def evaluate_vessels_and_thal(
    ca: Optional[float], thal: Optional[float], t: ClinicalThresholds = DEFAULT_THRESHOLDS,
) -> List[RuleTrigger]:
    """
    Evaluates fluoroscopy vessel count and thallium stress test result —
    two of the strongest predictors in standard cardiac catheterization
    datasets, and both entirely absent from v1.
      - ca: number of major vessels (0-3) colored by fluoroscopy.
      - thal: 3 = normal, 6 = fixed defect, 7 = reversible defect
        (reversible defect indicates inducible ischemia and carries the
        highest risk of the three).
    """
    triggers: List[RuleTrigger] = []
    ca_v = _to_float(ca)
    thal_v = _to_float(thal)

    if ca_v is not None:
        if ca_v >= t.vessels_high_risk:
            triggers.append(RuleTrigger(
                "VESSELS_MULTI", "Vessel Imaging",
                f"Multi-Vessel Disease — {int(ca_v)} major vessels narrowed",
                0.80, ca_v, "critical", "Fluoroscopy",
            ))
        elif ca_v >= 1.0:
            triggers.append(RuleTrigger(
                "VESSELS_SINGLE", "Vessel Imaging",
                f"Single-Vessel Disease — {int(ca_v)} major vessel narrowed",
                0.50, ca_v, "warning", "Fluoroscopy",
            ))

    if thal_v == 7.0:
        triggers.append(RuleTrigger(
            "THAL_REVERSIBLE_DEFECT", "Vessel Imaging",
            "Thallium Test: Reversible Defect — inducible ischemia",
            0.75, thal_v, "critical", "Thallium stress test",
        ))
    elif thal_v == 6.0:
        triggers.append(RuleTrigger(
            "THAL_FIXED_DEFECT", "Vessel Imaging",
            "Thallium Test: Fixed Defect — prior infarct pattern",
            0.55, thal_v, "warning", "Thallium stress test",
        ))

    return triggers


def evaluate_renal_function(
    creatinine: Optional[float], egfr: Optional[float], t: ClinicalThresholds = DEFAULT_THRESHOLDS,
) -> List[RuleTrigger]:
    """
    Evaluates renal function via eGFR (preferred) using KDIGO CKD staging.
    Reduced renal function is an independent, often under-weighted,
    cardiovascular risk amplifier — absent entirely from v1.
    """
    egfr_v = _to_float(egfr)
    creat_v = _to_float(creatinine)
    if egfr_v is None:
        return []

    if egfr_v < t.egfr_stage5:
        return [RuleTrigger("CKD_STAGE5", "Renal Function", f"CKD Stage 5 / Kidney Failure (eGFR {egfr_v:.0f})", 0.90, egfr_v, "critical", "KDIGO")]
    if egfr_v < t.egfr_stage4:
        return [RuleTrigger("CKD_STAGE4", "Renal Function", f"CKD Stage 4, Severely Decreased (eGFR {egfr_v:.0f})", 0.75, egfr_v, "critical", "KDIGO")]
    if egfr_v < t.egfr_stage3b:
        return [RuleTrigger("CKD_STAGE3B", "Renal Function", f"CKD Stage 3b, Moderately-Severely Decreased (eGFR {egfr_v:.0f})", 0.55, egfr_v, "warning", "KDIGO")]
    if egfr_v < t.egfr_stage3a:
        return [RuleTrigger("CKD_STAGE3A", "Renal Function", f"CKD Stage 3a, Mildly-Moderately Decreased (eGFR {egfr_v:.0f})", 0.35, egfr_v, "info", "KDIGO")]
    if egfr_v < t.egfr_stage2:
        return [RuleTrigger("CKD_STAGE2", "Renal Function", f"CKD Stage 2, Mildly Decreased (eGFR {egfr_v:.0f})", 0.15, egfr_v, "info", "KDIGO")]
    return [RuleTrigger("RENAL_NORMAL", "Renal Function", f"Normal Renal Function (eGFR {egfr_v:.0f})", 0.05, egfr_v, "info", "KDIGO")]


def evaluate_lifestyle_and_history(
    data: Dict[str, Any], t: ClinicalThresholds = DEFAULT_THRESHOLDS,
) -> List[RuleTrigger]:
    """Evaluates lifestyle factors, comorbidities, and family history."""
    triggers: List[RuleTrigger] = []

    if _to_binary_flag(data.get("smoking")) is True:
        triggers.append(RuleTrigger("SMOKING", "Lifestyle & History", "Active / Past Smoking History", 0.65, 1.0, "warning"))
    if _to_binary_flag(data.get("hypertension")) is True:
        triggers.append(RuleTrigger("HYPERTENSION_DX", "Lifestyle & History", "Diagnosed Hypertension History", 0.55, 1.0, "warning"))
    if data.get("prior_medical_events"):
        triggers.append(RuleTrigger(
            "PRIOR_EVENTS", "Lifestyle & History",
            f"Prior Cardiac/Medical Events: {data.get('prior_medical_events')}", 0.60, None, "critical",
        ))
    if _to_binary_flag(data.get("alcohol")) is True:
        triggers.append(RuleTrigger("ALCOHOL_USE", "Lifestyle & History", "Regular Alcohol Consumption", 0.25, 1.0, "info"))
    if _to_binary_flag(data.get("sedentary")) is True:
        triggers.append(RuleTrigger("SEDENTARY_LIFESTYLE", "Lifestyle & History", "Sedentary Lifestyle / Low Physical Activity", 0.30, 1.0, "info"))

    family_hx = _to_binary_flag(data.get("family_history_cad"))
    if family_hx is True:
        age_val = _to_float(data.get("family_history_onset_age"))
        sex = str(data.get("sex", "")).strip().lower()
        premature_cutoff = t.premature_cad_female_age if sex in ("f", "female") else t.premature_cad_male_age
        if age_val is not None and age_val < premature_cutoff:
            triggers.append(RuleTrigger(
                "FAMILY_HX_PREMATURE_CAD", "Lifestyle & History",
                f"Family History of Premature Coronary Artery Disease (onset age {age_val:.0f})",
                0.55, age_val, "warning",
            ))
        else:
            triggers.append(RuleTrigger(
                "FAMILY_HX_CAD", "Lifestyle & History",
                "Family History of Coronary Artery Disease", 0.35, None, "info",
            ))

    return triggers


def evaluate_lipid_fractions(
    ldl: Optional[float] = None,
    hdl: Optional[float] = None,
    triglycerides: Optional[float] = None,
    total_cholesterol: Optional[float] = None,
    t: ClinicalThresholds = DEFAULT_THRESHOLDS,
) -> List[RuleTrigger]:
    """
    Evaluates lipid fractions with specific point weights.
    Includes Total/HDL ratio calculation as an additional risk marker.
    """
    triggers: List[RuleTrigger] = []
    
    # LDL evaluation
    if ldl is not None:
        if ldl >= t.ldl_very_high:
            triggers.append(RuleTrigger(
                "LDL_VERY_HIGH", "Lipid Fractions",
                f"Very High LDL Cholesterol ({ldl:.0f} mg/dL) - 15 points",
                0.15, ldl, "critical", "NCEP ATP III",
            ))
        elif ldl >= t.ldl_high:
            triggers.append(RuleTrigger(
                "LDL_HIGH", "Lipid Fractions",
                f"High LDL Cholesterol ({ldl:.0f} mg/dL) - 10 points",
                0.10, ldl, "warning", "NCEP ATP III",
            ))
        elif ldl >= t.ldl_borderline:
            triggers.append(RuleTrigger(
                "LDL_BORDERLINE", "Lipid Fractions",
                f"Borderline High LDL ({ldl:.0f} mg/dL) - 5 points",
                0.05, ldl, "info", "NCEP ATP III",
            ))
    
    # HDL evaluation
    if hdl is not None:
        if hdl < t.hdl_low:
            triggers.append(RuleTrigger(
                "HDL_LOW", "Lipid Fractions",
                f"Low HDL Cholesterol ({hdl:.0f} mg/dL) - 8 points",
                0.08, hdl, "warning", "NCEP ATP III",
            ))
        elif hdl >= t.hdl_protective:
            triggers.append(RuleTrigger(
                "HDL_PROTECTIVE", "Lipid Fractions",
                f"Protective HDL Level ({hdl:.0f} mg/dL) - 0 points",
                0.0, hdl, "info", "NCEP ATP III",
            ))
    
    # Triglycerides evaluation
    if triglycerides is not None:
        if triglycerides >= t.trig_very_high:
            triggers.append(RuleTrigger(
                "TRIG_VERY_HIGH", "Lipid Fractions",
                f"Very High Triglycerides ({triglycerides:.0f} mg/dL) - 12 points",
                0.12, triglycerides, "critical", "NCEP ATP III",
            ))
        elif triglycerides >= t.trig_high:
            triggers.append(RuleTrigger(
                "TRIG_HIGH", "Lipid Fractions",
                f"High Triglycerides ({triglycerides:.0f} mg/dL) - 8 points",
                0.08, triglycerides, "warning", "NCEP ATP III",
            ))
        elif triglycerides >= t.trig_borderline:
            triggers.append(RuleTrigger(
                "TRIG_BORDERLINE", "Lipid Fractions",
                f"Borderline High Triglycerides ({triglycerides:.0f} mg/dL) - 4 points",
                0.04, triglycerides, "info", "NCEP ATP III",
            ))
    
    # Total/HDL ratio evaluation
    if total_cholesterol is not None and hdl is not None and hdl > 0:
        ratio = total_cholesterol / hdl
        if ratio >= 5.0:
            triggers.append(RuleTrigger(
                "CHOL_HDL_RATIO_HIGH", "Lipid Fractions",
                f"High Total/HDL Ratio ({ratio:.1f}) - 10 points",
                0.10, ratio, "warning", "NCEP ATP III",
            ))
        elif ratio >= 4.0:
            triggers.append(RuleTrigger(
                "CHOL_HDL_RATIO_ELEVATED", "Lipid Fractions",
                f"Elevated Total/HDL Ratio ({ratio:.1f}) - 5 points",
                0.05, ratio, "info", "NCEP ATP III",
            ))
    
    return triggers


def evaluate_cardiorenal_and_labs(
    egfr: Optional[float] = None,
    creatinine: Optional[float] = None,
    bun: Optional[float] = None,
    hba1c: Optional[float] = None,
    hscrp: Optional[float] = None,
    t: ClinicalThresholds = DEFAULT_THRESHOLDS,
) -> List[RuleTrigger]:
    """
    Evaluates cardiorenal function and inflammatory markers with specific point weights.
    """
    triggers: List[RuleTrigger] = []
    
    # eGFR evaluation
    if egfr is not None:
        if egfr < t.egfr_stage5:
            triggers.append(RuleTrigger(
                "CKD_STAGE5", "Cardiorenal & Labs",
                f"CKD Stage 5 / Kidney Failure (eGFR {egfr:.0f}) - 20 points",
                0.20, egfr, "critical", "KDIGO",
            ))
        elif egfr < t.egfr_stage4:
            triggers.append(RuleTrigger(
                "CKD_STAGE4", "Cardiorenal & Labs",
                f"CKD Stage 4, Severely Decreased (eGFR {egfr:.0f}) - 15 points",
                0.15, egfr, "critical", "KDIGO",
            ))
        elif egfr < t.egfr_stage3b:
            triggers.append(RuleTrigger(
                "CKD_STAGE3B", "Cardiorenal & Labs",
                f"CKD Stage 3b, Moderately-Severely Decreased (eGFR {egfr:.0f}) - 10 points",
                0.10, egfr, "warning", "KDIGO",
            ))
        elif egfr < t.egfr_stage3a:
            triggers.append(RuleTrigger(
                "CKD_STAGE3A", "Cardiorenal & Labs",
                f"CKD Stage 3a, Mildly-Moderately Decreased (eGFR {egfr:.0f}) - 5 points",
                0.05, egfr, "info", "KDIGO",
            ))
    
    # Creatinine evaluation
    if creatinine is not None:
        if creatinine >= 2.0:
            triggers.append(RuleTrigger(
                "CREATININE_HIGH", "Cardiorenal & Labs",
                f"Elevated Creatinine ({creatinine:.1f} mg/dL) - 12 points",
                0.12, creatinine, "critical", "KDIGO",
            ))
        elif creatinine >= 1.5:
            triggers.append(RuleTrigger(
                "CREATININE_ELEVATED", "Cardiorenal & Labs",
                f"Mildly Elevated Creatinine ({creatinine:.1f} mg/dL) - 6 points",
                0.06, creatinine, "warning", "KDIGO",
            ))
    
    # BUN evaluation
    if bun is not None:
        if bun >= 30.0:
            triggers.append(RuleTrigger(
                "BUN_HIGH", "Cardiorenal & Labs",
                f"Elevated BUN ({bun:.0f} mg/dL) - 8 points",
                0.08, bun, "warning", "KDIGO",
            ))
    
    # HbA1c evaluation
    if hba1c is not None:
        if hba1c >= t.hba1c_diabetes:
            triggers.append(RuleTrigger(
                "HBA1C_DIABETES", "Cardiorenal & Labs",
                f"HbA1c in Diabetic Range ({hba1c:.1f}%) - 12 points",
                0.12, hba1c, "critical", "ADA",
            ))
        elif hba1c >= t.hba1c_prediabetes:
            triggers.append(RuleTrigger(
                "HBA1C_PREDIABETES", "Cardiorenal & Labs",
                f"HbA1c in Prediabetic Range ({hba1c:.1f}%) - 6 points",
                0.06, hba1c, "warning", "ADA",
            ))
    
    # hs-CRP evaluation
    if hscrp is not None:
        if hscrp >= 3.0:
            triggers.append(RuleTrigger(
                "HSCRP_HIGH", "Cardiorenal & Labs",
                f"High-sensitivity CRP Elevated ({hscrp:.1f} mg/L) - 10 points",
                0.10, hscrp, "warning", "AHA/ACC",
            ))
        elif hscrp >= 1.0:
            triggers.append(RuleTrigger(
                "HSCRP_ELEVATED", "Cardiorenal & Labs",
                f"Mildly Elevated hs-CRP ({hscrp:.1f} mg/L) - 5 points",
                0.05, hscrp, "info", "AHA/ACC",
            ))
    
    return triggers


def evaluate_advanced_ecg_and_stress(
    st_slope: Optional[float] = None,
    num_major_vessels: Optional[float] = None,
    thal: Optional[float] = None,
    t: ClinicalThresholds = DEFAULT_THRESHOLDS,
) -> List[RuleTrigger]:
    """
    Evaluates advanced ECG and stress test parameters with specific point weights.
    """
    triggers: List[RuleTrigger] = []
    
    # ST segment slope evaluation
    slope = _to_float(st_slope)
    if slope == 2.0:
        triggers.append(RuleTrigger(
            "ST_SLOPE_DOWN", "Advanced ECG & Stress",
            "Downsloping ST Segment - 8 points",
            0.08, slope, "warning", "Exercise ECG",
        ))
    elif slope == 1.0:
        triggers.append(RuleTrigger(
            "ST_SLOPE_FLAT", "Advanced ECG & Stress",
            "Flat ST Segment - 4 points",
            0.04, slope, "info", "Exercise ECG",
        ))
    
    # Number of major vessels evaluation
    vessels = _to_float(num_major_vessels)
    if vessels is not None:
        if vessels >= t.vessels_high_risk:
            triggers.append(RuleTrigger(
                "VESSELS_MULTI", "Advanced ECG & Stress",
                f"Multi-Vessel Disease ({int(vessels)} vessels) - 15 points",
                0.15, vessels, "critical", "Fluoroscopy",
            ))
        elif vessels >= 1.0:
            triggers.append(RuleTrigger(
                "VESSELS_SINGLE", "Advanced ECG & Stress",
                f"Single-Vessel Disease ({int(vessels)} vessel) - 8 points",
                0.08, vessels, "warning", "Fluoroscopy",
            ))
    
    # Thalassemia/stress defect evaluation
    thal_v = _to_float(thal)
    if thal_v == 7.0:
        triggers.append(RuleTrigger(
            "THAL_REVERSIBLE_DEFECT", "Advanced ECG & Stress",
            "Thallium Test: Reversible Defect - 12 points",
            0.12, thal_v, "critical", "Thallium stress test",
        ))
    elif thal_v == 6.0:
        triggers.append(RuleTrigger(
            "THAL_FIXED_DEFECT", "Advanced ECG & Stress",
            "Thallium Test: Fixed Defect - 8 points",
            0.08, thal_v, "warning", "Thallium stress test",
        ))
    
    return triggers


def evaluate_metabolic_syndrome(
    data: Dict[str, Any], t: ClinicalThresholds = DEFAULT_THRESHOLDS,
) -> List[RuleTrigger]:
    """
    Evaluates metabolic syndrome using ATP III 5-factor criteria with specific point weights.
    Metabolic syndrome requires 3+ of: elevated BP, elevated triglycerides, 
    low HDL, elevated fasting glucose, central obesity (BMI).
    """
    triggers: List[RuleTrigger] = []
    
    sys_bp = _to_float(data.get("systolic_bp")) or _to_float(data.get("resting_bp"))
    dia_bp = _to_float(data.get("diastolic_bp"))
    trig = _to_float(data.get("triglycerides"))
    hdl = _to_float(data.get("hdl"))
    fbs = _to_float(data.get("fasting_blood_sugar")) or _to_float(data.get("glucose_mgdl"))
    bmi = _to_float(data.get("bmi"))
    
    criteria_count = 0
    
    # Elevated BP criterion
    if (sys_bp is not None and sys_bp >= 130) or (dia_bp is not None and dia_bp >= 85):
        criteria_count += 1
        triggers.append(RuleTrigger(
            "METABOLIC_BP_ELEVATED", "Metabolic Syndrome",
            "Elevated Blood Pressure (≥130/85 mmHg) - 5 points",
            0.05, sys_bp or dia_bp, "info", "ATP III",
        ))
    
    # Elevated triglycerides criterion
    if trig is not None and trig >= 150:
        criteria_count += 1
        triggers.append(RuleTrigger(
            "METABOLIC_TRIG_HIGH", "Metabolic Syndrome",
            f"Elevated Triglycerides (≥150 mg/dL, actual: {trig:.0f}) - 5 points",
            0.05, trig, "info", "ATP III",
        ))
    
    # Low HDL criterion
    if hdl is not None and hdl < 40:
        criteria_count += 1
        triggers.append(RuleTrigger(
            "METABOLIC_HDL_LOW", "Metabolic Syndrome",
            f"Low HDL (<40 mg/dL, actual: {hdl:.0f}) - 5 points",
            0.05, hdl, "info", "ATP III",
        ))
    
    # Elevated fasting glucose criterion
    if fbs is not None and fbs >= 100:
        criteria_count += 1
        triggers.append(RuleTrigger(
            "METABOLIC_GLUCOSE_HIGH", "Metabolic Syndrome",
            f"Elevated Fasting Glucose (≥100 mg/dL, actual: {fbs:.0f}) - 5 points",
            0.05, fbs, "info", "ATP III",
        ))
    
    # Central obesity criterion (BMI ≥30 for ATP III)
    if bmi is not None and bmi >= 30:
        criteria_count += 1
        triggers.append(RuleTrigger(
            "METABOLIC_OBESITY", "Metabolic Syndrome",
            f"Central Obesity (BMI ≥30, actual: {bmi:.1f}) - 5 points",
            0.05, bmi, "info", "ATP III",
        ))
    
    # Metabolic syndrome diagnosis (3+ criteria)
    if criteria_count >= 3:
        triggers.append(RuleTrigger(
            "METABOLIC_SYNDROME", "Metabolic Syndrome",
            f"Metabolic Syndrome Present ({criteria_count}/5 ATP III criteria) - 15 points",
            0.15, criteria_count, "critical", "ATP III",
        ))
    
    return triggers


def evaluate_ascvd_framingham_factors(
    data: Dict[str, Any], t: ClinicalThresholds = DEFAULT_THRESHOLDS,
) -> List[RuleTrigger]:
    """
    Evaluates ASCVD/Framingham 10-year risk factors with sex-specific weighting.
    Factors: age, sex, total cholesterol, HDL, systolic BP, smoking, diabetes, hypertension treatment.
    """
    triggers: List[RuleTrigger] = []
    
    age = _to_float(data.get("age"))
    sex = str(data.get("sex", "")).strip().lower()
    chol = _to_float(data.get("cholesterol"))
    hdl = _to_float(data.get("hdl"))
    sys_bp = _to_float(data.get("systolic_bp")) or _to_float(data.get("resting_bp"))
    smoking = _to_binary_flag(data.get("smoking"))
    diabetes = _to_binary_flag(data.get("diabetes"))
    htn_treatment = _to_binary_flag(data.get("hypertension"))
    
    # Age-related risk (sex-specific)
    if age is not None:
        if sex in ("f", "female"):
            if age >= 65:
                triggers.append(RuleTrigger(
                    "ASCVD_AGE_FEMALE_HIGH", "ASCVD/Framingham",
                    f"Female Age {age:.0f} - High ASCVD Risk Factor - 8 points",
                    0.08, age, "warning", "ACC/AHA",
                ))
            elif age >= 55:
                triggers.append(RuleTrigger(
                    "ASCVD_AGE_FEMALE_MODERATE", "ASCVD/Framingham",
                    f"Female Age {age:.0f} - Moderate ASCVD Risk Factor - 4 points",
                    0.04, age, "info", "ACC/AHA",
                ))
        else:  # male
            if age >= 55:
                triggers.append(RuleTrigger(
                    "ASCVD_AGE_MALE_HIGH", "ASCVD/Framingham",
                    f"Male Age {age:.0f} - High ASCVD Risk Factor - 8 points",
                    0.08, age, "warning", "ACC/AHA",
                ))
            elif age >= 45:
                triggers.append(RuleTrigger(
                    "ASCVD_AGE_MALE_MODERATE", "ASCVD/Framingham",
                    f"Male Age {age:.0f} - Moderate ASCVD Risk Factor - 4 points",
                    0.04, age, "info", "ACC/AHA",
                ))
    
    # Cholesterol interaction with age
    if chol is not None and age is not None:
        chol_age_risk = False
        if sex in ("f", "female"):
            chol_age_risk = chol >= 200 and age >= 55
        else:
            chol_age_risk = chol >= 200 and age >= 45
        
        if chol_age_risk:
            triggers.append(RuleTrigger(
                "ASCVD_CHOL_AGE_INTERACTION", "ASCVD/Framingham",
                f"Age-Cholesterol Interaction Risk - 6 points",
                0.06, chol, "warning", "ACC/AHA",
            ))
    
    # Smoking diabetes interaction
    if smoking is True and diabetes is True:
        triggers.append(RuleTrigger(
            "ASCVD_SMOKING_DIABETES", "ASCVD/Framingham",
            "Smoking + Diabetes Synergy - 10 points",
            0.10, None, "critical", "ACC/AHA",
        ))
    
    # Hypertension treatment consideration
    if htn_treatment is True and sys_bp is not None and sys_bp >= 140:
        triggers.append(RuleTrigger(
            "ASCVD_HTN_TREATED_UNCONTROLLED", "ASCVD/Framingham",
            "Treated but Uncontrolled Hypertension - 8 points",
            0.08, sys_bp, "warning", "ACC/AHA",
        ))
    
    return triggers


# ---------------------------------------------------------------------------
# Multi-parameter synergy / precedence rules
# ---------------------------------------------------------------------------

def evaluate_synergy_rules(
    patient_data: Dict[str, Any],
    sys_bp: Optional[float], dia_bp: Optional[float],
    chol: Optional[float], st_dep: Optional[float],
    cp_type: Optional[float], ex_angina: Any,
    ca: Optional[float], thal: Optional[float],
    egfr: Optional[float],
    t: ClinicalThresholds = DEFAULT_THRESHOLDS,
) -> Tuple[List[RuleTrigger], bool]:
    """
    Detects combinations of findings whose *joint* presence is more
    dangerous than the sum of their parts. Returns (triggers, critical_override).
    """
    triggers: List[RuleTrigger] = []
    critical_override = False
    ang = _to_binary_flag(ex_angina)
    smoking = _to_binary_flag(patient_data.get("smoking"))
    diabetes = _to_binary_flag(patient_data.get("diabetes"))
    bmi = _to_float(patient_data.get("bmi"))
    creatinine = _to_float(patient_data.get("creatinine"))
    st_slope = _to_float(patient_data.get("st_slope"))
    prior_events = patient_data.get("prior_medical_events")
    hscrp = _to_float(patient_data.get("hscrp"))
    ldl = _to_float(patient_data.get("ldl"))

    is_hypertensive_crisis = (sys_bp is not None and sys_bp >= t.bp_crisis_sys) or (
        dia_bp is not None and dia_bp >= t.bp_crisis_dia
    )
    is_severe_ischemia = (st_dep is not None and st_dep >= t.st_dep_severe) and (
        cp_type in (0.0, 1.0) or ang is True
    )
    is_triad_risk = (
        sys_bp is not None and sys_bp >= t.bp_stage2_sys
        and chol is not None and chol >= t.chol_high
        and smoking is True
    )
    is_multivessel_reversible = (ca is not None and ca >= t.vessels_high_risk) and (thal == 7.0)
    is_renal_cardiac = (
        egfr is not None and egfr < t.egfr_stage3a
        and diabetes is True
        and ((sys_bp is not None and sys_bp >= t.bp_stage2_sys) or (dia_bp is not None and dia_bp >= t.bp_stage2_dia))
    )

    if is_hypertensive_crisis:
        triggers.append(RuleTrigger(
            "SYNERGY_CRISIS_BP", "Acute Synergy",
            "CRITICAL: Hypertensive crisis requires immediate clinical intervention",
            0.98, sys_bp, "critical",
        ))
        critical_override = True

    if is_severe_ischemia:
        triggers.append(RuleTrigger(
            "SYNERGY_ACUTE_ISCHEMIA", "Acute Synergy",
            "CRITICAL: Severe ST depression combined with active angina",
            0.95, st_dep, "critical",
        ))
        critical_override = True

    if is_multivessel_reversible:
        triggers.append(RuleTrigger(
            "SYNERGY_MULTIVESSEL_ISCHEMIA", "Acute Synergy",
            "CRITICAL: Multi-vessel disease with reversible perfusion defect — inducible ischemia across multiple territories",
            0.92, ca, "critical",
        ))
        critical_override = True

    if is_triad_risk:
        triggers.append(RuleTrigger(
            "SYNERGY_TRIAD", "Cardiovascular Triad",
            "HIGH SYNERGY: Stage 2 hypertension + high cholesterol + active smoking",
            0.85, None, "critical",
        ))

    if is_renal_cardiac:
        triggers.append(RuleTrigger(
            "SYNERGY_RENAL_CARDIAC", "Renal-Cardiac Synergy",
            "HIGH SYNERGY: Reduced renal function + diabetes + hypertension — compounding cardiovascular-renal risk",
            0.80, egfr, "critical",
        ))

    # NEW SYNERGY RULES
    
    # SYNERGY_CARDIORENAL_METABOLIC — Diabetes + Hypertension + (Impaired eGFR or High Creatinine or Severe BMI)
    is_cardiorenal_metabolic = (
        diabetes is True
        and ((sys_bp is not None and sys_bp >= t.bp_stage2_sys) or (dia_bp is not None and dia_bp >= t.bp_stage2_dia))
        and ((egfr is not None and egfr < t.egfr_stage3a) or (creatinine is not None and creatinine >= 1.5) or (bmi is not None and bmi >= t.bmi_obese_2))
    )
    if is_cardiorenal_metabolic:
        triggers.append(RuleTrigger(
            "SYNERGY_CARDIORENAL_METABOLIC", "Multi-System Synergy",
            "CRITICAL: Diabetes + Hypertension + Renal/Metabolic Dysfunction — Cardiorenal Metabolic Syndrome",
            0.88, None, "critical",
        ))
        critical_override = True

    # SYNERGY_MULTI_VESSEL_ISCHEMIA — num_major_vessels ≥ 2 + Thalassemia defect + ST depression
    is_multi_vessel_ischemia = (
        ca is not None and ca >= t.vessels_high_risk
        and thal == 7.0
        and st_dep is not None and st_dep >= t.st_dep_moderate
    )
    if is_multi_vessel_ischemia:
        triggers.append(RuleTrigger(
            "SYNERGY_MULTI_VESSEL_ISCHEMIA", "Multi-System Synergy",
            "CRITICAL: Multi-vessel disease + reversible defect + ST depression — extensive ischemia",
            0.90, ca, "critical",
        ))
        critical_override = True

    # SYNERGY_ISCHEMIC_STRESS_DEFICIT — Exercise angina + Downsloping ST segment + Chronotropic reserve deficiency
    hr = _to_float(patient_data.get("max_heart_rate"))
    age = _to_float(patient_data.get("age"))
    chronotropic_deficiency = False
    if hr is not None and age is not None:
        expected_max = max(100.0, 220.0 - age)
        ratio = hr / expected_max
        chronotropic_deficiency = ratio < t.hr_reserve_low_ratio
    
    is_ischemic_stress_deficit = (
        ang is True
        and st_slope == 2.0
        and chronotropic_deficiency
    )
    if is_ischemic_stress_deficit:
        triggers.append(RuleTrigger(
            "SYNERGY_ISCHEMIC_STRESS_DEFICIT", "Multi-System Synergy",
            "HIGH SYNERGY: Exercise angina + downsloping ST + chronotropic incompetence — high-risk stress pattern",
            0.82, None, "critical",
        ))

    # SYNERGY_HYPERTENSIVE_END_ORGAN — Hypertensive crisis/Stage 2 BP + Prior cardiac event/ischemia
    is_hypertensive_end_organ = (
        ((sys_bp is not None and sys_bp >= t.bp_stage2_sys) or (dia_bp is not None and dia_bp >= t.bp_stage2_dia))
        and prior_events is not None
    )
    if is_hypertensive_end_organ:
        triggers.append(RuleTrigger(
            "SYNERGY_HYPERTENSIVE_END_ORGAN", "Multi-System Synergy",
            "HIGH SYNERGY: Stage 2 hypertension + prior cardiac events — end-organ damage risk",
            0.78, None, "critical",
        ))

    # SYNERGY_ATHEROSCLEROTIC_INFLAMMATION — Elevated hs-CRP + High LDL/Cholesterol + Active smoking
    is_atherosclerotic_inflammation = (
        hscrp is not None and hscrp >= 2.0
        and ((ldl is not None and ldl >= t.ldl_high) or (chol is not None and chol >= t.chol_high))
        and smoking is True
    )
    if is_atherosclerotic_inflammation:
        triggers.append(RuleTrigger(
            "SYNERGY_ATHEROSCLEROTIC_INFLAMMATION", "Multi-System Synergy",
            "HIGH SYNERGY: Elevated hs-CRP + dyslipidemia + smoking — inflammatory atherosclerotic risk",
            0.75, None, "critical",
        ))

    return triggers, critical_override


def generate_clinical_recommendations(
    triggered_rules: List[RuleTrigger],
    risk_tier: RiskTier,
    patient_data: Dict[str, Any],
) -> List[str]:
    """
    Generates clinical recommendations based on triggered rules and risk tier.
    Provides actionable medical advice for emergency intervention, cardiology referral,
    medication management, and lifestyle interventions.
    """
    recommendations: List[str] = []
    rule_codes = {r.rule_code for r in triggered_rules}
    
    # Emergency/Critical interventions
    critical_rules = {
        "BP_CRISIS", "SYNERGY_CRISIS_BP", "SYNERGY_ACUTE_ISCHEMIA",
        "SYNERGY_MULTIVESSEL_ISCHEMIA", "SYNERGY_CARDIORENAL_METABOLIC",
        "SYNERGY_MULTI_VESSEL_ISCHEMIA", "ST_DEP_SEVERE", "CKD_STAGE5", "CKD_STAGE4"
    }
    
    if critical_rules.intersection(rule_codes):
        recommendations.append("EMERGENCY: Immediate clinical intervention required - consider hospital admission or urgent cardiology consultation.")
        recommendations.append("Obtain immediate 12-lead ECG, cardiac biomarkers, and consult interventional cardiology if indicated.")
    
    # Cardiology referrals
    cardiology_rules = {
        "ST_DEP_MODERATE", "ST_DEP_SEVERE", "VESSELS_MULTI", "VESSELS_SINGLE",
        "THAL_REVERSIBLE_DEFECT", "THAL_FIXED_DEFECT", "EXERCISE_ANGINA",
        "CHEST_PAIN_ANGINA", "SYNERGY_ISCHEMIC_STRESS_DEFICIT"
    }
    
    if cardiology_rules.intersection(rule_codes):
        recommendations.append("Cardiology referral recommended for comprehensive cardiac evaluation and stress testing.")
        recommendations.append("Consider coronary angiography if non-invasive testing indicates high-risk ischemia.")
    
    # Medication recommendations
    if "HYPERTENSION_DX" in rule_codes or "BP_STAGE2" in rule_codes or "BP_STAGE1" in rule_codes:
        recommendations.append("Initiate or optimize antihypertensive therapy - target BP <130/80 mmHg.")
        recommendations.append("Consider ACE inhibitors/ARBs for patients with diabetes or CKD for renal protection.")
    
    if {"LDL_HIGH", "LDL_VERY_HIGH", "CHOL_HIGH", "CHOL_VERY_HIGH"}.intersection(rule_codes):
        recommendations.append("Initiate statin therapy for primary/secondary prevention of atherosclerotic disease.")
        recommendations.append("Consider high-intensity statin if LDL ≥190 mg/dL or 10-year ASCVD risk ≥20%.")
    
    if "DIABETES_DX" in rule_codes or "HBA1C_DIABETES" in rule_codes:
        recommendations.append("Optimize glycemic control with target HbA1c <7% to reduce cardiovascular complications.")
        recommendations.append("Consider SGLT2 inhibitors or GLP-1 agonists for patients with diabetes and established CVD.")
    
    if {"CKD_STAGE3A", "CKD_STAGE3B", "CKD_STAGE4", "CKD_STAGE5"}.intersection(rule_codes):
        recommendations.append("Nephrology consultation recommended for CKD management and renal preservation.")
        recommendations.append("Avoid nephrotoxic medications and monitor renal function regularly.")
    
    # Lifestyle interventions
    if "SMOKING" in rule_codes:
        recommendations.append("Smoking cessation is critical - offer counseling, nicotine replacement therapy, and pharmacologic support.")
    
    if {"BMI_OBESE_1", "BMI_OBESE_2", "BMI_OBESE_3"}.intersection(rule_codes):
        recommendations.append("Weight management intervention recommended - target 5-10% weight loss for clinical benefit.")
        recommendations.append("Refer to registered dietitian for structured weight loss program.")
    
    if "METABOLIC_SYNDROME" in rule_codes:
        recommendations.append("Comprehensive lifestyle intervention for metabolic syndrome - DASH diet, regular exercise, and weight management.")
        recommendations.append("Address all ATP III criteria: BP, lipids, glucose, and obesity simultaneously.")
    
    if {"SEDENTARY_LIFESTYLE", "HR_CHRONOTROPIC_INCOMPETENCE"}.intersection(rule_codes):
        recommendations.append("Prescribe structured exercise program - aim for 150 minutes moderate-intensity aerobic activity weekly.")
        recommendations.append("Consider cardiac rehabilitation if history of cardiac events or reduced exercise capacity.")
    
    # Risk-specific recommendations
    if risk_tier == RiskTier.CRITICAL:
        recommendations.append("CRITICAL RISK: Patient requires immediate risk stratification and likely intervention.")
        recommendations.append("Consider admission to monitored bed if acute coronary syndrome suspected.")
    elif risk_tier == RiskTier.HIGH:
        recommendations.append("HIGH RISK: Schedule cardiology evaluation within 1-2 weeks for comprehensive workup.")
        recommendations.append("Aggressive risk factor modification required - medication adherence and lifestyle changes.")
    elif risk_tier == RiskTier.MODERATE:
        recommendations.append("MODERATE RISK: Follow-up within 1 month for risk reassessment and lifestyle counseling.")
        recommendations.append("Focus on primary prevention through diet, exercise, and risk factor monitoring.")
    else:
        recommendations.append("LOW RISK: Continue current healthy lifestyle and maintain regular health screenings.")
        recommendations.append("Reassess cardiovascular risk annually or sooner if symptoms develop.")
    
    # Special considerations
    if "FAMILY_HX_PREMATURE_CAD" in rule_codes:
        recommendations.append("Family history of premature CAD - initiate screening 10 years earlier than first-degree relative's event.")
    
    if "ALCOHOL_USE" in rule_codes:
        recommendations.append("Alcohol moderation recommended - limit to ≤1 drink/day for women, ≤2 drinks/day for men.")
    
    if "PRIOR_EVENTS" in rule_codes:
        recommendations.append("Secondary prevention essential - ensure adherence to guideline-directed medical therapy.")
        recommendations.append("Consider dual antiplatelet therapy if recent coronary intervention or acute coronary syndrome.")
    
    return recommendations


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def _noisy_or(scores: List[float]) -> float:
    """
    Combines roughly-independent risk scores into one probability-like
    value via noisy-OR: combined = 1 - Π(1 - s_i).

    This replaces v1's "top-4 weighted average", which had two problems:
    it ignored everything past the 4th-highest trigger, and its 0.70/0.30
    split between the top rule and the rest was an arbitrary constant with
    no clinical basis. Noisy-OR uses every triggered rule, treats each as
    independent evidence pushing risk up, and saturates gracefully instead
    of being capped by a fixed formula shape.
    """
    if not scores:
        return 0.0
    survival = 1.0
    for s in scores:
        s_clamped = min(max(s, 0.0), 0.995)
        survival *= (1.0 - s_clamped)
    return min(0.99, 1.0 - survival)


EXPECTED_FIELDS = [
    "systolic_bp", "resting_bp", "diastolic_bp", "age", "sex", "cholesterol",
    "ldl", "hdl", "triglycerides", "fasting_blood_sugar", "glucose_mgdl",
    "hba1c", "diabetes", "st_depression", "st_slope", "resting_ecg",
    "chest_pain_type", "exercise_angina", "bmi", "max_heart_rate",
    "ca", "thal", "creatinine", "egfr", "smoking", "hypertension",
    "alcohol", "sedentary", "prior_medical_events", "family_history_cad",
]


def _data_completeness(patient_data: Dict[str, Any]) -> float:
    provided = sum(1 for f in EXPECTED_FIELDS if patient_data.get(f) is not None)
    return round(provided / len(EXPECTED_FIELDS), 3)


# ---------------------------------------------------------------------------
# Master rule engine execution
# ---------------------------------------------------------------------------

def calculate_rule_based_risk(
    patient_data: Dict[str, Any], t: ClinicalThresholds = DEFAULT_THRESHOLDS,
) -> Dict[str, Any]:
    """
    Executes the deterministic clinical rule engine on patient data.

    Returns a dict with (v1-compatible keys first, new keys appended):
        risk_score, risk_label, risk_category, triggered_rules,
        top_contributions, scoring_method,
        critical_override, data_completeness, warnings, rules_version
    """
    sys_bp = _to_float(patient_data.get("systolic_bp")) or _to_float(patient_data.get("resting_bp"))
    dia_bp = _to_float(patient_data.get("diastolic_bp"))
    age = _to_float(patient_data.get("age"))
    chol = _to_float(patient_data.get("cholesterol"))
    ldl = _to_float(patient_data.get("ldl"))
    hdl = _to_float(patient_data.get("hdl"))
    trig = _to_float(patient_data.get("triglycerides"))
    st_dep = _to_float(patient_data.get("st_depression"))
    cp_type = _to_float(patient_data.get("chest_pain_type"))
    ex_ang = patient_data.get("exercise_angina")
    bmi = _to_float(patient_data.get("bmi"))
    hr = _to_float(patient_data.get("max_heart_rate"))
    ca = _to_float(patient_data.get("ca"))
    thal = _to_float(patient_data.get("thal"))
    egfr = _to_float(patient_data.get("egfr"))
    creatinine = _to_float(patient_data.get("creatinine"))

    all_triggers: List[RuleTrigger] = []
    all_triggers += evaluate_blood_pressure(sys_bp, dia_bp, t)
    all_triggers += evaluate_lipid_panel(chol, ldl, hdl, trig, t)
    all_triggers += evaluate_lipid_fractions(ldl, hdl, trig, chol, t)
    all_triggers += evaluate_glucose_diabetes(
        patient_data.get("fasting_blood_sugar"),
        patient_data.get("glucose_mgdl"),
        patient_data.get("hba1c"),
        patient_data.get("diabetes"),
        t,
    )
    all_triggers += evaluate_cardiorenal_and_labs(
        egfr, creatinine, patient_data.get("bun"), patient_data.get("hba1c"), patient_data.get("hscrp"), t
    )
    all_triggers += evaluate_ecg(st_dep, patient_data.get("st_slope"), patient_data.get("resting_ecg"), t)
    all_triggers += evaluate_advanced_ecg_and_stress(patient_data.get("st_slope"), ca, thal, t)
    all_triggers += evaluate_chest_pain_and_angina(cp_type, ex_ang)
    all_triggers += evaluate_bmi(bmi, t)
    all_triggers += evaluate_heart_rate_reserve(hr, age, t)
    all_triggers += evaluate_age_sex(age, patient_data.get("sex"), t)
    all_triggers += evaluate_vessels_and_thal(ca, thal, t)
    all_triggers += evaluate_renal_function(creatinine, egfr, t)
    all_triggers += evaluate_lifestyle_and_history(patient_data, t)
    all_triggers += evaluate_metabolic_syndrome(patient_data, t)
    all_triggers += evaluate_ascvd_framingham_factors(patient_data, t)

    synergy_triggers, critical_override = evaluate_synergy_rules(
        patient_data, sys_bp, dia_bp, chol, st_dep, cp_type, ex_ang, ca, thal, egfr, t,
    )
    all_triggers += synergy_triggers

    # A finding can be reported by overlapping legacy and new evaluators.
    # Display each finding, but score a rule code only once at its highest
    # documented point weight; otherwise LDL/ECG/renal abnormalities are
    # double-counted and ordinary profiles can be classified as Critical.
    scoring_by_code: Dict[str, RuleTrigger] = {}
    for rule in all_triggers:
        # Scores at or below 0.10 are informational/protective findings.
        # They are returned for auditability but must never inflate a risk band.
        if rule.rule_score <= 0.10:
            continue
        previous = scoring_by_code.get(rule.rule_code)
        if previous is None or points_for_rule(rule) > points_for_rule(previous):
            scoring_by_code[rule.rule_code] = rule
    scoring_triggers = list(scoring_by_code.values())
    total_points = sum(points_for_rule(rule) for rule in scoring_triggers)

    risk_band, tier = risk_band_for_points(total_points)
    # Keep the 0..1 response contract, while making the value a transparent
    # normalized point total rather than a compounded pseudo-probability.
    final_score = 0.10 if total_points == 0 else round(min(total_points / 70.0, 0.99), 4)
    if critical_override:
        tier = RiskTier.CRITICAL
        risk_band = "Critical"
        final_score = max(final_score, 0.80)

    label, color = TIER_META[tier]
    pct = round(final_score * 100, 1)

    completeness = _data_completeness(patient_data)
    warnings: List[str] = []
    if completeness < 0.25:
        warnings.append(
            "Very limited data was provided (fewer than 25% of expected clinical "
            "fields). Treat this risk score as low-confidence."
        )
    elif completeness < 0.5:
        warnings.append(
            "Less than half of expected clinical fields were provided; "
            "the risk score may not reflect the full clinical picture."
        )

    # Sort all triggers (including informational ones) by score, descending,
    # for transparent, auditable output.
    all_triggers.sort(key=lambda r: r.rule_score, reverse=True)
    triggered_rules = [r.to_dict() for r in all_triggers]

    # Point shares make the explanation reconstruct the exact score.
    top_contributions = []
    total_evidence = total_points or 1
    for r in sorted(scoring_triggers, key=points_for_rule, reverse=True):
        top_contributions.append({
            "feature": r.rule_code.lower(),
            "value": r.value,
            "rule_score": round(r.rule_score, 4),
            "points": points_for_rule(r),
            "weight": round(points_for_rule(r) / total_evidence, 4),
            "shap_value": round(points_for_rule(r) / 70.0, 4),
            "impact": "high impact" if points_for_rule(r) >= 12 else ("moderate impact" if points_for_rule(r) >= 6 else "low impact"),
            "direction": "increases risk",
            "description": r.description,
        })

    # Generate clinical recommendations based on triggered rules and risk tier
    clinical_recommendations = generate_clinical_recommendations(all_triggers, tier, patient_data)

    return {
        # --- v1-compatible keys ---
        "risk_score": final_score,
        "risk_label": label,
        "risk_band": risk_band,
        "total_points": total_points,
        "point_breakdown": [
            {"rule_code": r.rule_code, "points": points_for_rule(r)}
            for r in sorted(scoring_triggers, key=points_for_rule, reverse=True)
        ],
        "risk_category": {
            "label": label,
            "percentage": pct,
            "tier": tier.value,
            "color": color,
        },
        "triggered_rules": triggered_rules,
        "top_contributions": top_contributions,
        "scoring_method": "deterministic_clinical_rule_engine",
        # --- new keys ---
        "critical_override": critical_override,
        "data_completeness": completeness,
        "warnings": warnings,
        "rules_version": RULES_VERSION,
        "clinical_recommendations": clinical_recommendations,
    }


# Backward compatibility helper
def calculate_equal_weighted_risk(patient_data: Dict[str, Any], feature_names: List[str] = None) -> Dict[str, Any]:
    """Alias for calculate_rule_based_risk to maintain full compatibility."""
    return calculate_rule_based_risk(patient_data)


if __name__ == "__main__":
    import json

    demo_patient = {
        "systolic_bp": 190, "diastolic_bp": 100, "age": 62, "sex": "male",
        "cholesterol": 265, "hdl": 32, "triglycerides": 220,
        "fasting_blood_sugar": 1, "st_depression": 1.5, "chest_pain_type": 0,
        "exercise_angina": 1, "bmi": 31.2, "max_heart_rate": 118,
        "ca": 2, "thal": 7, "egfr": 55, "smoking": 1, "hypertension": 1,
    }
    print(json.dumps(calculate_rule_based_risk(demo_patient), indent=2))
