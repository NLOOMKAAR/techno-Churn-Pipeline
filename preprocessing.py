"""
preprocessing.py
-----------------
Sub-Objective 1, Activity 1.3 - Data Pre-processing
  - Display summary statistics
  - Check for missing values
  - Impute missing data for numeric columns
  - Display data types
  - Normalize data
"""
import json
import numpy as np
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"


def load_raw():
    return pd.read_csv(DATA_DIR / "telco_churn_raw.csv")


def clean_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """Fix the classic Telco-churn dtype issue: TotalCharges arrives as object
    because of blank-string entries; coerce to numeric."""
    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce")
    return df


def summary_statistics(df: pd.DataFrame) -> dict:
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    return json.loads(df[numeric_cols].describe().to_json())


def missing_value_report(df: pd.DataFrame) -> dict:
    miss = df.isna().sum()
    pct = (miss / len(df) * 100).round(2)
    return {
        col: {"missing_count": int(miss[col]), "missing_pct": float(pct[col])}
        for col in df.columns if miss[col] > 0
    }


def impute_numeric(df: pd.DataFrame) -> pd.DataFrame:
    """Impute missing numeric values with the column median (robust to outliers)."""
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    for col in numeric_cols:
        if df[col].isna().any():
            median_val = df[col].median()
            df[col] = df[col].fillna(median_val)
    return df


def normalize(df: pd.DataFrame, cols=("tenure", "MonthlyCharges", "TotalCharges")) -> pd.DataFrame:
    """Min-max normalize selected numeric columns into new *_norm columns."""
    for col in cols:
        min_v, max_v = df[col].min(), df[col].max()
        df[f"{col}_norm"] = (df[col] - min_v) / (max_v - min_v)
    return df


def dtype_report(df: pd.DataFrame) -> dict:
    return {col: str(dtype) for col, dtype in df.dtypes.items()}


def run_preprocessing():
    """Executes the full 1.3 pipeline stage and returns (clean_df, report_dict)."""
    df = load_raw()
    dtypes_before = dtype_report(df)
    df = clean_dtypes(df)
    missing_before = missing_value_report(df)
    stats_before = summary_statistics(df)
    df = impute_numeric(df)
    df = normalize(df)
    missing_after = missing_value_report(df)
    dtypes_after = dtype_report(df)

    report = {
        "rows": len(df),
        "columns": len(df.columns),
        "dtypes_before": dtypes_before,
        "dtypes_after": dtypes_after,
        "missing_before": missing_before,
        "missing_after": missing_after,
        "summary_statistics": stats_before,
    }
    df.to_csv(DATA_DIR / "telco_churn_clean.csv", index=False)
    return df, report


if __name__ == "__main__":
    _, rep = run_preprocessing()
    print(json.dumps(rep, indent=2)[:1500])
