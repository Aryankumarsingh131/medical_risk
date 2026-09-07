"""
src/train.py
------------
Model training, cross-model benchmarking, sub-population evaluation, and persistence.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from typing import Dict, List, Tuple, Any
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from src.preprocessing import ClinicalDataPreprocessor, EndToEndRiskPipeline


PROCESSED_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"
MODELS_DIR = Path(__file__).resolve().parents[1] / "models"
TARGET_COL = "target_risk"
SOURCE_COL = "source_dataset"
RANDOM_STATE = 42
TEST_SIZE = 0.20


def create_joint_strata(df: pd.DataFrame) -> pd.Series:
    strata = df[SOURCE_COL].astype(str) + "___" + df[TARGET_COL].astype(str)
    counts = strata.value_counts()
    rare_strata = counts[counts < 2].index
    if not rare_strata.empty:
        strata = strata.replace({s: f"fallback_{df.loc[strata == s, TARGET_COL].iloc[0]}" for s in rare_strata})
    return strata


def evaluate_model(
    model_name: str,
    pipeline: Any,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    sources_test: pd.Series,
) -> Dict[str, Any]:
    y_pred = pipeline.predict(X_test)
    y_prob = (
        pipeline.predict_proba(X_test)[:, 1]
        if hasattr(pipeline, "predict_proba")
        else pipeline.decision_function(X_test)
    )

    overall_acc = round(accuracy_score(y_test, y_pred), 4)
    overall_f1 = round(f1_score(y_test, y_pred, average="binary", zero_division=0), 4)
    overall_roc_auc = round(roc_auc_score(y_test, y_prob), 4)

    per_source_metrics = {}
    for src in sorted(sources_test.unique()):
        mask = sources_test == src
        y_src = y_test[mask]
        y_pred_src = y_pred[mask]
        y_prob_src = y_prob[mask]
        n_samples = len(y_src)

        acc = round(accuracy_score(y_src, y_pred_src), 4)
        f1 = round(f1_score(y_src, y_pred_src, average="binary", zero_division=0), 4)
        auc = round(roc_auc_score(y_src, y_prob_src), 4) if len(np.unique(y_src)) > 1 else None

        per_source_metrics[str(src)] = {
            "samples": n_samples,
            "accuracy": acc,
            "f1": f1,
            "roc_auc": auc,
        }

    return {
        "model_name": model_name,
        "overall": {
            "accuracy": overall_acc,
            "f1": overall_f1,
            "roc_auc": overall_roc_auc,
        },
        "per_source": per_source_metrics,
    }


def train_and_evaluate(
    data_path: Path = PROCESSED_DIR / "clean_combined_dataset.csv",
    models_dir: Path = MODELS_DIR,
) -> Tuple[str, Any, Dict[str, Any]]:
    if not data_path.exists():
        raise FileNotFoundError(f"Cleaned dataset not found at {data_path}. Run preprocessing.py first.")

    df = pd.read_csv(data_path)
    feature_cols = [c for c in df.columns if c not in (TARGET_COL, SOURCE_COL)]
    y = df[TARGET_COL].astype(int)
    sources = df[SOURCE_COL]
    joint_strata = create_joint_strata(df)

    X_train, X_test, y_train, y_test, src_train, src_test = train_test_split(
        df[feature_cols],
        y,
        sources,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=joint_strata,
    )

    candidate_models = {
        "LogisticRegression": Pipeline(
            [
                ("scaler", StandardScaler()),
                ("clf", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=RANDOM_STATE)),
            ]
        ),
        "RandomForestClassifier": RandomForestClassifier(
            n_estimators=200,
            max_depth=12,
            min_samples_split=5,
            class_weight="balanced",
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
        "XGBClassifier": XGBClassifier(
            n_estimators=250,
            max_depth=6,
            learning_rate=0.08,
            subsample=0.85,
            colsample_bytree=0.85,
            scale_pos_weight=2.3,
            random_state=RANDOM_STATE,
            n_jobs=-1,
            eval_metric="logloss",
        ),
    }

    results = []
    trained_pipelines = {}

    for name, model in candidate_models.items():
        model.fit(X_train, y_train)
        trained_pipelines[name] = model
        eval_dict = evaluate_model(name, model, X_test, y_test, src_test)
        results.append(eval_dict)

    best_eval = max(results, key=lambda r: r["overall"]["roc_auc"])
    best_model_name = best_eval["model_name"]
    best_estimator = trained_pipelines[best_model_name]

    prep_path = models_dir / "preprocessing_pipeline.joblib"
    preprocessor = joblib.load(prep_path) if prep_path.exists() else ClinicalDataPreprocessor().fit(df)
    full_pipeline = EndToEndRiskPipeline(preprocessor, best_estimator, feature_cols)

    models_dir.mkdir(parents=True, exist_ok=True)
    best_model_path = models_dir / "best_model.joblib"
    joblib.dump(full_pipeline, best_model_path)
    joblib.dump(best_estimator, PROCESSED_DIR / "xgb_model.joblib")

    metrics_path = models_dir / "model_evaluation_metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"[train] Best model {best_model_name} (ROC-AUC: {best_eval['overall']['roc_auc']:.4f}) saved to {best_model_path}")
    return best_model_name, full_pipeline, results


if __name__ == "__main__":
    train_and_evaluate()
