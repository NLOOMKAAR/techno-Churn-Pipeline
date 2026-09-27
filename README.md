# Telco Customer Churn - Cloud-Native DataOps Pipeline
### AIMLCZG549 API-Driven Cloud Native Solutions — Assignment I

## 1. Business Problem
A telecom operator wants to proactively flag customers likely to **churn**
(cancel service) so retention teams can intervene early. This project builds
an automated, cloud-deployable data pipeline that ingests customer data,
cleans/prepares it, runs exploratory analysis to surface churn drivers, and
exposes everything through REST APIs and a live dashboard.

## 2. Architecture
```
                 ┌────────────────────────────┐
                 │   APScheduler (every 2 min) │
                 │        scheduler.py         │
                 └──────────────┬──────────────┘
                                │ triggers
                                ▼
   generate_data.py → preprocessing.py → eda.py → pipeline.py (logging)
   (Ingestion)         (1.3 Pre-proc)     (1.4 EDA)  (1.5 DataOps/logging)
                                │
                                ▼
                  logs/pipeline.log + logs/run_history.json
                                │
                                ▼
                 ┌──────────────────────────────┐
                 │   FastAPI app (api/main.py)  │
                 │  /api/app/info  /api/app/flow │
                 │  /api/pipeline/*  /api/dataset/*│
                 │  /api/eda/*  /dashboard  /health│
                 └──────────────────────────────┘
                                │
                    Deployed as a Docker container to
                    AWS ECS Fargate / GCP Cloud Run / Azure Container Apps
```

## 3. Repository Layout
| Path | Purpose |
|---|---|
| `generate_data.py` | 1.2 Data ingestion — pulls the real Kaggle Telco Customer Churn dataset (7,043 rows) |
| `preprocessing.py` | 1.3 Summary stats, missing-value handling, dtype fix, normalization |
| `eda.py` | 1.4 Correlation, binning, encoding, feature importance, charts |
| `pipeline.py` | 1.5 DataOps orchestrator — runs stages, logs, writes run history |
| `scheduler.py` | 1.5 APScheduler — fires `pipeline.py` every 2 minutes |
| `api/main.py` | Sub-Objective 2 — FastAPI app: versioned routes, probes, middleware |
| `api/config.py` | 12-factor settings (env-var driven) |
| `api/schemas.py` | Typed Pydantic request/response models (OpenAPI contract) |
| `api/logging_setup.py` | Structured JSON logging for cloud log aggregators |
| `export_openapi.py` | Dumps the live OpenAPI 3.1 schema to `openapi.json` |
| `charts/` | Generated EDA visualizations + dashboard screenshot |
| `logs/pipeline.log`, `logs/run_history.json` | DataOps activity logs |
| `logs/api_test_evidence/` | Captured request/response + status codes for every endpoint |
| `postman_collection.json` | Importable Postman collection for API testing |
| `Dockerfile`, `entrypoint.sh`, `.dockerignore`, `.env.example` | Containerization for cloud deployment |
| `docker-compose.yaml` | Local integration-test harness |
| `k8s/` | Kubernetes manifests: Namespace/ConfigMap, Deployment, Service/HPA/Ingress, CronJob |

## 4. Running Locally
```bash
pip install -r requirements.txt
python generate_data.py          # 1.2 ingestion
python pipeline.py               # runs 1.3 + 1.4 once, logs the run
python scheduler.py              # keeps running the pipeline every 2 minutes
# in a second terminal:
uvicorn api.main:app --reload --port 8000
# Dashboard:      http://localhost:8000/dashboard
# Swagger UI:     http://localhost:8000/docs
# OpenAPI schema: http://localhost:8000/openapi.json

# Or with Docker Compose (mirrors the container's env-driven config):
docker compose up --build
```

## 5. Cloud Deployment (any of the following)

