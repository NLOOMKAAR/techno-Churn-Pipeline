# Telco Churn DataOps Pipeline - Cloud-native container image
FROM python:3.12-slim

# --- Security: run as a non-root user (required by most cluster PodSecurity
# policies / OpenShift SCCs, and good practice everywhere else) ---
RUN groupadd -r appuser && useradd -r -g appuser -d /app appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Generate the initial dataset at build time (falls back to the bundled
# copy automatically if the build environment has no network egress).
RUN python generate_data.py

RUN chmod +x /app/entrypoint.sh \
    && chown -R appuser:appuser /app

USER appuser

# 12-factor: the port is configurable via $PORT, defaulting to 8000.
ENV PORT=8000 \
    HOST=0.0.0.0 \
    LOG_LEVEL=INFO \
    LOG_FORMAT=json \
    PYTHONUNBUFFERED=1
EXPOSE 8000

# Container-native health check hitting the liveness probe (works even
# without an orchestrator, e.g. plain `docker run` + `docker ps`).
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request,os,sys; \
    urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",8000)}/health/live', timeout=3)" \
    || exit 1

# entrypoint.sh starts BOTH the APScheduler background pipeline and the
# FastAPI server (uvicorn) in the same container, which is how this is
# meant to run on Cloud Run / ECS Fargate / Azure Container Apps / K8s / an EC2 VM.
CMD ["/app/entrypoint.sh"]
