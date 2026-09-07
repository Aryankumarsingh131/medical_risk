"""
src/data_inventory.py
---------------------
Comprehensive dataset diagnostics & health check for clinical datasets:
  - Dataset dimensions (rows, total features, numeric vs categorical features)
  - Memory consumption (MB)
  - Duplicate row counts & % duplication
  - Target column identification, target type & class imbalance ratio
  - Missing value counts & % missing cells
  - Potential outlier counts across numeric columns (1.5 * IQR rule)
  - Detailed feature-level data types, statistics, and distributions

Outputs an expanded Markdown comparison table to reports/dataset_inventory.md.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List

import pandas as pd
import numpy as np


RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
REPORTS_DIR = Path(__file__).resolve().parents[1] / "reports"

# Known target column candidate patterns ordered by priority
TARGET_CANDIDATES = [
    "diabetes_012",
    "diabetes_binary",
    "tenyearchd",
    "death_event",
    "heart disease",
    "heartdisease",
    "heart_disease",
    "presence",
    "chd",
    "target",
    "outcome",
    "label",
    "diagnosis",
    "risk_level",
    "risk_label",
    "stroke_risk",
    "stroke",
    "osteoporosis",
    "condition",
    "cardio",
    "num",
    "class",
    "diabetes",
    "risk",
]


def load_file_flexible(filepath: Path) -> pd.DataFrame:
    """Load dataset handling comma/semicolon/tab delimiters."""
    try:
        df = pd.read_csv(filepath)
        if len(df.columns) == 1 and (";" in df.columns[0] or "\t" in df.columns[0]):
            sep = ";" if ";" in df.columns[0] else "\t"
            df = pd.read_csv(filepath, sep=sep)
        return df
    except Exception:
        return pd.read_csv(filepath, sep=None, engine="python")


def detect_target_column(df: pd.DataFrame, filename: str = "") -> Tuple[Optional[str], str]:
    """
    Heuristically detect the target column and determine its type
    (Binary, Multiclass, Continuous, or None).
    """
    col_names_clean = {
        col.lower().strip().replace("-", "_").replace(" ", "_"): col
        for col in df.columns
    }

    detected_col = None
    for cand in TARGET_CANDIDATES:
        cand_clean = cand.replace(" ", "_")
        for clean_name, original_name in col_names_clean.items():
            if clean_name == cand_clean:
                detected_col = original_name
                break
        if detected_col:
            break

    if not detected_col:
        for cand in TARGET_CANDIDATES:
            cand_clean = cand.replace(" ", "_")
            for clean_name, original_name in col_names_clean.items():
                if clean_name.startswith(f"{cand_clean}_") or clean_name.endswith(f"_{cand_clean}"):
                    detected_col = original_name
                    break
            if detected_col:
                break

    if not detected_col:
        for clean_name, original_name in col_names_clean.items():
            if any(k in clean_name for k in ["target", "label", "outcome", "diag", "disease", "result"]):
                detected_col = original_name
                break

    if not detected_col and len(df.columns) > 0:
        last_col = df.columns[-1]
        if df[last_col].nunique(dropna=True) <= 10:
            detected_col = last_col

    if not detected_col:
        return None, "None"

    num_unique = df[detected_col].nunique(dropna=True)
    if num_unique == 2:
        target_type = "Binary"
    elif 2 < num_unique <= 10:
        target_type = f"Multiclass ({num_unique})"
    elif pd.api.types.is_numeric_dtype(df[detected_col]):
        target_type = "Continuous"
    else:
        target_type = f"Categorical ({num_unique})"

    return detected_col, target_type


def compute_imbalance_ratio(df: pd.DataFrame, target_col: Optional[str]) -> str:
    """Calculate class imbalance ratio (majority : minority)."""
    if not target_col or target_col not in df.columns:
        return "N/A"
    counts = df[target_col].value_counts(dropna=True)
    if len(counts) < 2:
        return "1:1" if len(counts) == 1 else "N/A"
    majority = counts.iloc[0]
    minority = counts.iloc[-1]
    if minority == 0:
        return "Inf:1"
    ratio = majority / minority
    return f"{ratio:.2f}:1"


def compute_outlier_count(df: pd.DataFrame) -> int:
    """Count number of outlier data points across numeric columns using 1.5 * IQR rule."""
    num_df = df.select_dtypes(include=[np.number])
    if num_df.empty:
        return 0
    total_outliers = 0
    for col in num_df.columns:
        series = num_df[col].dropna()
        if len(series) < 10:
            continue
        q25, q75 = series.quantile(0.25), series.quantile(0.75)
        iqr = q75 - q25
        if iqr > 0:
            lower = q25 - 1.5 * iqr
            upper = q75 + 1.5 * iqr
            outliers = ((series < lower) | (series > upper)).sum()
            total_outliers += int(outliers)
    return total_outliers


def analyze_dataset(filepath: Path) -> Dict[str, Any]:
    """
    Load CSV, print detailed statistics to console, and return rich parameter dict.
    """
    print("=" * 80)
    print(f"Dataset: {filepath.name}")
    print("=" * 80)

    try:
        df = load_file_flexible(filepath)
    except Exception as exc:
        print(f"  [ERROR] Failed to read {filepath.name}: {exc}\n")
        return {
            "dataset": filepath.name,
            "num_rows": 0,
            "num_features": 0,
            "num_numeric": 0,
            "num_categorical": 0,
            "memory_mb": 0.0,
            "duplicate_rows": 0,
            "target_name": "N/A (Error)",
            "target_type": "N/A",
            "imbalance_ratio": "N/A",
            "missing_pct": 0.0,
            "outlier_count": 0,
        }

    num_rows, num_cols = df.shape
    total_cells = num_rows * num_cols if num_rows > 0 and num_cols > 0 else 1
    total_missing_cells = int(df.isnull().sum().sum())
    overall_missing_pct = round((total_missing_cells / total_cells) * 100, 2)
    memory_mb = round(df.memory_usage(deep=True).sum() / (1024 * 1024), 2)
    duplicate_rows = int(df.duplicated().sum())
    duplicate_pct = round((duplicate_rows / num_rows) * 100, 2) if num_rows > 0 else 0.0

    target_name, target_type = detect_target_column(df, filepath.name)
    imbalance_ratio = compute_imbalance_ratio(df, target_name)
    outlier_count = compute_outlier_count(df)

    num_features = num_cols - 1 if target_name else num_cols
    feature_df = df.drop(columns=[target_name]) if target_name and target_name in df.columns else df
    num_numeric = len(feature_df.select_dtypes(include=[np.number]).columns)
    num_categorical = len(feature_df.select_dtypes(exclude=[np.number]).columns)

    # 1. Print Shape & Storage Diagnostics
    print(f"Shape: {num_rows:,} rows × {num_cols:,} columns ({num_features} features: {num_numeric} numeric, {num_categorical} categorical)")
    print(f"Memory: {memory_mb} MB | Duplicate Rows: {duplicate_rows:,} ({duplicate_pct}%) | Outliers Detected: {outlier_count:,}")

    # 2. Print Column names & Dtypes
    print("\nColumns & Data Diagnostics:")
    for col, dtype in df.dtypes.items():
        missing_count = int(df[col].isnull().sum())
        missing_p = (missing_count / num_rows * 100) if num_rows > 0 else 0
        missing_str = f" | {missing_count} missing ({missing_p:.1f}%)" if missing_count > 0 else ""
        unique_cnt = df[col].nunique(dropna=True)
        target_flag = "  <-- [TARGET]" if col == target_name else ""
        print(f"  - {col} ({dtype}, {unique_cnt} unique){missing_str}{target_flag}")

    # 3. Print Target Column & Class Balance
    print(f"\nLikely Target Column: {target_name or 'Not detected'} (Type: {target_type}, Imbalance Ratio: {imbalance_ratio})")
    if target_name and target_name in df.columns:
        print("Class Balance / Distribution:")
        counts = df[target_name].value_counts(dropna=False)
        percentages = df[target_name].value_counts(dropna=False, normalize=True) * 100
        for idx, (val, count) in enumerate(counts.items()):
            if idx >= 8:
                print(f"  ... and {len(counts) - 8} other classes")
                break
            pct = percentages[val]
            val_label = "<NaN>" if pd.isna(val) else val
            print(f"  - Class '{val_label}': {count:,} ({pct:.2f}%)")

    # 4. Print Missing Value Summary
    missing_series = df.isnull().sum()
    cols_with_missing = missing_series[missing_series > 0]
    print(f"\nMissing Values Overview: Total missing cells = {total_missing_cells:,} ({overall_missing_pct}%)")
    if not cols_with_missing.empty:
        print("  Columns with missing values:")
        for col, count in cols_with_missing.items():
            pct = (count / num_rows) * 100
            print(f"    * {col}: {count:,} ({pct:.2f}%)")
    else:
        print("  No missing values found across any columns.")

    print("\n")

    return {
        "dataset": filepath.name,
        "num_rows": num_rows,
        "num_features": num_features,
        "num_numeric": num_numeric,
        "num_categorical": num_categorical,
        "memory_mb": memory_mb,
        "duplicate_rows": duplicate_rows,
        "target_name": target_name or "N/A",
        "target_type": target_type,
        "imbalance_ratio": imbalance_ratio,
        "missing_pct": overall_missing_pct,
        "outlier_count": outlier_count,
    }


def generate_markdown_report(summary_records: List[Dict[str, Any]], output_path: Path) -> str:
    """Generate comprehensive Markdown comparison table and save to reports/dataset_inventory.md."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    header = "# Dataset Inventory & Diagnostic Comparison\n\n"
    intro = (
        "Comprehensive health-check across all raw datasets in `data/raw/` comparing shape, "
        "feature composition (numeric vs categorical), memory footprint, duplicates, target distribution, "
        "class imbalance ratio, outlier counts, and missingness.\n\n"
    )

    table_header = (
        "| Dataset | Rows | Total Feat | Num / Cat | Memory | Duplicates | Target Name | Target Type | Imbalance | Outliers | Missing % |\n"
    )
    table_divider = (
        "| :--- | :---: | :---: | :---: | :---: | :---: | :--- | :--- | :---: | :---: | :---: |\n"
    )

    rows = []
    for rec in summary_records:
        rows.append(
            f"| `{rec['dataset']}` | {rec['num_rows']:,} | {rec['num_features']:,} | "
            f"{rec['num_numeric']} / {rec['num_categorical']} | {rec['memory_mb']} MB | "
            f"{rec['duplicate_rows']:,} | `{rec['target_name']}` | {rec['target_type']} | "
            f"{rec['imbalance_ratio']} | {rec['outlier_count']:,} | {rec['missing_pct']}% |"
        )

    md_content = header + intro + table_header + table_divider + "\n".join(rows) + "\n"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"[data_inventory] Expanded markdown report generated at: {output_path}")
    return md_content


def run_inventory(raw_dir: Path = RAW_DIR, report_path: Path = REPORTS_DIR / "dataset_inventory.md") -> List[Dict[str, Any]]:
    """Scan raw_dir for data files, analyze each, and produce the markdown report."""
    raw_files = sorted(raw_dir.glob("*.csv")) + sorted(raw_dir.glob("*.txt"))
    valid_files = [fp for fp in raw_files if not fp.name.startswith(".")]

    if not valid_files:
        print(f"[data_inventory] No CSV/data files found in {raw_dir}")
        return []

    print(f"[data_inventory] Analyzing {len(valid_files)} file(s) in {raw_dir} with expanded diagnostics...\n")
    summaries = []
    for fp in valid_files:
        summary = analyze_dataset(fp)
        summaries.append(summary)

    generate_markdown_report(summaries, report_path)
    return summaries


if __name__ == "__main__":
    run_inventory()
