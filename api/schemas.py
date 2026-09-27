"""
api/schemas.py
---------------
Typed request/response models. Giving every endpoint a real Pydantic model
(instead of returning bare dicts) means the generated OpenAPI 3.1 schema at
/openapi.json is fully typed - which is what lets a cloud API gateway
(AWS API Gateway, Apigee, Kong, Azure APIM) import this service directly
and generate a client SDK / validate requests at the edge.
"""
from typing import Any, Optional

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str = Field(..., examples=["NOT_FOUND"])
    message: str
    request_id: Optional[str] = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class LivenessResponse(BaseModel):
    status: str = "alive"
    server_time_utc: str


class ReadinessCheck(BaseModel):
    name: str
    ok: bool
    detail: Optional[str] = None


class ReadinessResponse(BaseModel):
    status: str  # "ready" | "not_ready"
    checks: list[ReadinessCheck]


class AppInfoResponse(BaseModel):
    app_name: str
    version: str
    environment: str
    deployment_target: str
    python_version: str
    platform: str
    started_at_utc: str
    uptime_seconds: float


class PipelineStage(BaseModel):
    order: int
    stage: str
    module: str
    description: str


class AppFlowResponse(BaseModel):
    pipeline_name: str
    schedule: str
    stages: list[PipelineStage]


class PipelineRun(BaseModel):
    run_id: str
    timestamp_utc: str
    status: str
    duration_sec: float
    rows_processed: Optional[int] = None
    model_config = {"extra": "allow"}  # tolerate extra fields (e.g. top_feature_importances)


class PipelineRunsResponse(BaseModel):
    total_runs: int
    runs: list[PipelineRun]


class DatasetInfoResponse(BaseModel):
    rows: int
    columns: int
    column_names: list[str]
    target_variable: str
    churn_rate: float


class FeatureImportanceResponse(BaseModel):
    run_id: str
    top_feature_importances: dict[str, float]
    top_correlations_with_churn: dict[str, float]


class MetricsResponse(BaseModel):
    requests_total: int
    requests_by_path: dict[str, int]
    pipeline_runs_total: int
    pipeline_runs_success: int
    pipeline_runs_failed: int
    uptime_seconds: float
