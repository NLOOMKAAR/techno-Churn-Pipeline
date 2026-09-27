"""
api/config.py
--------------
12-factor-style configuration: every knob a cloud platform (Cloud Run, ECS,
Container Apps, Kubernetes) needs to override at deploy time comes from an
environment variable, never a hardcoded value. This is what lets the exact
same container image run unmodified in dev, staging, and prod.

Precedence: real environment variables > .env file (local dev only) > defaults.
"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")

    # --- Identity ---
    app_name: str = "telco-churn-dataops-pipeline"
    app_version: str = "2.0.0"
    environment: str = "production"  # dev | staging | production

    # --- Network ---
    host: str = "0.0.0.0"
    port: int = 8000

    # --- CORS (comma-separated list, "*" for all) ---
    cors_origins: str = "*"

    # --- Paths (overridable so the container can mount a volume anywhere) ---
    base_dir: Path = Path(__file__).parent.parent
    data_dir: Path = base_dir / "data"
    log_dir: Path = base_dir / "logs"

    # --- Observability ---
    log_level: str = "INFO"
    log_format: str = "json"  # json | text  -- json for cloud log aggregators

    # --- DataOps schedule (kept in sync with scheduler.py) ---
    schedule_interval_minutes: int = 2

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def history_file(self) -> Path:
        return self.log_dir / "run_history.json"

    @property
    def clean_data_file(self) -> Path:
        return self.data_dir / "telco_churn_clean.csv"


@lru_cache
def get_settings() -> Settings:
    """Cached singleton so env vars are parsed once per process."""
    return Settings()
