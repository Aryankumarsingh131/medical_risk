"""
src/build_training_data.py
--------------------------
Loads all datasets from data/raw/ using `load_and_standardize` from src/schema_mapping.py,
attaches a `source_dataset` provenance tag to each record, concatenates them into
a single master DataFrame, reports detailed missingness statistics before and after merging,
and saves the result to data/processed/combined_dataset.csv.

Also performs a stratified train/validation/test split on records with valid target labels
and saves train.csv, val.csv, test.csv to data/processed/.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from src.schema_mapping import (
    CANONICAL_COLUMNS,
    DATASET_CONFIGS,
    RAW_DIR,
    PROCESSED_DIR,
    load_and_standardize,
)

RANDOM_STATE = 42
VAL_SIZE = 0.10   # 10 % validation
TEST_SIZE = 0.15  # 15 % test
TARGET_COL = "target_risk"


def print_missing_report(df: pd.DataFrame, title: str) -> None:
    """Print per-column missingness counts and percentages."""
    print(f"\n--- Missing Values Report: {title} ({len(df):,} rows × {df.shape[1]} cols) ---")
    report_rows = []
    for col in df.columns:
        missing_cnt = int(df[col].isnull().sum())
        missing_pct = (missing_cnt / len(df) * 100) if len(df) > 0 else 0.0
        report_rows.append(f"  * {col:<22}: {missing_cnt:>7,} missing ({missing_pct:>6.2f}%)")
    print("\n".join(report_rows))


def load_all_standardized(raw_dir: Path = RAW_DIR) -> Tuple[pd.DataFrame, Dict[str, pd.DataFrame]]:
    """
    Load every configured dataset in raw_dir via load_and_standardize(),
    print its individual shape and missingness, attach `source_dataset`,
    and concatenate into a single combined DataFrame.
    """
    dataset_frames: Dict[str, pd.DataFrame] = {}
    frames_with_source: List[pd.DataFrame] = []

    raw_files = [f.name for f in raw_dir.glob("*") if not f.name.startswith(".") and (f.suffix in [".csv", ".txt"])]
    target_datasets = [f for f in raw_files if f in DATASET_CONFIGS]

    if not target_datasets:
        raise FileNotFoundError(f"No configured datasets found in {raw_dir}")

    print("=" * 80)
    print(f"Loading and standardizing {len(target_datasets)} datasets from {raw_dir}")
    print("=" * 80)

    for ds_name in sorted(target_datasets):
        try:
            df_std = load_and_standardize(ds_name, raw_dir=raw_dir)
            dataset_frames[ds_name] = df_std.copy()

            # Report individual dataset stats before merge
            print_missing_report(df_std, title=f"Dataset '{ds_name}'")

            # Attach source dataset tracking column
            df_with_src = df_std.copy()
            df_with_src["source_dataset"] = ds_name
            frames_with_source.append(df_with_src)
        except Exception as exc:
            print(f"[build_training_data] Warning: Skipped {ds_name} due to error: {exc}")

    # Concatenate all standardized datasets
    combined_df = pd.concat(frames_with_source, ignore_index=True)
    return combined_df, dataset_frames


def split_data(
    df: pd.DataFrame,
    target_col: str = TARGET_COL,
    val_size: float = VAL_SIZE,
    test_size: float = TEST_SIZE,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Filter records with valid target values and perform stratified train/val/test split.
    """
    valid_df = df.dropna(subset=[target_col]).copy()
    valid_df[target_col] = valid_df[target_col].astype(int)

    print(f"\n[build_training_data] Valid labelled records for training: {len(valid_df):,} / {len(df):,}")

    stratify = valid_df[target_col] if valid_df[target_col].nunique() > 1 else None

    train_df, temp_df = train_test_split(
        valid_df,
        test_size=(val_size + test_size),
        random_state=RANDOM_STATE,
        stratify=stratify,
    )

    relative_test = test_size / (val_size + test_size)
    stratify_temp = temp_df[target_col] if stratify is not None else None

    val_df, test_df = train_test_split(
        temp_df,
        test_size=relative_test,
        random_state=RANDOM_STATE,
        stratify=stratify_temp,
    )

    print(
        f"[build_training_data] Stratified Splits -> Train: {len(train_df):,} rows | "
        f"Val: {len(val_df):,} rows | Test: {len(test_df):,} rows"
    )
    return train_df, val_df, test_df


def save_processed_datasets(
    combined_df: pd.DataFrame,
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    output_dir: Path = PROCESSED_DIR,
) -> None:
    """Save combined_dataset.csv and train/val/test split CSVs."""
    output_dir.mkdir(parents=True, exist_ok=True)

    combined_path = output_dir / "combined_dataset.csv"
    combined_df.to_csv(combined_path, index=False)
    print(f"\n[build_training_data] Saved combined dataset to {combined_path} ({combined_df.shape})")

    for name, df_split in [("train", train_df), ("val", val_df), ("test", test_df)]:
        split_path = output_dir / f"{name}.csv"
        df_split.to_csv(split_path, index=False)
        print(f"[build_training_data] Saved split: {split_path.name} ({df_split.shape})")


def run_pipeline() -> pd.DataFrame:
    combined_df, _ = load_all_standardized(RAW_DIR)

    print("=" * 80)
    print_missing_report(combined_df, title="COMBINED DATASET (AFTER MERGE)")
    print("=" * 80)

    train_df, val_df, test_df = split_data(combined_df)
    save_processed_datasets(combined_df, train_df, val_df, test_df, PROCESSED_DIR)

    return combined_df


if __name__ == "__main__":
    run_pipeline()
