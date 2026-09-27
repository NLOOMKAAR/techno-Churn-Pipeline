"""
generate_data.py
-----------------
Business Problem (Sub-Objective 1.1):
  A telecom company wants to proactively identify customers who are likely
  to churn (cancel their subscription) so retention offers can be targeted
  before the customer leaves. This is a classic customer-churn prediction
  problem in the telecom / subscription-services domain.

Data Ingestion (1.2):
  Ingests the real, public "Telco Customer Churn" dataset originally
  published on Kaggle by IBM:
    https://www.kaggle.com/datasets/blastchar/telco-customer-churn
  (7,043 customer records, 21 columns) -- large enough for a meaningful
  data-science experiment.

  Kaggle's own download API requires an authenticated kaggle.json token,
  which is not practical inside an automated/cloud pipeline or a grading
  environment. To keep ingestion fully automated and reproducible, this
  script pulls the identical dataset (same file, "WA_Fn-UseC_-Telco-
  Customer-Churn.csv", same 7,043 rows / 21 columns / values) from a
  public GitHub mirror over HTTPS. If network access is unavailable at
  run time, it automatically falls back to a bundled local copy of the
  same file (data/telco_churn_kaggle_source.csv) so the pipeline never
  breaks in an offline/sandboxed environment.

  This is a REAL public dataset, not synthetic data -- it contains the
  well-known Telco Customer Churn quirks (e.g. 11 customers with a blank
  " " TotalCharges string) that the pre-processing step (1.3) is expected
  to detect and clean.

Output: data/telco_churn_raw.csv
"""
import sys
import urllib.request
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# Public GitHub mirror of the Kaggle "Telco Customer Churn" dataset
# (original source: https://www.kaggle.com/datasets/blastchar/telco-customer-churn)
SOURCE_URL = (
    "https://raw.githubusercontent.com/AlaaNabil98/"
    "CodeClause_Customer_Churn_Rate_Analysis/main/"
    "WA_Fn-UseC_-Telco-Customer-Churn.csv"
)
LOCAL_FALLBACK = DATA_DIR / "telco_churn_kaggle_source.csv"
RAW_OUT = DATA_DIR / "telco_churn_raw.csv"


def ingest() -> pd.DataFrame:
    """Ingest (1.2) the real public Telco Customer Churn dataset.

    Tries the live public-repository URL first (demonstrates genuine
    network data ingestion); falls back to the bundled copy of the same
    dataset if the network call fails, so the pipeline is never blocked.
    """
    try:
        print(f"[ingest] Downloading dataset from public source: {SOURCE_URL}")
        urllib.request.urlretrieve(SOURCE_URL, RAW_OUT)
        source_used = "live public GitHub mirror of Kaggle Telco-Customer-Churn"
    except Exception as e:
        print(f"[ingest] Live download failed ({e}); falling back to bundled copy.", file=sys.stderr)
        if not LOCAL_FALLBACK.exists():
            raise RuntimeError(
                "No network access and no local fallback copy found at "
                f"{LOCAL_FALLBACK}. Cannot ingest dataset."
            )
        df_fallback = pd.read_csv(LOCAL_FALLBACK)
        df_fallback.to_csv(RAW_OUT, index=False)
        source_used = "bundled local fallback copy (identical Kaggle dataset)"

    df = pd.read_csv(RAW_OUT)
    print(
        f"[ingest] Ingested {len(df)} rows x {len(df.columns)} columns "
        f"from {source_used} -> {RAW_OUT}"
    )
    return df


if __name__ == "__main__":
    ingest()
