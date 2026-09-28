"""
api/main.py
-----------
Sub-Objective 2 - API Access, upgraded for cloud-native integration.

Cloud-native characteristics added on top of the original assignment API:
  - 12-factor config (api/config.py) - every deploy-time knob is an env var
  - Versioned API surface: /api/v1/*  (legacy /api/* kept as aliases so
    nothing that already depends on this service breaks)
  - Split liveness vs readiness probes (/health/live, /health/ready) -
    the standard Kubernetes/Cloud Run/ECS health-check contract
  - Structured JSON logs (api/logging_setup.py) for CloudWatch/Cloud
    Logging/ELK, tagged with a per-request correlation ID
  - X-Request-ID middleware for distributed tracing across services
  - A uniform JSON error envelope on every 4xx/5xx response
  - A minimal /metrics endpoint (Prometheus-style counters) for
    observability integration
  - CORS middleware, configurable via env var, so a separately-hosted
    frontend/API-gateway can call this service cross-origin
  - Fully typed responses (api/schemas.py) -> a complete OpenAPI 3.1
    contract at /openapi.json that an API gateway can import directly

Run locally:
    uvicorn api.main:app --host 0.0.0.0 --port 8000

Run with overridden config:
    PORT=9000 LOG_FORMAT=text CORS_ORIGINS=https://app.example.com \
        uvicorn api.main:app --host 0.0.0.0 --port 9000
"""
import json
import logging
import platform
import sys
import time
import uuid
from collections import Counter
from contextvars import ContextVar
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.config import get_settings
from api.logging_setup import configure_logging
from api.schemas import (
    AppFlowResponse, AppInfoResponse, DatasetInfoResponse, ErrorResponse,
    FeatureImportanceResponse, LivenessResponse, MetricsResponse,
    PipelineRunsResponse, ReadinessCheck, ReadinessResponse,
)

settings = get_settings()
configure_logging(settings.log_level, settings.log_format)
logger = logging.getLogger("churn_api")

APP_START_TIME = datetime.now(timezone.utc)
_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")

# In-memory metrics (reset on restart - fine for a demo/assignment service;
# swap for a Prometheus client + /metrics in the standard exposition format
# for real production use).
_metrics = {"requests_total": 0, "requests_by_path": Counter()}


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id_ctx.get()
        return True


logging.getLogger().addFilter(RequestIdFilter())

