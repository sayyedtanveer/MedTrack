from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────
    app_name: str = "MedTrack ERP"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"

    # ── Database ─────────────────────────────────
    database_url: str = ""
    database_sync_url: str = ""  # Used only by Alembic

    # Replit provides PG* env vars; construct URLs from them if DATABASE_URL not set
    pghost: str = ""
    pgport: str = "5432"
    pguser: str = ""
    pgpassword: str = ""
    pgdatabase: str = ""

    @property
    def async_database_url(self) -> str:
        """Return asyncpg-compatible URL, constructing from PG* vars if needed."""
        url = self.database_url
        if not url and self.pghost:
            url = f"postgresql://{self.pguser}:{self.pgpassword}@{self.pghost}:{self.pgport}/{self.pgdatabase}?sslmode=disable"
        # Convert sync postgres:// to asyncpg driver
        url = url.replace("postgresql://", "postgresql+asyncpg://")
        # asyncpg uses ssl=disable, not sslmode=disable
        url = url.replace("sslmode=disable", "ssl=disable")
        return url

    @property
    def sync_database_url(self) -> str:
        """Return sync psycopg2-compatible URL."""
        # Prefer the Replit-injected DATABASE_URL (already a sync URL)
        url = self.database_url
        if not url and self.pghost:
            url = f"postgresql://{self.pguser}:{self.pgpassword}@{self.pghost}:{self.pgport}/{self.pgdatabase}?sslmode=disable"
        url = url.replace("postgresql+asyncpg://", "postgresql://")
        return url

    # ── JWT ──────────────────────────────────────
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 60
    jwt_refresh_expiry_days: int = 7

    # ── CORS ─────────────────────────────────────
    cors_origins: str = "*"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def validate_cors_for_production(self) -> None:
        """Raise ValueError if running in production with wildcard CORS.

        Call this during application startup to enforce the security
        requirement that CORS_ALLOWED_ORIGINS must be explicitly set in
        production environments.

        Requirements: 43.2
        """
        if self.is_production:
            origins = self.cors_origins_list
            if not origins or origins == ["*"]:
                raise ValueError(
                    "CORS_ALLOWED_ORIGINS must be explicitly set in production. "
                    "Wildcard '*' is not allowed for security reasons. "
                    "Set CORS_ORIGINS to a comma-separated list of allowed origins, "
                    "e.g. https://app.yourdomain.com,https://admin.yourdomain.com"
                )

    # ── File Storage ─────────────────────────────
    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 10

    # ── Redis ────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── Email (Resend) ───────────────────────────────
    resend_api_key: str = ""
    resend_from_email: str = "noreply@medtrack.app"

    # ── Frontend URL (for email links) ───────────
    frontend_url: str = "http://localhost:5173"

    # ── Legacy SMTP (deprecated) ─────────────────
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def database_sync_url_computed(self) -> str:
        """Return explicit sync URL or derive from async URL."""
        return self.sync_database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