**Option A — Render.com (genuinely free, no credit card, recommended for a quick live demo)**
This repo includes `render.yaml`, so deployment is one click:
1. Push this repo to GitHub (public or private).
2. On [render.com](https://render.com) → **New → Blueprint** → connect the repo. Render
   reads `render.yaml` and builds the existing `Dockerfile` automatically —
   no code changes needed, since `PORT` is already read dynamically from
   the environment (`api/config.py`).
3. Render assigns a public HTTPS URL, e.g. `https://telco-churn-dataops-pipeline.onrender.com`.
   Visit `/dashboard`, `/docs`, `/api/v1/app/info`, etc. — this is now a
   real internet-accessible cloud deployment, not `localhost`.

Caveat: Render's free instances spin down after ~15 minutes with no
incoming HTTP requests (cold start ~30–50s on the next request). Since the
DataOps scheduler only keeps firing while the container is awake, use a
free uptime pinger (e.g. [cron-job.org](https://cron-job.org) or
UptimeRobot) to hit `/health/live` every 5–10 minutes if you want the
2-minute pipeline schedule to keep running continuously for a demo/grading
window, rather than only while someone is actively browsing the dashboard.

**Option B — Google Cloud Run**
```bash
gcloud builds submit --tag gcr.io/<PROJECT_ID>/telco-churn-pipeline
gcloud run deploy telco-churn-pipeline \
  --image gcr.io/<PROJECT_ID>/telco-churn-pipeline \
  --min-instances=1 --port 8000 --allow-unauthenticated \
  --set-env-vars ENVIRONMENT=production,LOG_FORMAT=json
```
Free tier: 2M requests/month, 180K vCPU-seconds/month — but requires a
Google account with a credit card on file (not charged within free limits).
`--min-instances=1` avoids Render-style spin-down but may incur small cost
beyond the free allowance; omit it to scale to zero and stay fully free.

**Option C — AWS ECS Fargate / App Runner**: push the image to ECR;
App Runner in particular can build straight from the `Dockerfile` in this
repo. Health-check target `/health/ready` (readiness, not liveness — the
load balancer should stop routing to a pod that isn't ready, not restart it).

**Option D — Azure Container Apps**
```bash
az containerapp up --name telco-churn-pipeline \
  --source . --ingress external --target-port 8000
```

**Option E — Kubernetes** (any cluster: GKE/EKS/AKS/on-prem) — see Section 7.

Each platform exposes its own **built-in deployment/status API**
(e.g. `gcloud run services describe`, AWS `DescribeServices`, Azure
`az containerapp show`) which can be queried for deployment metadata —
this satisfies Activity 3.1's "use built-in APIs to access deployment info"
in addition to the custom `/api/v1/app/info` and `/api/v1/app/flow`
endpoints this project also exposes.

## 6. API Endpoints (Sub-Objective 2)
| Endpoint | Detail Exposed |
|---|---|
| `GET /health/live` | Liveness probe — is the process up? |
| `GET /health/ready` | Readiness probe — can it actually serve traffic? |
| `GET /health` | *(deprecated)* legacy alias for `/health/live` |
| `GET /api/v1/app/info` | App name, version, environment, deployment target, uptime |
| `GET /api/v1/app/flow` | Pipeline stage/flow definition & schedule |
| `GET /api/v1/pipeline/runs` | Full DataOps run history |
| `GET /api/v1/pipeline/latest` | Latest run's status & metrics |
| `GET /api/v1/dataset/info` | Dataset schema, row/column counts, churn rate |
| `GET /api/v1/eda/feature-importance` | Latest churn-driver feature importances |
| `GET /metrics` | Request counters + pipeline success/failure counts |
| `GET /dashboard` | HTML cloud dashboard (auto-refreshing) |
| `GET /openapi.json` / `GET /docs` | Machine-readable API contract / Swagger UI |
| `GET /api/*` | *(deprecated)* unversioned aliases of the `/api/v1/*` routes, kept for backward compatibility |

All endpoints were tested with `curl`; captured status codes and JSON
bodies are stored in `logs/api_test_evidence/`. A Postman collection
(`postman_collection.json`) is provided for interactive re-testing.
Every error response (4xx/5xx, including unmatched routes) returns a
uniform envelope: `{"error": {"code", "message", "request_id"}}`.

## 7. Cloud-Native API Integration
This service follows the standard patterns needed to plug into a real
cloud platform's API ecosystem, not just run in a single container:

- **12-factor config** (`api/config.py`) — every deploy-time setting
  (port, CORS origins, log level/format, environment name, schedule
  interval) is an environment variable, never hardcoded. See `.env.example`.
- **API versioning** — the stable contract lives under `/api/v1/*`; the
  original unversioned `/api/*` paths are kept as deprecated aliases so
  nothing already integrated against this service breaks.
- **Typed OpenAPI 3.1 contract** (`api/schemas.py` + `/openapi.json`) —
  every response is a real Pydantic model, so the schema an API gateway
  (AWS API Gateway, Azure APIM, Apigee, Kong) imports is fully typed.
  Regenerate the static file with `python export_openapi.py`.
- **Split liveness/readiness probes** — `/health/live` vs `/health/ready`
  follow the Kubernetes/Cloud Run/ECS health-check contract: liveness
  failing restarts the pod; readiness failing just pulls it out of the
  load balancer without restarting it.
- **Structured JSON logs + request correlation** (`api/logging_setup.py`)
  — every log line is JSON with a `request_id` that's also echoed back
  as the `X-Request-ID` response header, so a request can be traced
  across this service and any others in front of/behind it.
- **Uniform error envelope** — every error, including framework-level
  404s, returns `{"error": {"code", "message", "request_id"}}` instead
  of ad-hoc shapes, so client/gateway error handling is consistent.
- **`/metrics`** — basic request and pipeline-run counters for wiring
  into a monitoring stack (Prometheus scraping, CloudWatch, etc).
- **Container hardening** (`Dockerfile`) — runs as a non-root user, has a
  `HEALTHCHECK` against `/health/live`, and takes `PORT`/`HOST` from env.
- **Kubernetes manifests** (`k8s/`) — `Namespace` + `ConfigMap`,
  `Deployment` with resource requests/limits and both probes wired up,
  `Service` + `HorizontalPodAutoscaler` + optional `Ingress`, and a
  `CronJob` that runs the pipeline exactly once every 2 minutes when the
  API is scaled to multiple replicas (the embedded APScheduler is
  disabled via `ENABLE_EMBEDDED_SCHEDULER=false` in that case, to avoid
  every replica triggering its own duplicate pipeline run):
  ```bash
  kubectl apply -f k8s/00-namespace-and-config.yaml
  kubectl apply -f k8s/10-deployment.yaml
  kubectl apply -f k8s/20-service-hpa-ingress.yaml
  kubectl apply -f k8s/30-cronjob.yaml
  ```
- **`docker-compose.yaml`** — local integration-test harness mirroring
  the same env-driven configuration as the container/cluster deployment.

