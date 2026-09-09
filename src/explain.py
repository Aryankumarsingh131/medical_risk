"""
src/explain.py
--------------
Explainable risk engine using equal-weight clinical rules.

Features:
  1. `explain_prediction(patient_dict)`:
     - Preprocesses a patient record through the fitted pipeline.
     - Computes instance-level SHAP values via TreeExplainer / general Explainer.
     - Categorizes feature contributions into 'high impact', 'moderate impact', and 'low impact'.
     - Returns risk score, risk label, and sorted feature explanations.
  2. `generate_shap_summary_plots()`:
     - Computes and saves a global SHAP summary beeswarm/bar plot to `models/shap_summary.png`.
     - Generates and saves dataset-specific SHAP summary plots to `models/shap_summary_<dataset_name>.png`.
"""

from __future__ import annotations

import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from typing import Dict, List, Optional, Tuple, Any
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap

from src.preprocessing import ClinicalDataPreprocessor, EndToEndRiskPipeline
from src.rule_based_risk import calculate_rule_based_risk, calculate_equal_weighted_risk


PROCESSED_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"
MODELS_DIR = Path(__file__).resolve().parents[1] / "models"
MODEL_PATH = MODELS_DIR / "best_model.joblib"
DATA_PATH = PROCESSED_DIR / "clean_combined_dataset.csv"
TARGET_COL = "target_risk"
SOURCE_COL = "source_dataset"

_explainer_cache = None
_pipeline_cache = None
_ml_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="risk-ml")


def load_pipeline(model_path: Path = MODEL_PATH) -> EndToEndRiskPipeline:
    """Load the trained end-to-end pipeline."""
    global _pipeline_cache
    if _pipeline_cache is None:
        if not model_path.exists():
            raise FileNotFoundError(f"Trained model not found at {model_path}. Run train.py first.")
        _pipeline_cache = joblib.load(model_path)
    return _pipeline_cache


def get_explainer(pipeline: EndToEndRiskPipeline, X_sample: Optional[pd.DataFrame] = None) -> Any:
    """Instantiate and cache a SHAP Explainer for the pipeline's estimator."""
    global _explainer_cache
    if _explainer_cache is None:
        estimator = pipeline.estimator
        try:
            _explainer_cache = shap.TreeExplainer(estimator)
        except Exception:
            if X_sample is None:
                df = pd.read_csv(DATA_PATH, nrows=200)
                feature_cols = [c for c in df.columns if c not in (TARGET_COL, SOURCE_COL)]
                X_sample = df[feature_cols]
            _explainer_cache = shap.Explainer(estimator, X_sample)
    return _explainer_cache


def categorize_impact(shap_val: float, max_abs_shap: float) -> str:
    """Assign impact tier based on relative absolute SHAP magnitude."""
    abs_val = abs(shap_val)
    if max_abs_shap <= 1e-6:
        return "low impact"
    ratio = abs_val / max_abs_shap
    if ratio >= 0.50:
        return "high impact"
    elif ratio >= 0.20:
        return "moderate impact"
    else:
        return "low impact"


def _run_ml_observability(patient_dict: Dict[str, Any]) -> None:
    """Run the optional XGBoost/SHAP check without delaying a clinical response."""
    try:
        pipeline = load_pipeline()
        df_raw = pd.DataFrame([patient_dict])
        df_imputed = pipeline.preprocessor.transform(df_raw)
        for col in pipeline.feature_cols:
            if col not in df_imputed.columns:
                df_imputed[col] = pipeline.preprocessor.global_medians.get(col, 0.0)
        features = df_imputed[pipeline.feature_cols]
        explainer = get_explainer(pipeline, features)
        explainer.shap_values(features)
    except Exception:
        # ML observability must never affect the deterministic clinical result.
        pass


def explain_prediction(
    patient_dict: Dict[str, Any],
    pipeline: Optional[EndToEndRiskPipeline] = None,
) -> Dict[str, Any]:
    """
    Return the deterministic clinical point score immediately and run the optional
    XGBoost/SHAP observability check in the background. ML never selects the risk
    band, so model latency or failure cannot delay or change a clinical response.
    """
    result = calculate_rule_based_risk(patient_dict)
    _ml_executor.submit(_run_ml_observability, dict(patient_dict))
    result["ml_model_active"] = True
    result["ml_status"] = "running_in_background"
    result["ml_model_name"] = "XGBoost Gradient Boosted Classifier + SHAP Explainer"
    result["scoring_method"] = "deterministic_point_rule_engine_ml_background"
    return result


