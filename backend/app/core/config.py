"""Application configuration, sourced entirely from the environment (N3: no secrets in code)."""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Placeholder JWT secrets shipped for local dev (config default + .env.example).
# Refused in production so a deploy can't silently sign tokens with a public value.
_WEAK_JWT_SECRETS = {"change-me-in-production", "dev-secret-change-me"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App ---
    app_name: str = "Leads Tracker API"
    environment: str = Field(default="local")  # local | production | test
    log_level: str = Field(default="INFO")
    api_v1_prefix: str = "/api/v1"

    # --- Database ---
    database_url: str = Field(
        default="postgresql+psycopg2://leads:leads@db:5432/leads",
    )

    # --- Auth / JWT ---
    jwt_secret: str = Field(default="change-me-in-production")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 12  # 12h

    # --- Object storage (S3 / MinIO) ---
    s3_endpoint_url: str | None = Field(default="http://minio:9000")  # None → real AWS S3
    s3_region: str = Field(default="us-east-1")
    s3_access_key: str = Field(default="minioadmin")
    s3_secret_key: str = Field(default="minioadmin")
    s3_bucket: str = Field(default="resumes")
    s3_use_path_style: bool = Field(default=True)  # required for MinIO
    presigned_url_expire_seconds: int = 300

    # --- Email ---
    email_backend: str = Field(default="smtp")  # smtp | console
    smtp_host: str = Field(default="mailpit")
    smtp_port: int = Field(default=1025)
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = Field(default=False)
    email_from: str = Field(default="Leads Tracker <no-reply@leads.local>")
    dashboard_url: str = Field(default="http://localhost:3000/leads")

    # --- Uploads ---
    max_upload_bytes: int = Field(default=10 * 1024 * 1024)  # 10 MB
    allowed_resume_content_types: tuple[str, ...] = (
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    # --- Seed (first-boot demo attorney) ---
    seed_attorney_email: str = Field(default="attorney@example.com")
    seed_attorney_password: str = Field(default="attorney123")
    seed_attorney_name: str = Field(default="Attorney Admin")

    # --- CORS ---
    cors_origins: tuple[str, ...] = ("http://localhost:3000",)

    @model_validator(mode="after")
    def _require_strong_jwt_secret_in_production(self) -> "Settings":
        """Fail fast if a production deploy is still using a placeholder JWT secret."""
        if self.environment == "production" and self.jwt_secret in _WEAK_JWT_SECRETS:
            raise ValueError(
                "JWT_SECRET is set to a known placeholder value. Set a strong secret "
                "(e.g. `openssl rand -hex 32`) before running in production."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
