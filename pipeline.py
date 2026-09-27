"""
pipeline.py
-----------
Sub-Objective 1, Activity 1.5 - DataOps
  Automates steps 1.3 (pre-processing) and 1.4 (EDA) into a single
  repeatable pipeline "run". Every run is logged (structured JSON lines)
  to logs/pipeline.log AND appended to logs/run_history.json so that the
  API layer (Sub-Objective 2) and the dashboard can surface run history,
  status, and metrics.
"""
import json
import logging
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from preprocessing import run_preprocessing
from eda import run_eda

BASE_DIR = Path(__file__).parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
HISTORY_FILE = LOG_DIR / "run_history.json"

logger = logging.getLogger("dataops_pipeline")
logger.setLevel(logging.INFO)
if not logger.handlers:
    fh = logging.FileHandler(LOG_DIR / "pipeline.log")
    fh.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(message)s'))
    logger.addHandler(fh)
    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(message)s'))
    logger.addHandler(sh)


def _load_history():
    if HISTORY_FILE.exists():
        return json.loads(HISTORY_FILE.read_text())
    return []


def _save_history(history):
    HISTORY_FILE.write_text(json.dumps(history, indent=2))


def run_pipeline_once():
    run_id = datetime.now(timezone.utc).strftime("run-%Y%m%dT%H%M%S")
    start = time.time()
    logger.info(f"[{run_id}] Pipeline run STARTED")
    status = "SUCCESS"
    error_msg = None
    prep_report, eda_report = {}, {}
    try:
        logger.info(f"[{run_id}] Stage 1/2: Pre-processing (1.3) starting")
        clean_df, prep_report = run_preprocessing()
        logger.info(
            f"[{run_id}] Pre-processing complete | rows={prep_report['rows']} "
            f"missing_fixed={list(prep_report['missing_before'].keys())}"
        )

        logger.info(f"[{run_id}] Stage 2/2: EDA (1.4) starting")
        eda_report = run_eda(clean_df)
        logger.info(
            f"[{run_id}] EDA complete | charts={len(eda_report['charts_generated'])} "
            f"top_driver={list(eda_report['top_feature_importances'].keys())[0]}"
        )
    except Exception as e:
        status = "FAILED"
        error_msg = str(e)
        logger.error(f"[{run_id}] Pipeline FAILED: {e}\n{traceback.format_exc()}")

    duration = round(time.time() - start, 2)
    logger.info(f"[{run_id}] Pipeline run ENDED | status={status} | duration_sec={duration}")

    record = {
        "run_id": run_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "duration_sec": duration,
        "rows_processed": prep_report.get("rows"),
        "missing_values_fixed": prep_report.get("missing_before"),
        "top_feature_importances": eda_report.get("top_feature_importances"),
        "top_correlations_with_churn": eda_report.get("top_correlations_with_churn"),
        "charts_generated": eda_report.get("charts_generated"),
        "error": error_msg,
    }
    history = _load_history()
    history.append(record)
    _save_history(history)
    return record


if __name__ == "__main__":
    result = run_pipeline_once()
    print(json.dumps(result, indent=2)[:2000])