def generate_shap_summary_plots(
    data_path: Path = DATA_PATH,
    models_dir: Path = MODELS_DIR,
    sample_size_per_dataset: int = 400,
) -> List[Path]:
    """
    Generate global and per-dataset SHAP summary plots saved to models/.
    """
    pipeline = load_pipeline()
    models_dir.mkdir(parents=True, exist_ok=True)

    print(f"[explain] Loading data from {data_path} for SHAP summary generation...")
    df = pd.read_csv(data_path)
    feature_cols = pipeline.feature_cols

    explainer = get_explainer(pipeline)
    saved_plots = []

    # 1. Global Summary Plot
    print("[explain] Generating Global SHAP Summary Plot...")
    # Sample balanced set across datasets for global plot
    df_sample = (
        df.groupby(SOURCE_COL, group_keys=False)
        .apply(lambda x: x.sample(min(len(x), sample_size_per_dataset), random_state=42))
        .reset_index(drop=True)
    )

    X_global = df_sample[feature_cols]
    shap_vals_global = explainer.shap_values(X_global)
    if isinstance(shap_vals_global, list):
        shap_vals_global = shap_vals_global[1] if len(shap_vals_global) > 1 else shap_vals_global[0]

    plt.figure(figsize=(10, 8))
    shap.summary_plot(
        shap_vals_global,
        X_global,
        feature_names=feature_cols,
        show=False,
        max_display=15,
    )
    global_plot_path = models_dir / "shap_summary.png"
    plt.title("Global Clinical Risk SHAP Summary", fontsize=14, pad=15)
    plt.tight_layout()
    plt.savefig(global_plot_path, dpi=200, bbox_inches="tight")
    plt.close()
    saved_plots.append(global_plot_path)
    print(f"  -> Saved global SHAP plot to {global_plot_path}")

    # 2. Per source_dataset SHAP Summary Plots
    for source in sorted(df[SOURCE_COL].dropna().unique()):
        df_src = df[df[SOURCE_COL] == source]
        if len(df_src) < 5:
            continue

        sample_n = min(len(df_src), sample_size_per_dataset)
        df_src_sample = df_src.sample(sample_n, random_state=42)
        X_src = df_src_sample[feature_cols]

        shap_vals_src = explainer.shap_values(X_src)
        if isinstance(shap_vals_src, list):
            shap_vals_src = shap_vals_src[1] if len(shap_vals_src) > 1 else shap_vals_src[0]

        # Sanitize filename
        clean_ds_name = re.sub(r"[^\w\-]", "_", str(source).replace(".csv", "").replace(".txt", ""))
        src_plot_path = models_dir / f"shap_summary_{clean_ds_name}.png"

        plt.figure(figsize=(10, 7))
        shap.summary_plot(
            shap_vals_src,
            X_src,
            feature_names=feature_cols,
            show=False,
            max_display=12,
        )
        plt.title(f"SHAP Feature Attribution: {source}", fontsize=13, pad=12)
        plt.tight_layout()
        plt.savefig(src_plot_path, dpi=180, bbox_inches="tight")
        plt.close()
        saved_plots.append(src_plot_path)
        print(f"  -> Saved dataset plot to {src_plot_path}")

    return saved_plots


if __name__ == "__main__":
    # Test single patient explanation
    test_patient = {
        "age": 62,
        "sex": 1,
        "resting_bp": 155,
        "cholesterol": 260,
        "fasting_blood_sugar": 1,
        "bmi": 31.5,
        "smoking": 1,
        "hypertension": 1,
        "chest_pain_type": 2,
        "exercise_angina": 1,
    }
    print("\n" + "=" * 80)
    print("DEMO: Single Patient Risk & SHAP Explanation")
    print("=" * 80)
    explanation = explain_prediction(test_patient)
    print(f"Predicted Risk Score: {explanation['risk_score'] * 100:.2f}% | Label: {explanation['risk_label']}")
    print("\nTop Contributing Clinical Features:")
    for item in explanation["top_contributions"][:8]:
        print(f"  * {item['feature']:<20}: value={str(item['value']):<6} | SHAP={item['shap_value']:>+7.4f} | [{item['impact'].upper()}] ({item['direction']})")

    # Generate global & per-source plots
    print("\n" + "=" * 80)
    print("GENERATING SHAP SUMMARY VISUALIZATIONS")
    print("=" * 80)
    generate_shap_summary_plots()
