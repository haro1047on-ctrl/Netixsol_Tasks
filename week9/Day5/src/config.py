"""City Care Clinics - Centralized Application Configuration.

Loads environment variables with Pydantic Settings, providing strongly-typed configuration
for database, security, LLM provider, SMTP email delivery, and clinic operations.
"""
from __future__ import annotations

import os
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ClinicConfig(BaseSettings):
    """Central configuration schema for City Care Clinics assistant."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Application & Environment
    app_env: str = Field(default="development", alias="APP_ENV")
    application_secret: str = Field(
        default="city_care_clinics_secret_key_2026_super_secure",
        alias="APPLICATION_SECRET"
    )
    jwt_secret_key: str = Field(
        default="city_care_clinics_jwt_secret_2026_super_secure",
        alias="JWT_SECRET_KEY"
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=1440, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    allowed_origins: str = Field(
        default="http://localhost:8000,http://localhost:8501,http://localhost:8502,http://127.0.0.1:8000,http://127.0.0.1:8501,http://127.0.0.1:8502",
        alias="ALLOWED_ORIGINS"
    )
    clinic_timezone: str = Field(default="Asia/Karachi", alias="CLINIC_TIMEZONE")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Database
    database_url: Optional[str] = Field(default=None, alias="DATABASE_URL")

    # LLM Provider
    llm_provider: str = Field(default="gemini", alias="LLM_PROVIDER")
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    groq_model: str = Field(default="qwen/qwen3.8-27b", alias="GROQ_MODEL")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-3.8-flash", alias="GEMINI_MODEL")
    llm_fallback_to_offline: bool = Field(default=True, alias="LLM_FALLBACK_TO_OFFLINE")

    # Real Email Delivery & SMTP Provider
    email_provider: str = Field(default="smtp", alias="EMAIL_PROVIDER")
    smtp_host: str = Field(default="smtp.gmail.com", alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_username: str = Field(default="notifications@citycareclinics.pk", alias="SMTP_USERNAME")
    smtp_password: str = Field(default="", alias="SMTP_PASSWORD")
    smtp_use_tls: bool = Field(default=True, alias="SMTP_USE_TLS")
    smtp_from_email: str = Field(default="notifications@citycareclinics.pk", alias="SMTP_FROM_EMAIL")
    test_email_recipient: str = Field(default="test_patient@example.com", alias="TEST_EMAIL_RECIPIENT")

    # ChromaDB & Vector Knowledge Base
    chroma_persist_directory: Optional[str] = Field(default=None, alias="CHROMA_PERSIST_DIRECTORY")

    # Reminders & Schedulers
    reminder_check_interval_seconds: int = Field(default=60, alias="REMINDER_CHECK_INTERVAL_SECONDS")
    reminder_dry_run: bool = Field(default=False, alias="REMINDER_DRY_RUN")

    @property
    def cors_origins(self) -> List[str]:
        """Parses comma-separated allowed origins into a list."""
        if not self.allowed_origins or self.allowed_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    def is_production(self) -> bool:
        """Checks if running in production mode."""
        return self.app_env.lower() in ("production", "prod")

    def get_effective_database_url(self) -> str:
        """Returns PostgreSQL URL or local SQLite fallback URL."""
        if self.database_url and (self.database_url.startswith("postgresql") or self.database_url.startswith("sqlite")):
            return self.database_url
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        db_path = os.path.join(base_dir, "Day2", "clinic_fhir.db")
        return f"sqlite:///{db_path}"


ClinicConfig.model_rebuild()

# Global Singleton
settings = ClinicConfig()

