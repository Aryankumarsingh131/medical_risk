"""
src/schema_mapping.py
---------------------
Expanded canonical clinical schema supporting comprehensive multi-domain risk indicators:
  - Demographics & Vitals: age, sex, resting_bp, temperature, max_heart_rate, bmi
  - Labs & Biometrics: cholesterol, fasting_blood_sugar, st_depression
  - Lifestyle Factors: smoking, alcohol, drug
  - Neurological & Motor Signs: speech, movement
  - Medical History & Regimen: active_diagnosis, prior_medical_events, current_medication_list
  - Symptom & Disease Flags: chest_pain_type, exercise_angina, hypertension, diabetes
  - Target: target_risk (1 = high risk/event, 0 = low risk/absence)

Provides dataset-specific column mappings, unit transformations, encoding
normalizations, and `load_and_standardize(dataset_name)`.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from typing import Callable, Dict, List, Optional, Any
import numpy as np
import pandas as pd


RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"

# ---------------------------------------------------------------------------
# CANONICAL SCHEMA DEFINITION
# ---------------------------------------------------------------------------
CANONICAL_COLUMNS: List[str] = [
    # Demographics & Vitals
    "age",
    "sex",
    "resting_bp",
    "temperature",
    "max_heart_rate",
    "bmi",
    # Labs & Biometrics
    "cholesterol",
    "fasting_blood_sugar",
    "st_depression",
    # Lifestyle & Habits
    "smoking",
    "alcohol",
    "drug",
    # Neurological & Motor
    "speech",
    "movement",
    # History & Medication
    "active_diagnosis",
    "prior_medical_events",
    "current_medication_list",
    # Clinical Signs & Comorbidities
    "chest_pain_type",
    "exercise_angina",
    "hypertension",
    "diabetes",
    # Unified Target
    "target_risk",
]


# ---------------------------------------------------------------------------
# TRANSFORMATION HELPERS
# ---------------------------------------------------------------------------
def _map_sex(val: Any) -> float:
    if pd.isna(val):
        return np.nan
    v_str = str(val).strip().lower()
    if v_str in ["1", "1.0", "m", "male"]:
        return 1.0
    if v_str in ["0", "0.0", "f", "female"]:
        return 0.0
    return np.nan


def _map_binary_target(val: Any) -> float:
    if pd.isna(val):
        return np.nan
    v_str = str(val).strip().lower()
    if v_str in ["1", "1.0", "presence", "yes", "true", "high"]:
        return 1.0
    if v_str in ["0", "0.0", "absence", "no", "false", "low"]:
        return 0.0
    try:
        num = float(val)
        return 1.0 if num > 0 else 0.0
    except Exception:
        return np.nan


def _map_smoking_str(val: Any) -> float:
    if pd.isna(val):
        return np.nan
    v_str = str(val).strip().lower()
    if v_str in ["current", "ever", "former", "not current", "1", "1.0", "yes"]:
        return 1.0
    if v_str in ["never", "no info", "0", "0.0", "no"]:
        return 0.0
    return np.nan


def _map_alcohol(val: Any) -> float:
    if pd.isna(val):
        return np.nan
    v_str = str(val).strip().lower()
    if v_str in ["moderate", "heavy", "yes", "1", "1.0"]:
        return 1.0
    if v_str in ["none", "never", "no", "0", "0.0"]:
        return 0.0
    try:
        return float(val)
    except Exception:
        return np.nan


def _map_activity_movement(val: Any) -> float:
    if pd.isna(val):
        return np.nan
    v_str = str(val).strip().lower()
    if v_str in ["active", "high", "moderate"]:
        return 1.0
    if v_str in ["sedentary", "low", "inactive", "bedridden"]:
        return 0.0
    try:
        return float(val)
    except Exception:
        return np.nan


# ---------------------------------------------------------------------------
# DATASET CONFIGURATIONS & COLUMN TRANSLATIONS
# ---------------------------------------------------------------------------
DATASET_CONFIGS: Dict[str, Dict[str, Any]] = {
    "framingham_heart_study.csv": {
        "delimiter": ",",
        "column_map": {
            "age": "age",
            "male": "sex",
            "sysBP": "resting_bp",
            "totChol": "cholesterol",
            "glucose": "fasting_blood_sugar",
            "heartRate": "max_heart_rate",
            "BMI": "bmi",
            "currentSmoker": "smoking",
            "prevalentHyp": "hypertension",
            "diabetes": "diabetes",
            "prevalentStroke": "prior_medical_events",
            "BPMeds": "current_medication_list",
            "TenYearCHD": "target_risk",
        },
        "value_transforms": {
            "sex": _map_sex,
            "fasting_blood_sugar": lambda v: np.where(pd.isna(v), np.nan, (pd.to_numeric(v, errors="coerce") > 120).astype(float)),
            "target_risk": _map_binary_target,
            "smoking": lambda v: pd.to_numeric(v, errors="coerce"),
            "hypertension": lambda v: pd.to_numeric(v, errors="coerce"),
            "diabetes": lambda v: pd.to_numeric(v, errors="coerce"),
            "prior_medical_events": lambda v: pd.to_numeric(v, errors="coerce"),
            "current_medication_list": lambda v: pd.to_numeric(v, errors="coerce"),
        },
    },
    "Heart_disease_cleveland_new.csv": {
        "delimiter": ",",
        "column_map": {
            "age": "age",
            "sex": "sex",
            "trestbps": "resting_bp",
            "chol": "cholesterol",
            "fbs": "fasting_blood_sugar",
            "thalach": "max_heart_rate",
            "cp": "chest_pain_type",
            "exang": "exercise_angina",
            "oldpeak": "st_depression",
            "target": "target_risk",
        },
        "value_transforms": {
            "sex": _map_sex,
            "fasting_blood_sugar": lambda v: pd.to_numeric(v, errors="coerce"),
            "exercise_angina": lambda v: pd.to_numeric(v, errors="coerce"),
            "target_risk": _map_binary_target,
        },
    },
    "Heart_Disease_Prediction.csv": {
        "delimiter": ",",
        "column_map": {
            "Age": "age",
            "Sex": "sex",
            "BP": "resting_bp",
            "Cholesterol": "cholesterol",
            "FBS over 120": "fasting_blood_sugar",
            "Max HR": "max_heart_rate",
            "Chest pain type": "chest_pain_type",
            "Exercise angina": "exercise_angina",
            "ST depression": "st_depression",
            "Heart Disease": "target_risk",
        },
        "value_transforms": {
            "sex": _map_sex,
            "fasting_blood_sugar": lambda v: pd.to_numeric(v, errors="coerce"),
            "exercise_angina": lambda v: pd.to_numeric(v, errors="coerce"),
            "target_risk": _map_binary_target,
        },
    },
    "heart_failure_clinical_records_dataset.csv": {
        "delimiter": ",",
        "column_map": {
            "age": "age",
            "sex": "sex",
            "smoking": "smoking",
            "high_blood_pressure": "hypertension",
            "diabetes": "diabetes",
            "DEATH_EVENT": "target_risk",
        },
        "value_transforms": {
            "sex": _map_sex,
            "smoking": lambda v: pd.to_numeric(v, errors="coerce"),
            "hypertension": lambda v: pd.to_numeric(v, errors="coerce"),
            "diabetes": lambda v: pd.to_numeric(v, errors="coerce"),
            "target_risk": _map_binary_target,
        },
    },
    "cardiovascular.txt": {
        "delimiter": ";",
        "column_map": {
            "age": "age",
            "sbp": "resting_bp",
            "tobacco": "smoking",
            "alcohol": "alcohol",
            "obesity": "bmi",
            "chd": "target_risk",
        },
        "value_transforms": {
            "smoking": lambda v: np.where(pd.isna(v), np.nan, (pd.to_numeric(v, errors="coerce") > 0).astype(float)),
            "alcohol": lambda v: pd.to_numeric(v, errors="coerce"),
            "target_risk": _map_binary_target,
        },
    },
    "diabetes_prediction_dataset.csv": {
        "delimiter": ",",
        "column_map": {
            "age": "age",
            "gender": "sex",
            "bmi": "bmi",
            "smoking_history": "smoking",
            "blood_glucose_level": "fasting_blood_sugar",
            "hypertension": "hypertension",
            "diabetes": "diabetes",
            "heart_disease": "target_risk",
        },
        "value_transforms": {
            "sex": _map_sex,
            "smoking": _map_smoking_str,
            "fasting_blood_sugar": lambda v: np.where(pd.isna(v), np.nan, (pd.to_numeric(v, errors="coerce") > 120).astype(float)),
            "hypertension": lambda v: pd.to_numeric(v, errors="coerce"),
            "diabetes": lambda v: pd.to_numeric(v, errors="coerce"),
            "target_risk": _map_binary_target,
        },
    },
    "stroke_risk_dataset.csv": {
        "delimiter": ",",
        "column_map": {
            "Age": "age",
            "High Blood Pressure": "hypertension",
            "Chest Pain": "chest_pain_type",
            "Fatigue & Weakness": "movement",
            "At Risk (Binary)": "target_risk",
        },
        "value_transforms": {
            "hypertension": lambda v: pd.to_numeric(v, errors="coerce"),
            "movement": lambda v: pd.to_numeric(v, errors="coerce"),
            "target_risk": _map_binary_target,
        },
    },
    "The_Cancer_data_1500_V2.csv": {
        "delimiter": ",",
        "column_map": {
            "Age": "age",
            "Gender": "sex",
            "BMI": "bmi",
            "Smoking": "smoking",
            "AlcoholIntake": "alcohol",
            "PhysicalActivity": "movement",
            "CancerHistory": "prior_medical_events",
            "Diagnosis": "target_risk",
        },
        "value_transforms": {
            "sex": _map_sex,
            "smoking": lambda v: pd.to_numeric(v, errors="coerce"),
            "alcohol": lambda v: pd.to_numeric(v, errors="coerce"),
            "movement": lambda v: pd.to_numeric(v, errors="coerce"),
            "prior_medical_events": lambda v: pd.to_numeric(v, errors="coerce"),
            "target_risk": _map_binary_target,
        },
    },
    "osteoporosis.csv": {
        "delimiter": ",",
        "column_map": {
            "Age": "age",
            "Gender": "sex",
            "Smoking": "smoking",
            "Alcohol Consumption": "alcohol",
            "Physical Activity": "movement",
            "Medical Conditions": "active_diagnosis",
            "Prior Fractures": "prior_medical_events",
            "Medications": "current_medication_list",
            "Osteoporosis": "target_risk",
        },
        "value_transforms": {
            "sex": _map_sex,
            "smoking": lambda v: (v.astype(str).str.lower() == "yes").astype(float),
            "alcohol": _map_alcohol,
            "movement": _map_activity_movement,
            "prior_medical_events": lambda v: (v.astype(str).str.lower() == "yes").astype(float),
            "current_medication_list": lambda v: (v.astype(str).str.lower() == "yes").astype(float),
            "active_diagnosis": lambda v: (v.astype(str).str.lower() == "yes").astype(float),
            "target_risk": _map_binary_target,
        },
    },
    "Health_Risk_Dataset.csv": {
        "delimiter": ",",
        "column_map": {
            "Age": "age",
            "Gender": "sex",
            "Systolic_BP": "resting_bp",
            "Cholesterol": "cholesterol",
            "BMI": "bmi",
            "Smoking": "smoking",
            "Risk_Level": "target_risk",
        },
        "value_transforms": {
            "sex": _map_sex,
            "smoking": lambda v: pd.to_numeric(v, errors="coerce"),
            "target_risk": lambda v: (v.astype(str).str.lower().isin(["high", "medium", "1", "2"])).astype(float),
        },
    },
}


# ---------------------------------------------------------------------------
# CORE STANDARDIZATION FUNCTION
# ---------------------------------------------------------------------------
def load_and_standardize(
    dataset_name: str,
    raw_dir: Path = RAW_DIR,
) -> pd.DataFrame:
    """
    Load a raw dataset by filename, map columns and units to the canonical
    schema, and return a standardized DataFrame with all CANONICAL_COLUMNS.
    Any canonical column absent in the source is populated with NaN.
    """
    filepath = raw_dir / dataset_name
    if not filepath.exists():
        raise FileNotFoundError(f"Dataset '{dataset_name}' not found in {raw_dir}")

    config = DATASET_CONFIGS.get(dataset_name)
    delimiter = config.get("delimiter", ",") if config else ","

    try:
        df_raw = pd.read_csv(filepath, sep=delimiter)
        if len(df_raw.columns) == 1 and ";" in df_raw.columns[0]:
            df_raw = pd.read_csv(filepath, sep=";")
    except Exception:
        df_raw = pd.read_csv(filepath, sep=None, engine="python")

    standardized_df = pd.DataFrame(index=df_raw.index)

    if config:
        col_map = config.get("column_map", {})
        val_transforms = config.get("value_transforms", {})

        for orig_col, canon_col in col_map.items():
            if orig_col in df_raw.columns:
                series = df_raw[orig_col].copy()
                if canon_col in val_transforms:
                    transform_fn = val_transforms[canon_col]
                    if callable(transform_fn):
                        try:
                            series = transform_fn(series)
                        except Exception:
                            series = series.apply(transform_fn)
                standardized_df[canon_col] = pd.to_numeric(series, errors="coerce")

    for col in CANONICAL_COLUMNS:
        if col not in standardized_df.columns:
            standardized_df[col] = np.nan
        else:
            standardized_df[col] = pd.to_numeric(standardized_df[col], errors="coerce")

    standardized_df = standardized_df[CANONICAL_COLUMNS]
    return standardized_df


def standardize_all(
    raw_dir: Path = RAW_DIR,
    output_dir: Path = PROCESSED_DIR,
) -> Dict[str, pd.DataFrame]:
    """Process all configured datasets and save mapped files to output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)
    results = {}

    for dataset_name in DATASET_CONFIGS.keys():
        filepath = raw_dir / dataset_name
        if not filepath.exists():
            continue
        print(f"[schema_mapping] Standardizing: {dataset_name}...")
        df_std = load_and_standardize(dataset_name, raw_dir=raw_dir)
        clean_name = dataset_name.replace(".csv", "").replace(".txt", "")
        out_path = output_dir / f"mapped_{clean_name}.csv"
        df_std.to_csv(out_path, index=False)
        print(f"  -> Saved {out_path.name} | Shape: {df_std.shape} | Valid targets: {df_std['target_risk'].dropna().shape[0]}")
        results[dataset_name] = df_std

    return results


if __name__ == "__main__":
    standardize_all()