app = FastAPI(
    title="Telco Churn DataOps Pipeline API",
    description=(
        "Cloud-native, versioned REST API exposing application, deployment, "
        "pipeline and dataset details for the AIMLCZG549 Assignment-1 "
        "Telco Churn DataOps pipeline."
    ),
    version=settings.app_version,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    """Assigns/propagates X-Request-ID and logs one structured line per request."""
    incoming_id = request.headers.get("x-request-id")
    request_id = incoming_id or str(uuid.uuid4())
    token = _request_id_ctx.set(request_id)
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Unhandled exception while processing request")
        _request_id_ctx.reset(token)
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "INTERNAL_ERROR", "message": "Internal server error",
                                "request_id": request_id}},
            headers={"X-Request-ID": request_id},
        )
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    _metrics["requests_total"] += 1
    _metrics["requests_by_path"][request.url.path] += 1
    logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms}ms)")
    response.headers["X-Request-ID"] = request_id
    _request_id_ctx.reset(token)
    return response


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Uniform {error: {code, message, request_id}} envelope on every error response,
    including framework-level 404s for unmatched routes (Starlette raises those
    directly, bypassing a handler registered only for fastapi.HTTPException)."""
    code = {404: "NOT_FOUND", 400: "BAD_REQUEST", 422: "VALIDATION_ERROR",
            503: "NOT_READY"}.get(exc.status_code, "ERROR")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": code, "message": exc.detail,
                            "request_id": _request_id_ctx.get()}},
    )


def _load_history():
    if settings.history_file.exists():
        return json.loads(settings.history_file.read_text())
    return []


# ---------------------------------------------------------------------------
# Health probes - the standard cloud/Kubernetes contract.
#   liveness  = "is the process up at all?"   -> restart the container if not
#   readiness = "can it actually serve now?"  -> pull out of the LB if not
# ---------------------------------------------------------------------------
@app.get("/health/live", response_model=LivenessResponse, tags=["health"])
def health_live():
    return LivenessResponse(server_time_utc=datetime.now(timezone.utc).isoformat())


@app.get("/health/ready", response_model=ReadinessResponse, tags=["health"])
def health_ready():
    checks = [
        ReadinessCheck(name="log_dir_writable", ok=settings.log_dir.exists(),
                        detail=str(settings.log_dir)),
        ReadinessCheck(name="data_dir_present", ok=settings.data_dir.exists(),
                        detail=str(settings.data_dir)),
        ReadinessCheck(name="pipeline_has_run", ok=settings.history_file.exists(),
                        detail="at least one pipeline run recorded" if settings.history_file.exists()
                        else "no run_history.json yet - scheduler may still be starting"),
    ]
    ready = all(c.ok for c in checks)
    status_code = 200 if ready else 503
    body = ReadinessResponse(status="ready" if ready else "not_ready", checks=checks)
    return JSONResponse(status_code=status_code, content=json.loads(body.model_dump_json()))


@app.get("/health", response_model=LivenessResponse, tags=["health"], deprecated=True)
def health_legacy():
    """Deprecated alias kept for backward compatibility - use /health/live or /health/ready."""
    return health_live()


# ---------------------------------------------------------------------------
# Versioned application API
# ---------------------------------------------------------------------------
@app.get("/api/v1/app/info", response_model=AppInfoResponse, tags=["app"])
def app_info():
    return AppInfoResponse(
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        deployment_target="Docker container (Kubernetes / AWS ECS-Fargate / "
                           "GCP Cloud Run / Azure Container Apps)",
        python_version=sys.version.split()[0],
        platform=platform.platform(),
        started_at_utc=APP_START_TIME.isoformat(),
        uptime_seconds=round((datetime.now(timezone.utc) - APP_START_TIME).total_seconds(), 2),
    )


@app.get("/api/v1/app/flow", response_model=AppFlowResponse, tags=["app"])
def app_flow():
    return AppFlowResponse(
        pipeline_name="dataops_pipeline_job",
        schedule=f"every {settings.schedule_interval_minutes} minutes (APScheduler interval trigger, UTC)",
        stages=[
            {"order": 1, "stage": "Data Ingestion", "module": "generate_data.py",
             "description": "Loads/refreshes the raw Telco customer dataset from a public source"},
            {"order": 2, "stage": "Pre-processing", "module": "preprocessing.py",
             "description": "Summary stats, missing value detection & imputation, dtype fix, normalization"},
            {"order": 3, "stage": "EDA", "module": "eda.py",
             "description": "Correlation, binning, encoding, feature importance, visualizations"},
            {"order": 4, "stage": "Logging & History", "module": "pipeline.py",
             "description": "Structured logs to logs/pipeline.log and run_history.json"},
        ],
    )


@app.get("/api/v1/pipeline/runs", response_model=PipelineRunsResponse, tags=["pipeline"])
def pipeline_runs(limit: int = 10):
    history = _load_history()
    return PipelineRunsResponse(total_runs=len(history), runs=history[-limit:])


@app.get("/api/v1/pipeline/latest", tags=["pipeline"],
         responses={404: {"model": ErrorResponse}})
def pipeline_latest():
    history = _load_history()
    if not history:
        raise HTTPException(status_code=404, detail="No pipeline runs recorded yet")
    return history[-1]


@app.get("/api/v1/dataset/info", response_model=DatasetInfoResponse, tags=["dataset"],
         responses={404: {"model": ErrorResponse}})
def dataset_info():
    import pandas as pd
    csv_path = settings.clean_data_file
    if not csv_path.exists():
        raise HTTPException(status_code=404, detail="Dataset not yet generated - run the pipeline first")
    df = pd.read_csv(csv_path)
    return DatasetInfoResponse(
        rows=len(df),
        columns=len(df.columns),
        column_names=df.columns.tolist(),
        target_variable="Churn",
        churn_rate=round((df["Churn"] == "Yes").mean(), 4),
    )


@app.get("/api/v1/eda/feature-importance", response_model=FeatureImportanceResponse, tags=["eda"],
         responses={404: {"model": ErrorResponse}})
def feature_importance_endpoint():
    history = _load_history()
    if not history:
        raise HTTPException(status_code=404, detail="No pipeline runs recorded yet")
    latest = history[-1]
    return FeatureImportanceResponse(
        run_id=latest["run_id"],
        top_feature_importances=latest["top_feature_importances"],
        top_correlations_with_churn=latest["top_correlations_with_churn"],
    )


@app.get("/metrics", response_model=MetricsResponse, tags=["observability"])
def metrics():
    history = _load_history()
    success = sum(1 for r in history if r.get("status") == "SUCCESS")
    return MetricsResponse(
        requests_total=_metrics["requests_total"],
        requests_by_path=dict(_metrics["requests_by_path"]),
        pipeline_runs_total=len(history),
        pipeline_runs_success=success,
        pipeline_runs_failed=len(history) - success,
        uptime_seconds=round((datetime.now(timezone.utc) - APP_START_TIME).total_seconds(), 2),
    )


@app.on_event("startup")
def start_keep_alive():
    """Free-tier hosts sleep after ~15 min without inbound traffic, which would also pause the
    2-minute scheduler. Render exposes the public URL as RENDER_EXTERNAL_URL; pinging it every
    10 minutes goes through the host's proxy and counts as traffic. No-op locally/elsewhere.
    Disable with KEEP_ALIVE=false."""
    import os
    import threading
    import urllib.request
    url = os.environ.get("RENDER_EXTERNAL_URL")
    if not url or os.environ.get("KEEP_ALIVE", "true").lower() != "true":
        return

    def loop():
        while True:
            time.sleep(600)
            try:
                urllib.request.urlopen(url.rstrip("/") + "/health/live", timeout=15)
                logger.info("keep-alive ping ok")
            except Exception as exc:
                logger.warning(f"keep-alive ping failed: {exc}")

    threading.Thread(target=loop, daemon=True, name="keep-alive").start()
    logger.info(f"keep-alive enabled -> {url} every 10 min")


FRONTEND = settings.base_dir / "frontend" / "index.html"
CHART_DIR = settings.base_dir / "charts"
CHART_DIR.mkdir(exist_ok=True)
app.mount("/charts", StaticFiles(directory=str(CHART_DIR)), name="charts")


@app.get("/", include_in_schema=False)
def root():
    """Single-page front end (falls back to the simple dashboard if missing)."""
    if FRONTEND.exists():
        return FileResponse(FRONTEND)
    return HTMLResponse(dashboard())


@app.get("/api/v1/preprocessing/report", tags=["preprocessing"],
         responses={404: {"model": ErrorResponse}})
def preprocessing_report():
    """Activity 1.3 evidence: dtypes before/after, missing values, summary stats, normalization."""
    import pandas as pd
    from preprocessing import clean_dtypes, load_raw
    if not settings.clean_data_file.exists():
        raise HTTPException(status_code=404, detail="Run the pipeline first")
    raw = load_raw()
    before = {c: str(t) for c, t in raw.dtypes.items()}
    fixed = clean_dtypes(raw.copy())
    miss = fixed.isna().sum()
    clean = pd.read_csv(settings.clean_data_file)
    num = [c for c in ("SeniorCitizen", "tenure", "MonthlyCharges", "TotalCharges") if c in clean]
    desc = clean[num].describe().round(3)
    norm = [c for c in clean.columns if c.endswith("_norm")]
    return {
        "rows": len(clean),
        "dtypes_before": before,
        "dtypes_after": {c: str(t) for c, t in fixed.dtypes.items()},
        "missing_before_imputation": {c: {"count": int(n), "pct": round(n / len(fixed) * 100, 2)}
                                      for c, n in miss.items() if n > 0},
        "missing_after_imputation": int(clean[num].isna().sum().sum()),
        "imputation": "median (numeric columns)",
        "summary_statistics": json.loads(desc.to_json()),
        "normalization": {"method": "min-max", "columns": {c: {"min": float(clean[c].min()),
                          "max": float(clean[c].max())} for c in norm}},
    }


@app.get("/api/v1/eda/summary", tags=["eda"], responses={404: {"model": ErrorResponse}})
def eda_summary():
    """Activity 1.4 evidence: binning, encoding and categorical-vs-churn relationships."""
    import pandas as pd
    if not settings.clean_data_file.exists():
        raise HTTPException(status_code=404, detail="Run the pipeline first")
    df = pd.read_csv(settings.clean_data_file)
    y = (df["Churn"] == "Yes")
    bins = pd.cut(df["tenure"], [-1, 12, 24, 48, 72], labels=["0-12 mo", "13-24 mo", "25-48 mo", "49-72 mo"])
    cats = [c for c in df.select_dtypes(exclude="number").columns if c not in ("customerID",)]
    return {
        "churn_rate_by_tenure_bin": y.groupby(bins, observed=True).mean().round(4).to_dict(),
        "churn_rate_by_contract": y.groupby(df["Contract"]).mean().round(4).to_dict(),
        "churn_rate_by_internet_service": y.groupby(df["InternetService"]).mean().round(4).to_dict(),
        "binning": "tenure -> 4 bins (0-12, 13-24, 25-48, 49-72 months)",
        "encoding": {"method": "label encoding", "encoded_columns": cats},
        "charts": sorted(p.name for p in CHART_DIR.glob("0[1-6]_*.png")),
    }


@app.get("/api/v1/pipeline/logs", tags=["pipeline"])
def pipeline_logs(lines: int = 40):
    """Tail of logs/pipeline.log (Activity 1.5 logging)."""
    f = settings.log_dir / "pipeline.log"
    text = f.read_text().splitlines()[-max(1, min(lines, 500)):] if f.exists() else []
    return {"lines": text}


@app.get("/dashboard", response_class=HTMLResponse, tags=["dashboard"])
def dashboard():
    """Simple server-rendered Cloud dashboard summarizing DataOps activity."""
    history = _load_history()
    rows_html = "".join(
        f"<tr><td>{r['run_id']}</td><td>{r['timestamp_utc']}</td>"
        f"<td style='color:{'green' if r['status']=='SUCCESS' else 'red'}'>{r['status']}</td>"
        f"<td>{r['duration_sec']}s</td><td>{r.get('rows_processed','-')}</td></tr>"
        for r in reversed(history)
    )
    latest = history[-1] if history else {}
    top_features = latest.get("top_feature_importances", {})
    features_html = "".join(f"<li>{k}: {v:.4f}</li>" for k, v in top_features.items())
    html = f"""
    <html>
    <head>
        <title>Telco Churn DataOps Dashboard</title>
        <meta http-equiv="refresh" content="30">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 30px; background:#f7f8fa; }}
            h1 {{ color:#2c3e50; }}
            table {{ border-collapse: collapse; width:100%; background:white; }}
            th, td {{ border:1px solid #ddd; padding:8px; text-align:left; font-size:13px;}}
            th {{ background:#2c3e50; color:white; }}
            .card {{ background:white; padding:16px; border-radius:8px; margin-bottom:20px;
                     box-shadow:0 1px 3px rgba(0,0,0,0.1); }}
        </style>
    </head>
    <body>
        <h1>Telco Churn DataOps Pipeline - Cloud Dashboard</h1>
        <div class="card">
            <h3>Total runs: {len(history)}</h3>
            <p>Auto-refreshes every 30s. Pipeline scheduled every
               {settings.schedule_interval_minutes} minutes via APScheduler.</p>
        </div>
        <div class="card">
            <h3>Top Churn Drivers (latest run)</h3>
            <ul>{features_html or '<li>No data yet</li>'}</ul>
        </div>
        <div class="card">
            <h3>Run History</h3>
            <table>
                <tr><th>Run ID</th><th>Timestamp (UTC)</th><th>Status</th><th>Duration</th><th>Rows</th></tr>
                {rows_html}
            </table>
        </div>
    </body>
    </html>
    """
    return html


# ---------------------------------------------------------------------------
# Legacy (unversioned) aliases - kept so anything integrated against the
# original /api/* paths from the assignment submission keeps working.
# ---------------------------------------------------------------------------
app.add_api_route("/api/app/info", app_info, methods=["GET"], tags=["legacy"], deprecated=True)
app.add_api_route("/api/app/flow", app_flow, methods=["GET"], tags=["legacy"], deprecated=True)
app.add_api_route("/api/pipeline/runs", pipeline_runs, methods=["GET"], tags=["legacy"], deprecated=True)
app.add_api_route("/api/pipeline/latest", pipeline_latest, methods=["GET"], tags=["legacy"], deprecated=True)
app.add_api_route("/api/dataset/info", dataset_info, methods=["GET"], tags=["legacy"], deprecated=True)
app.add_api_route("/api/eda/feature-importance", feature_importance_endpoint, methods=["GET"],
                   tags=["legacy"], deprecated=True)
