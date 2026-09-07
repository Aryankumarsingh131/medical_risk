"""
src/preprocessing.py
--------------------
Data cleaning, group-aware imputation, outlier handling, and pipeline serialization.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from typing import Dict, List, Optional, Tuple, Any
import joblib
import numpy as np
import pandas as pd


PROCESSED_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"
MODELS_DIR = Path(__file__).resolve().parents[1] / "models"
TARGET_COL = "target_risk"
SOURCE_COL = "source_dataset"

CONTINUOUS_NUMERIC_COLS = [
    "age",
    "resting_bp",
    "temperature",
    "max_heart_rate",
    "bmi",
    "cholesterol",
    "st_depression",
]

CATEGORICAL_BINARY_COLS = [
    "sex",
    "fasting_blood_sugar",
    "smoking",
    "alcohol",
    "drug",
    "speech",
    "movement",
    "active_diagnosis",
    "prior_medical_events",
    "current_medication_list",
    "chest_pain_type",
    "exercise_angina",
    "hypertension",
    "diabetes",
]


class ClinicalDataPreprocessor:
    """
    Stateful preprocessor that computes group-specific and global imputation
    statistics, stores IQR outlier bounds, and transforms clinical DataFrames.
    """

    def __init__(self) -> None:
        self.group_medians: Dict[str, Dict[str, float]] = {}
        self.group_modes: Dict[str, Dict[str, float]] = {}
        self.global_medians: Dict[str, float] = {}
        self.global_modes: Dict[str, float] = {}
        self.iqr_bounds: Dict[str, Tuple[float, float]] = {}
        self.feature_names: List[str] = []

    def fit(self, df: pd.DataFrame) -> "ClinicalDataPreprocessor":
        features = [c for c in df.columns if c not in (TARGET_COL, SOURCE_COL)]
        self.feature_names = features

        # 1. Global statistics
        for col in features:
            if col in CONTINUOUS_NUMERIC_COLS:
                med = df[col].dropna().median()
                self.global_medians[col] = float(med) if pd.notna(med) else 0.0
            else:
                mode_vals = df[col].dropna().mode()
                self.global_modes[col] = float(mode_vals.iloc[0]) if not mode_vals.empty else 0.0

        # 2. Per source_dataset group statistics
        if SOURCE_COL in df.columns:
            for source, grp in df.groupby(SOURCE_COL):
                self.group_medians[str(source)] = {}
                self.group_modes[str(source)] = {}
                for col in features:
                    if col in CONTINUOUS_NUMERIC_COLS:
                        m = grp[col].dropna().median()
                        if pd.notna(m):
                            self.group_medians[str(source)][col] = float(m)
                    else:
                        m_vals = grp[col].dropna().mode()
                        if not m_vals.empty:
                            self.group_modes[str(source)][col] = float(m_vals.iloc[0])

        # 3. IQR Outlier thresholds (computed globally)
        for col in CONTINUOUS_NUMERIC_COLS:
            if col in df.columns:
                series = df[col].dropna()
                if len(series) > 10:
                    q25, q75 = series.quantile(0.25), series.quantile(0.75)
                    iqr = q75 - q25
                    lower = q25 - 1.5 * iqr
                    upper = q75 + 1.5 * iqr
                    self.iqr_bounds[col] = (float(lower), float(upper))

        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Impute missing values using fitted group and global statistics."""
        out = df.copy()
        features = [c for c in out.columns if c not in (TARGET_COL, SOURCE_COL)]

        for col in features:
            is_numeric = col in CONTINUOUS_NUMERIC_COLS
            fallback = self.global_medians.get(col, 0.0) if is_numeric else self.global_modes.get(col, 0.0)

            if SOURCE_COL in out.columns:
                for source in out[SOURCE_COL].dropna().unique():
                    mask = (out[SOURCE_COL] == source) & (out[col].isna())
                    if is_numeric:
                        val = self.group_medians.get(str(source), {}).get(col, fallback)
                    else:
                        val = self.group_modes.get(str(source), {}).get(col, fallback)
                    out.loc[mask, col] = val

            out[col] = out[col].fillna(fallback)

        return out


class EndToEndRiskPipeline:
    """Encapsulates fitted preprocessor + ML estimator for standalone deployment."""

    def __init__(self, preprocessor: ClinicalDataPreprocessor, estimator: Any, feature_cols: List[str]):
        self.preprocessor = preprocessor
        self.estimator = estimator
        self.feature_cols = feature_cols

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        df_imputed = self.preprocessor.transform(X)
        for col in self.feature_cols:
            if col not in df_imputed.columns:
                df_imputed[col] = self.preprocessor.global_medians.get(col, 0.0)
        X_features = df_imputed[self.feature_cols]
        return self.estimator.predict(X_features)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        df_imputed = self.preprocessor.transform(X)
        for col in self.feature_cols:
            if col not in df_imputed.columns:
                df_imputed[col] = self.preprocessor.global_medians.get(col, 0.0)
        X_features = df_imputed[self.feature_cols]
        return self.estimator.predict_proba(X_features)


def remove_iqr_outliers(df: pd.DataFrame, iqr_bounds: Dict[str, Tuple[float, float]]) -> Tuple[pd.DataFrame, int]:
    """Filter rows that contain extreme outliers in continuous numeric columns."""
    outlier_mask = pd.Series(False, index=df.index)

    for col, (lower, upper) in iqr_bounds.items():
        if col in df.columns:
            series = df[col]
            col_outliers = (series < max(0.0, lower)) | (series > upper)
            outlier_mask = outlier_mask | col_outliers

    num_outliers = int(outlier_mask.sum())
    cleaned_df = df[~outlier_mask].copy().reset_index(drop=True)
    return cleaned_df, num_outliers


def encode_target(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure target_risk is clean binary integer (0 or 1)."""
    if TARGET_COL in df.columns:
        df[TARGET_COL] = pd.to_numeric(df[TARGET_COL], errors="coerce").fillna(0)
        df[TARGET_COL] = (df[TARGET_COL] > 0).astype(int)
    return df


def clean_combined_data(
    df: Optional[pd.DataFrame] = None,
    input_path: Path = PROCESSED_DIR / "combined_dataset.csv",
    output_path: Path = PROCESSED_DIR / "clean_combined_dataset.csv",
    pipeline_save_path: Path = MODELS_DIR / "preprocessing_pipeline.joblib",
) -> Tuple[pd.DataFrame, ClinicalDataPreprocessor]:
    if df is None:
        if not input_path.exists():
            raise FileNotFoundError(f"Input dataset not found at {input_path}")
        print(f"[preprocessing] Loading {input_path}...")
        df = pd.read_csv(input_path)

    preprocessor = ClinicalDataPreprocessor().fit(df)
    imputed_df = preprocessor.transform(df)
    clean_df, outliers_removed = remove_iqr_outliers(imputed_df, preprocessor.iqr_bounds)
    clean_df = encode_target(clean_df)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    clean_df.to_csv(output_path, index=False)

    pipeline_save_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(preprocessor, pipeline_save_path)
    joblib.dump(preprocessor, PROCESSED_DIR / "preprocessor.joblib")

    return clean_df, preprocessor


if __name__ == "__main__":
    clean_combined_data()
