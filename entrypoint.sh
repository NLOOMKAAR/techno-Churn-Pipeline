#!/bin/sh
# Starts the DataOps scheduler (runs pipeline every N minutes, logs to logs/)
# as a background process, then starts the FastAPI app in the foreground so
# the container's PID 1 stays alive and cloud platforms can health-check
# /health/live and /health/ready.
#
# Every knob here is env-var driven (12-factor) so the same image works
# unmodified across dev/staging/prod and across Cloud Run / ECS / AKS / GKE.
set -e

PORT="${PORT:-8000}"
HOST="${HOST:-0.0.0.0}"
WEB_CONCURRENCY="${WEB_CONCURRENCY:-1}"
# In a multi-replica deployment (k8s Deployment with replicas>1), every pod
# running its own embedded scheduler would duplicate each pipeline run. Set
# ENABLE_EMBEDDED_SCHEDULER=false and drive scheduling with a single
# Kubernetes CronJob instead (see k8s/30-cronjob.yaml) for correctness at
# scale. Defaults to true for local/Docker/single-instance use.
ENABLE_EMBEDDED_SCHEDULER="${ENABLE_EMBEDDED_SCHEDULER:-true}"

if [ "$ENABLE_EMBEDDED_SCHEDULER" = "true" ]; then
  echo "[entrypoint] Starting DataOps scheduler (background, embedded)..."
  python scheduler.py &
  SCHEDULER_PID=$!
else
  echo "[entrypoint] Embedded scheduler disabled (ENABLE_EMBEDDED_SCHEDULER=false)."
  echo "[entrypoint] Expecting an external scheduler (e.g. k8s CronJob) to drive pipeline runs."
  SCHEDULER_PID=""
fi

term_handler() {
  echo "[entrypoint] Caught SIGTERM, shutting down scheduler and API gracefully..."
  if [ -n "$SCHEDULER_PID" ]; then
    kill -TERM "$SCHEDULER_PID" 2>/dev/null || true
    wait "$SCHEDULER_PID" 2>/dev/null || true
  fi
  exit 0
}
trap term_handler TERM INT

echo "[entrypoint] Starting API server on ${HOST}:${PORT} (workers=${WEB_CONCURRENCY})..."
exec uvicorn api.main:app --host "$HOST" --port "$PORT" --workers "$WEB_CONCURRENCY" &
API_PID=$!
wait "$API_PID"
