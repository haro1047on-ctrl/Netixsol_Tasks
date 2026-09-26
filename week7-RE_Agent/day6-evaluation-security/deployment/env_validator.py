"""Task 5: Production Environment Variable Schema & Validator."""
from __future__ import annotations

import os
from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Strict configuration schema for production deployment."""

    # Server settings
    HOST: str = Field(default="0.0.0.0", description="Server bind host")
    PORT: int = Field(default=8000, description="Server bind port")
    APP_ENV: str = Field(default="production", description="Environment: development, staging, production")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    SECRET_KEY: str = Field(default="realestate-hub-production-secret-key-day6", description="Application secret key")
    
    # Google AI / LLM Configuration
    GOOGLE_API_KEY: str = Field(default="", description="Google Gemini API Key")
    GEMINI_LLM_MODEL: str = Field(default="gemini-2.5-flash", description="Gemini LLM model name")
    GEMINI_EMBEDDING_MODEL: str = Field(default="models/text-embedding-004", description="Gemini text embedding model")

    # Vapi & Deepgram Voice Configurations
    VAPI_API_KEY: Optional[str] = Field(default="", description="Vapi API Key")
    VAPI_VOICE_ID: str = Field(default="Elliot", description="Voice ID")
    VAPI_VOICE_PROVIDER: str = Field(default="vapi", description="Voice Provider")
    VAPI_TRANSCRIBER_MODEL: str = Field(default="nova-3", description="Deepgram transcriber model")
    VAPI_TRANSCRIBER_LANGUAGE: str = Field(default="ur", description="ASR language code")
    BACKEND_PUBLIC_URL: Optional[str] = Field(default="", description="Public webhook URL for Vapi callbacks")

    # Database & Storage
    DB_BACKEND: str = Field(default="sqlite", description="Database engine (sqlite or postgresql)")
    CHROMA_PERSIST_DIR: str = Field(default="storage/chroma_db", description="ChromaDB vector persistence directory")
    
    # Operational SLOs
    SLO_LATENCY_P95_MS: float = Field(default=1500.0, description="Max acceptable p95 turn latency in ms")
    SLO_MAX_ERROR_RATE: float = Field(default=0.05, description="Max acceptable API error rate (5%)")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("PORT")
    @classmethod
    def validate_port(cls, v: int) -> int:
        if not (1 <= v <= 65535):
            raise ValueError("Port must be between 1 and 65535")
        return v


def validate_environment() -> AppSettings:
    """Validate runtime environment against strict schema."""
    settings = AppSettings()
    return settings


# Global settings instance
app_settings = validate_environment()
