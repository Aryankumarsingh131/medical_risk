"""
src/dataset_shift_check.py
--------------------------
Adversarial Dataset Shift & Domain Discrimination Test.

Trains a classifier to predict `source_dataset` provenance directly from clinical
feature distributions. If the classifier can easily distinguish which dataset a patient
record came from (accuracy significantly higher than majority baseline), it proves
strong covariate/domain shift across clinical sources.

Prints:
  - Domain discriminator accuracy vs majority-class random baseline
  - Top discriminating features driving dataset divergence
  - Plain-language conclusion:
      * 'datasets look compatible'
      * 'datasets show significant distribution shift, consider training separate models or adding a domain-adaptation step.'
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from typing import Dict, List, Tuple, Any
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder


PROCESSED_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"
REPORTS_DIR = Path(__file__).resolve().parents[1] / "reports"
DATA_PATH = PROCESSED_DIR / "clean_combined_dataset.csv"
TARGET_COL = "target_risk"
SOURCE_COL = "source_dataset"
RANDOM_STATE = 42


def run_domain_shift_test(
    data_path: Path = DATA_PATH,
    test_size: float = 0.25,
) -> Dict[str, Any]:
    """
    Train a domain classifier predicting source_dataset from clinical features.
    """
    if not data_path.exists():
        raise FileNotFoundError(f"Cleaned dataset not found at {data_path}. Run preprocessing.py first.")

    print("=" * 80)
    print("ADVERSARIAL DATASET SHIFT & DOMAIN DISCRIMINATION TEST")
    print("=" * 80)

    df = pd.read_csv(data_path)
    feature_cols = [c for c in df.columns if c not in (TARGET_COL, SOURCE_COL)]
    X = df[feature_cols]
    y_raw = df[SOURCE_COL]

    # Encode source datasets into integer classes
    le = LabelEncoder()
    y = le.fit_transform(y_raw)
    classes = list(le.classes_)

    # Calculate trivial baseline (majority class accuracy)
    class_counts = pd.Series(y).value_counts(normalize=True)
    baseline_acc = float(class_counts.iloc[0])
    majority_class_name = le.inverse_transform([class_counts.index[0]])[0]

    print(f"Total Datasets to Discriminate: {len(classes)}")
    print(f"Total Samples: {len(X):,} | Features: {len(feature_cols)}")
    print(f"Majority-Class Random Baseline Accuracy: {baseline_acc * 100:.2f}% (Majority source: '{majority_class_name}')\n")

    # Stratified split to evaluate out-of-sample domain discriminability
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=RANDOM_STATE,
        stratify=y,
    )

    # Train fast, robust domain discriminator
    clf = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    clf.fit(X_train, y_train)

    # Evaluate accuracy
    y_pred = clf.predict(X_test)
    domain_acc = float(accuracy_score(y_test, y_pred))

    print("-" * 80)
    print(f"Domain Discriminator Accuracy: {domain_acc * 100:.2f}%")
    print(f"Baseline (Majority Guess):     {baseline_acc * 100:.2f}%")
    print(f"Discrimination Delta:          +{(domain_acc - baseline_acc) * 100:.2f}% above baseline")
    print("-" * 80)

    # Feature importances driving domain separation
    importances = pd.DataFrame(
        {
            "feature": feature_cols,
            "importance": clf.feature_importances_,
        }
    ).sort_values("importance", ascending=False)

    print("\nTop 7 Features Distinguishing Clinical Sources:")
    for idx, row in importances.head(7).iterrows():
        print(f"  * {row['feature']:<22}: {row['importance'] * 100:.2f}% importance")

    print("\n" + "=" * 80)
    print("DATASET SHIFT VERDICT & CONCLUSION:")

    # Threshold: if discriminator accuracy exceeds baseline by > 15%, significant shift is present
    if domain_acc > (baseline_acc + 0.15) or domain_acc > 0.85:
        conclusion = "datasets show significant distribution shift, consider training separate models or adding a domain-adaptation step."
    else:
        conclusion = "datasets look compatible"

    print(f">>> '{conclusion}'")
    print("=" * 80 + "\n")

    # Save summary report
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / "dataset_shift_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Adversarial Dataset Shift Analysis Report\n\n")
        f.write(f"- **Domain Classifier Accuracy**: `{domain_acc * 100:.2f}%`\n")
        f.write(f"- **Majority-Class Baseline**: `{baseline_acc * 100:.2f}%`\n")
        f.write(f"- **Verdict**: **{conclusion}**\n\n")
        f.write("## Top Features Driving Domain Separation\n\n")
        f.write("| Feature | Feature Importance (%) |\n| :--- | :---: |\n")
        for _, row in importances.iterrows():
            f.write(f"| `{row['feature']}` | {row['importance'] * 100:.2f}% |\n")

    print(f"[dataset_shift_check] Shift report saved to {report_path}")

    return {
        "domain_accuracy": domain_acc,
        "baseline_accuracy": baseline_acc,
        "conclusion": conclusion,
        "feature_importances": importances.to_dict(orient="records"),
    }


if __name__ == "__main__":
    run_domain_shift_test()
