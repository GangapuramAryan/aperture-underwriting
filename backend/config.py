"""Application configuration.

Every value is read from the environment with a safe local default. Nothing
secret is committed: `.env` is git-ignored and `.env.example` documents the
required keys with placeholder values.

The database URL is deliberately a single setting. The service targets
PostgreSQL, and switching from the local SQLite development store to Postgres
is a one-line environment change with no code edit -- which is what makes the
claim "Postgres-ready" verifiable rather than aspirational.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # ---- Service ----
    app_name: str = "Aperture Underwriting Engine"
    api_version: str = "v1"
    environment: str = "local"

    # ---- Storage ----
    # SQLite for local development; set DATABASE_URL to a postgresql+psycopg://
    # DSN for the containerised Postgres + pgvector instance.
    database_url: str = "sqlite:///./aperture.db"

    # ---- Model artefacts ----
    model_dir: Path = Path("artifacts")
    enhanced_model_file: str = "model_enhanced.joblib"
    baseline_model_file: str = "model_baseline.joblib"

    # ---- Credit policy ----
    # Probability-of-default cut-offs. Between the two bounds an application is
    # referred to a human underwriter rather than auto-declined: the referral
    # band is where a thin-file applicant who would previously have been
    # rejected outright gets a second look.
    approve_threshold: float = 0.08
    refer_threshold: float = 0.18
    target_loss_rate: float = 0.03

    # ---- Line sizing ----
    max_credit_line: float = 500_000.0
    min_credit_line: float = 10_000.0
    line_income_multiple: float = 0.35

    # ---- Fraud policy ----
    fraud_review_threshold: float = 0.45
    fraud_block_threshold: float = 0.75

    # ---- Security ----
    jwt_secret: str = "local-development-only-do-not-use-in-production"
    jwt_algorithm: str = "HS256"
    token_ttl_minutes: int = 60

    # ---- LLM (provider chosen later; 'none' falls back to templates) ----
    llm_provider: str = "none"
    llm_model: str = ""
    llm_api_key: str = ""


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance, so the environment is read once per process."""
    return Settings()
