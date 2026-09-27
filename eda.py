"""
eda.py
------
Sub-Objective 1, Activity 1.4 - Exploratory Data Analysis
  - Correlation coefficients
  - Correlation between numeric and categorical features (point-biserial via
    encoding, and ANOVA-style group means)
  - Binning
  - Encoding
  - Feature importance
  - Visualizations (univariate + bivariate)
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder

CHART_DIR = Path(__file__).parent / "charts"
CHART_DIR.mkdir(exist_ok=True)
sns.set_theme(style="whitegrid")


def bin_tenure(df: pd.DataFrame) -> pd.DataFrame:
    bins = [-1, 12, 24, 48, 72]
    labels = ["0-12 mo", "13-24 mo", "25-48 mo", "49-72 mo"]
    df["tenure_bin"] = pd.cut(df["tenure"], bins=bins, labels=labels)
    return df


def encode_categoricals(df: pd.DataFrame):
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    cat_cols = [c for c in cat_cols if c not in ("customerID",)]
    encoders = {}
    df_enc = df.copy()
    for col in cat_cols:
        le = LabelEncoder()
        df_enc[col + "_enc"] = le.fit_transform(df_enc[col].astype(str))
        encoders[col] = list(le.classes_)
    return df_enc, encoders


def correlation_matrix(df_enc: pd.DataFrame):
    numeric_like = [c for c in df_enc.columns if c.endswith("_enc") or c in
                    ("tenure", "MonthlyCharges", "TotalCharges", "SeniorCitizen")]
    corr = df_enc[numeric_like].corr()
    return corr


def feature_importance(df_enc: pd.DataFrame):
    target = df_enc["Churn_enc"]
    feature_cols = [c for c in df_enc.columns if c.endswith("_enc") and c != "Churn_enc"] + \
                   ["tenure", "MonthlyCharges", "TotalCharges", "SeniorCitizen"]
    X = df_enc[feature_cols].fillna(0)
    clf = RandomForestClassifier(n_estimators=200, random_state=42, max_depth=8)
    clf.fit(X, target)
    importances = pd.Series(clf.feature_importances_, index=feature_cols).sort_values(ascending=False)
    return importances


def make_visualizations(df: pd.DataFrame, df_enc: pd.DataFrame, corr, importances):
    # Univariate: churn distribution
    plt.figure(figsize=(5, 4))
    df["Churn"].value_counts().plot(kind="bar", color=["#4C72B0", "#DD8452"])
    plt.title("Univariate: Churn Class Distribution")
    plt.xlabel("Churn"); plt.ylabel("Customer Count")
    plt.tight_layout(); plt.savefig(CHART_DIR / "01_churn_distribution.png", dpi=130); plt.close()

    # Univariate: monthly charges histogram
    plt.figure(figsize=(5, 4))
    sns.histplot(df["MonthlyCharges"], kde=True, color="#55A868")
    plt.title("Univariate: Monthly Charges Distribution")
    plt.tight_layout(); plt.savefig(CHART_DIR / "02_monthly_charges_hist.png", dpi=130); plt.close()

    # Bivariate: tenure bin vs churn rate
    plt.figure(figsize=(5.5, 4))
    churn_rate = df.groupby("tenure_bin", observed=True)["Churn"].apply(lambda s: (s == "Yes").mean())
    churn_rate.plot(kind="bar", color="#C44E52")
    plt.title("Bivariate: Churn Rate by Tenure Bin")
    plt.ylabel("Churn Rate")
    plt.tight_layout(); plt.savefig(CHART_DIR / "03_churn_by_tenure_bin.png", dpi=130); plt.close()

    # Bivariate: contract type vs churn (stacked)
    plt.figure(figsize=(5.5, 4))
    ct = pd.crosstab(df["Contract"], df["Churn"], normalize="index")
    ct.plot(kind="bar", stacked=True, color=["#4C72B0", "#DD8452"])
    plt.title("Bivariate: Churn Proportion by Contract Type")
    plt.ylabel("Proportion")
    plt.tight_layout(); plt.savefig(CHART_DIR / "04_churn_by_contract.png", dpi=130); plt.close()

    # Correlation heatmap
    plt.figure(figsize=(7, 6))
    sns.heatmap(corr, cmap="coolwarm", center=0, annot=False)
    plt.title("Correlation Heatmap (encoded features)")
    plt.tight_layout(); plt.savefig(CHART_DIR / "05_correlation_heatmap.png", dpi=130); plt.close()

    # Feature importance
    plt.figure(figsize=(6, 5))
    importances.head(10).sort_values().plot(kind="barh", color="#8172B2")
    plt.title("Top 10 Feature Importances (RandomForest)")
    plt.tight_layout(); plt.savefig(CHART_DIR / "06_feature_importance.png", dpi=130); plt.close()


def run_eda(df: pd.DataFrame):
    df = bin_tenure(df)
    df_enc, encoders = encode_categoricals(df)
    corr = correlation_matrix(df_enc)
    importances = feature_importance(df_enc)
    make_visualizations(df, df_enc, corr, importances)

    top_corr_with_churn = corr["Churn_enc"].drop("Churn_enc").abs().sort_values(ascending=False).head(8)

    report = {
        "encoders_used": {k: v for k, v in list(encoders.items())[:5]},
        "top_correlations_with_churn": json.loads(top_corr_with_churn.to_json()),
        "top_feature_importances": json.loads(importances.head(8).to_json()),
        "charts_generated": sorted(
            p.name for p in CHART_DIR.glob("0[1-6]_*.png")
        ),
    }
    return report


if __name__ == "__main__":
    from preprocessing import run_preprocessing
    clean_df, _ = run_preprocessing()
    rep = run_eda(clean_df)
    print(json.dumps(rep, indent=2)[:1500])
